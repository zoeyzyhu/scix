import subprocess
import sys
from pathlib import Path

import pytest

from scix.bootstrap import doctor, perform_dev_up, perform_up
from scix.exceptions import CheckFailedError, ScixError
from scix.generator import sync_workspace
from scix.scaffold import copy_template_paths, copy_template_root


def test_root_ai_tree_matches_packaged_template_ai() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_ai = repo_root / "ai"
    template_ai = repo_root / "src/scix/assets/template_root/ai"
    mirrored_roots = ["agents", "hooks", "policy", "skills"]

    source_files = sorted(
        path.relative_to(source_ai)
        for root_name in mirrored_roots
        for path in (source_ai / root_name).rglob("*")
        if path.is_file()
    )
    template_files = sorted(
        path.relative_to(template_ai)
        for root_name in mirrored_roots
        for path in (template_ai / root_name).rglob("*")
        if path.is_file()
    )

    assert source_files == template_files
    for relative_path in source_files:
        assert (source_ai / relative_path).read_text(encoding="utf-8") == (
            template_ai / relative_path
        ).read_text(encoding="utf-8")
    assert (template_ai / "generated/repos/.gitkeep").exists()


def test_sync_workspace_updates_packaged_template_ai_in_source_checkout(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    copy_template_paths(tmp_path / "src/scix/assets/template_root", ["ai"])
    source_file = tmp_path / "ai/policy/workspace.md"
    template_file = tmp_path / "src/scix/assets/template_root/ai/policy/workspace.md"
    source_file.write_text("updated workspace policy\n", encoding="utf-8")

    with pytest.raises(CheckFailedError):
        sync_workspace(tmp_path, check=True)

    changed = sync_workspace(tmp_path)

    assert template_file.read_text(encoding="utf-8") == "updated workspace policy\n"
    assert template_file in changed


def test_sync_workspace_generates_expected_files(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    changed = sync_workspace(tmp_path)

    assert changed
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".codex/config.toml").exists()
    assert (tmp_path / ".claude/settings.json").exists()
    assert (tmp_path / ".agents/skills/repo-router/SKILL.md").exists()
    assert (
        (tmp_path / ".agents/skills/repo-router/SKILL.md")
        .read_text(encoding="utf-8")
        .startswith("---\n")
    )
    assert (tmp_path / ".claude/agents/explorer.md").exists()
    assert (tmp_path / ".codex/agents/explorer.toml").exists()
    assert (tmp_path / "ai/generated/repos/kintera/AGENTS.md").exists()


def test_sync_workspace_copies_repo_overlays_into_existing_clone(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    (tmp_path / "repos/kintera").mkdir(parents=True)

    sync_workspace(tmp_path)

    assert (tmp_path / "repos/kintera/AGENTS.md").exists()
    assert (tmp_path / "repos/kintera/CLAUDE.md").exists()


def test_sync_workspace_check_detects_stale_file(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    sync_workspace(tmp_path)
    (tmp_path / "AGENTS.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(CheckFailedError):
        sync_workspace(tmp_path, check=True)


def test_perform_up_rejects_non_empty_directory_without_force(tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")

    with pytest.raises(ScixError):
        perform_up(tmp_path, assume_yes=True, skip_python=True, skip_repos=True)


def test_perform_up_rejects_repo_shaped_directory_without_force(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("developer checkout\n", encoding="utf-8")
    (tmp_path / "src/scix").mkdir(parents=True)

    with pytest.raises(ScixError):
        perform_up(tmp_path, assume_yes=True, skip_python=True, skip_repos=True)


def test_perform_up_force_allows_non_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")

    perform_up(tmp_path, assume_yes=True, force=True, skip_python=True, skip_repos=True)

    assert (tmp_path / ".ai-root").exists()
    assert (tmp_path / "README.md").exists()


def test_doctor_reports_invalid_skill_frontmatter(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    skill_path = tmp_path / "ai/skills/repo-router/SKILL.md"
    skill_path.write_text("# broken\n", encoding="utf-8")

    issues = doctor(tmp_path)

    assert any("Invalid skill file" in issue for issue in issues)


def test_perform_dev_up_backfills_workspace_without_overwriting_canonical_files(
    tmp_path: Path,
) -> None:
    copy_template_paths(tmp_path, ["ai"])
    (tmp_path / "src/scix").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'scix'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("custom contributor README\n", encoding="utf-8")
    (tmp_path / "ai/policy/workspace.md").write_text("custom workspace policy\n", encoding="utf-8")

    perform_dev_up(tmp_path, skip_python=True, skip_repos=True)

    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "custom contributor README\n"
    assert (tmp_path / "ai/policy/workspace.md").read_text(
        encoding="utf-8"
    ) == "custom workspace policy\n"
    assert (tmp_path / ".ai-root").exists()
    assert (tmp_path / "repos/README.md").exists()
    assert (tmp_path / "workspace/README.md").exists()
    assert (tmp_path / ".codex/config.toml").exists()
    assert (tmp_path / ".claude/settings.json").exists()


def test_dev_setup_and_bootstrap_import_without_yaml_on_sys_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(repo_root / 'src').__repr__()}); "
        "import scix.bootstrap; "
        "import scix.dev_setup"
    )
    result = subprocess.run(
        [sys.executable, "-S", "-c", code],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
