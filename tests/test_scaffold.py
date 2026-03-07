from pathlib import Path

import pytest

from scix.bootstrap import perform_up
from scix.exceptions import CheckFailedError, ScixError
from scix.generator import sync_workspace
from scix.scaffold import copy_template_root


def test_sync_workspace_generates_expected_files(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    changed = sync_workspace(tmp_path)

    assert changed
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".codex/config.toml").exists()
    assert (tmp_path / ".claude/settings.json").exists()
    assert (tmp_path / ".agents/skills/repo-router/SKILL.md").exists()
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


def test_perform_up_force_allows_non_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")

    perform_up(tmp_path, assume_yes=True, force=True, skip_python=True, skip_repos=True)

    assert (tmp_path / ".ai-root").exists()
    assert (tmp_path / "README.md").exists()
