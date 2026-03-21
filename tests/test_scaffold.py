from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import scix.bootstrap as bootstrap
from scix.bootstrap import dev_up_guidance, doctor, perform_dev_up, perform_up, up_guidance
from scix.exceptions import CheckFailedError, ScixError
from scix.generator import sync_workspace
from scix.scaffold import copy_template_paths, copy_template_root

REAL_ENSURE_AGENT_CLIS = bootstrap._ensure_agent_clis


@pytest.fixture(autouse=True)
def stub_agent_cli_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bootstrap,
        "_ensure_agent_clis",
        lambda: bootstrap.AgentInstallResult(install_needed=False, attempted=False),
    )


def _write_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def _prepare_dev_checkout(tmp_path: Path) -> None:
    copy_template_paths(tmp_path, ["ai"])
    (tmp_path / "src/scix").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'scix'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("custom contributor README\n", encoding="utf-8")
    (tmp_path / "ai/policy/workspace.md").write_text("custom workspace policy\n", encoding="utf-8")


def _create_reference_repo_dirs(root: Path) -> None:
    for repo_name in ["kintera", "pydisort", "snapy", "pyharp", "paddle"]:
        (root / "repos" / repo_name).mkdir(parents=True, exist_ok=True)


def _configure_fake_agent_install(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    preinstalled: bool = False,
    install_success: bool = True,
    install_codex: bool = True,
    install_claude: bool = True,
) -> list[str]:
    test_bin = tmp_path / "test-bin"
    test_bin.mkdir()
    nvm_dir = tmp_path / ".nvm"
    nvm_bin = nvm_dir / "versions/node/v22.9.0/bin"
    scripts: list[str] = []
    real_which = shutil.which

    monkeypatch.setenv("PATH", str(test_bin))
    monkeypatch.setenv("NVM_DIR", str(nvm_dir))

    def seed_installed_tools(*, codex: bool, claude: bool) -> None:
        (nvm_dir / "nvm.sh").parent.mkdir(parents=True, exist_ok=True)
        (nvm_dir / "nvm.sh").write_text("# nvm\n", encoding="utf-8")
        _write_executable(nvm_bin / "node")
        _write_executable(nvm_bin / "npm")
        if codex:
            _write_executable(nvm_bin / "codex")
        if claude:
            _write_executable(nvm_bin / "claude")

    if preinstalled:
        seed_installed_tools(codex=install_codex, claude=install_claude)

    def fake_which(name: str) -> str | None:
        if name == "bash":
            return "/bin/bash"
        if name == "curl":
            return "/usr/bin/curl"
        return real_which(name, path=os.environ.get("PATH"))

    def fake_run(
        cmd: list[str],
        cwd: Path | None = None,
        check: bool = False,
        capture_output: bool = False,
        text: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        del cwd, capture_output, text
        if cmd[:2] != ["/bin/bash", "-lc"]:
            raise AssertionError(f"Unexpected subprocess invocation: {cmd}")

        script = cmd[2]
        scripts.append(script)

        if "nvm which default" in script:
            if (nvm_bin / "node").exists():
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout=f"{nvm_bin / 'node'}\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(cmd, 3, stdout="", stderr="N/A")

        if not install_success:
            if check:
                raise subprocess.CalledProcessError(1, cmd)
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="failed")

        seed_installed_tools(codex=install_codex, claude=install_claude)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(bootstrap.shutil, "which", fake_which)
    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)
    return scripts


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


def test_root_curated_docs_match_packaged_template() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    template_root = repo_root / "src/scix/assets/template_root"
    mirrored_paths = [
        Path("README.md"),
        Path("requirements.txt"),
        Path("docs/AI_FOLDER_GUIDE.md"),
        Path("docs/img/scix_image.png"),
    ]

    for relative_path in mirrored_paths:
        source_path = repo_root / relative_path
        template_path = template_root / relative_path
        assert source_path.exists()
        assert template_path.exists()
        assert source_path.read_bytes() == template_path.read_bytes()

    source_readme = (repo_root / "README.md").read_text(encoding="utf-8")
    assert (
        '<img src="https://raw.githubusercontent.com/zoeyzyhu/scix/main/docs/img/scix_image.png"'
        in source_readme
    )  # noqa: E501
    assert "pip install -r requirements.txt" in source_readme
    assert "docs/AI_FOLDER_GUIDE.md" in source_readme
    assert not (template_root / "docs/img/scix_image_1.png").exists()


def test_scix_cheat_command_prints_curated_command_guide(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scix.cli import main

    result = main(["cheat"])

    assert result == 0
    output = capsys.readouterr().out
    assert "Start a new research workspace" in output
    assert "mkdir my-scix-work" in output
    assert "Contributor workflow" in output
    assert "pre-commit run --all-files" in output
    assert "Authenticate Codex" in output
    assert "┌" in output
    assert "└" in output


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


def test_sync_workspace_updates_packaged_template_docs_in_source_checkout(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    copy_template_paths(
        tmp_path / "src/scix/assets/template_root",
        ["README.md", "requirements.txt", "docs"],
    )
    source_readme = tmp_path / "README.md"
    template_readme = tmp_path / "src/scix/assets/template_root/README.md"
    source_requirements = tmp_path / "requirements.txt"
    template_requirements = tmp_path / "src/scix/assets/template_root/requirements.txt"
    extra_template_doc = tmp_path / "src/scix/assets/template_root/docs/img/scix_image_1.png"
    source_readme.write_text("updated root readme\n", encoding="utf-8")
    source_requirements.write_text("updated requirements\n", encoding="utf-8")
    extra_template_doc.parent.mkdir(parents=True, exist_ok=True)
    extra_template_doc.write_bytes(b"stale")

    with pytest.raises(CheckFailedError):
        sync_workspace(tmp_path, check=True)

    changed = sync_workspace(tmp_path)

    assert template_readme.read_text(encoding="utf-8") == "updated root readme\n"
    assert template_requirements.read_text(encoding="utf-8") == "updated requirements\n"
    assert template_readme in changed
    assert template_requirements in changed
    assert extra_template_doc in changed
    assert not extra_template_doc.exists()


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
    assert (tmp_path / ".claude/agents/student.md").exists()
    assert (tmp_path / ".codex/agents/student.toml").exists()
    assert (tmp_path / ".claude/agents/tester.md").exists()
    assert (tmp_path / ".codex/agents/tester.toml").exists()
    assert (tmp_path / "ai/generated/repos/kintera/AGENTS.md").exists()
    assert "implementer -> tester -> reviewer" in (tmp_path / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert "203 /learn" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "203 /learn" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")


def test_generated_student_role_requires_confirmation_before_skill_write(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    sync_workspace(tmp_path)

    codex_agent = (tmp_path / ".codex/agents/student.toml").read_text(encoding="utf-8")
    claude_agent = (tmp_path / ".claude/agents/student.md").read_text(encoding="utf-8")

    for content in [codex_agent, claude_agent]:
        assert "203 /learn" in content
        assert "starts with the exact literal `203 /learn`" in content
        assert "bare `/learn`" in content
        assert "Wait for explicit developer confirmation before editing files" in content
        assert "create or update `ai/skills/<skill-name>/SKILL.md`" in content
        assert "run `scix sync`" in content
        assert "valid YAML frontmatter" in content
        assert "lowercase hyphen-case" in content


def test_sync_workspace_generates_v116_codex_agent_schema(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    sync_workspace(tmp_path)

    fast_roles = ["explorer", "docs-researcher"]
    strong_roles = ["reviewer", "implementer", "tester", "student", "tutorial-designer"]

    for role_name in fast_roles:
        content = (tmp_path / f".codex/agents/{role_name}.toml").read_text(encoding="utf-8")
        assert f'name = "{role_name}"' in content
        assert 'developer_instructions = """' in content
        assert 'model = "gpt-5.4-mini"' in content
        assert "prompt =" not in content
        assert "model_hint =" not in content
        assert "tools =" not in content
        assert "web_search" not in content

    for role_name in strong_roles:
        content = (tmp_path / f".codex/agents/{role_name}.toml").read_text(encoding="utf-8")
        assert f'name = "{role_name}"' in content
        assert 'developer_instructions = """' in content
        assert "model =" not in content
        assert "prompt =" not in content
        assert "model_hint =" not in content
        assert "tools =" not in content
        assert "web_search" not in content

    docs_researcher = (tmp_path / ".claude/agents/docs-researcher.md").read_text(encoding="utf-8")
    assert "tools: read, search, web" not in docs_researcher


def test_sync_workspace_rejects_legacy_role_keys(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    roles_path = tmp_path / "ai/agents/roles.yaml"
    content = roles_path.read_text(encoding="utf-8")
    content = content.replace(
        "    developer_instructions: |",
        "    prompt: |\n      legacy instruction key\n    developer_instructions: |",
        1,
    )
    roles_path.write_text(content, encoding="utf-8")

    with pytest.raises(ScixError, match="deprecated key\\(s\\)"):
        sync_workspace(tmp_path)


def test_sync_workspace_copies_repo_overlays_into_existing_clone(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    (tmp_path / "repos/kintera").mkdir(parents=True)

    sync_workspace(tmp_path)

    assert (tmp_path / "repos/kintera/AGENTS.md").exists()
    assert (tmp_path / "repos/kintera/CLAUDE.md").exists()
    overlay_text = (tmp_path / "repos/kintera/AGENTS.md").read_text(encoding="utf-8")
    assert "exact validation command and result" in overlay_text


def test_sync_workspace_check_detects_stale_file(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    sync_workspace(tmp_path)
    (tmp_path / "AGENTS.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(CheckFailedError):
        sync_workspace(tmp_path, check=True)


def test_perform_up_rejects_non_empty_directory_without_force(tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")

    with pytest.raises(ScixError):
        perform_up(tmp_path, assume_yes=True, skip_repos=True)


def test_perform_up_rejects_repo_shaped_directory_without_force(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("developer checkout\n", encoding="utf-8")
    (tmp_path / "src/scix").mkdir(parents=True)

    with pytest.raises(ScixError):
        perform_up(tmp_path, assume_yes=True, skip_repos=True)


def test_perform_up_allows_directory_with_only_xenv(tmp_path: Path) -> None:
    (tmp_path / "xenv").mkdir()

    perform_up(tmp_path, assume_yes=True, skip_repos=True)

    assert (tmp_path / ".ai-root").exists()
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / "docs/AI_FOLDER_GUIDE.md").exists()
    assert (tmp_path / "docs/img/scix_image.png").exists()
    assert not (tmp_path / "docs/img/scix_image_1.png").exists()


def test_perform_up_force_allows_non_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")

    perform_up(tmp_path, assume_yes=True, force=True, skip_repos=True)

    assert (tmp_path / ".ai-root").exists()
    assert (tmp_path / "README.md").exists()


def test_perform_up_installs_missing_agent_clis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "_ensure_agent_clis", REAL_ENSURE_AGENT_CLIS)
    scripts = _configure_fake_agent_install(monkeypatch, tmp_path)
    workspace = tmp_path / "workspace"

    perform_up(workspace, assume_yes=True, skip_repos=True)

    install_scripts = [script for script in scripts if "npm install -g" in script]
    assert install_scripts
    install_script = install_scripts[-1]
    assert "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash" in (
        install_script
    )
    assert "nvm install --lts" in install_script
    assert "npm install -g @openai/codex" in install_script
    assert "npm install -g @anthropic-ai/claude-code" in install_script
    nvm_bin = tmp_path / ".nvm/versions/node/v22.9.0/bin"
    assert os.environ["PATH"].split(os.pathsep)[0] == str(nvm_bin)
    assert (nvm_bin / "codex").exists()
    assert (nvm_bin / "claude").exists()


def test_perform_dev_up_installs_missing_agent_clis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_dev_checkout(tmp_path)
    monkeypatch.setattr(bootstrap, "_ensure_agent_clis", REAL_ENSURE_AGENT_CLIS)
    scripts = _configure_fake_agent_install(monkeypatch, tmp_path)

    perform_dev_up(tmp_path, skip_repos=True)

    install_scripts = [script for script in scripts if "npm install -g" in script]
    assert install_scripts
    assert "npm install -g @openai/codex" in install_scripts[-1]
    assert "npm install -g @anthropic-ai/claude-code" in install_scripts[-1]


def test_agent_install_is_skipped_when_tools_are_already_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "_ensure_agent_clis", REAL_ENSURE_AGENT_CLIS)
    scripts = _configure_fake_agent_install(
        monkeypatch,
        tmp_path,
        preinstalled=True,
    )
    workspace = tmp_path / "workspace"

    perform_up(workspace, assume_yes=True, skip_repos=True)

    assert not any("curl -o-" in script for script in scripts)
    assert not any("npm install -g" in script for script in scripts)


def test_agent_install_failures_warn_but_do_not_raise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(bootstrap, "_ensure_agent_clis", REAL_ENSURE_AGENT_CLIS)
    _configure_fake_agent_install(monkeypatch, tmp_path, install_success=False)
    workspace = tmp_path / "workspace"

    perform_up(workspace, assume_yes=True, skip_repos=True)

    output = capsys.readouterr().out
    assert "Warning: scix could not finish installing nvm" in output
    assert "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash" in (
        output
    )
    assert "npm install -g @openai/codex" in output
    assert "npm install -g @anthropic-ai/claude-code" in output


def test_perform_dev_up_check_ignores_agent_cli_install_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_dev_checkout(tmp_path)
    _create_reference_repo_dirs(tmp_path)
    monkeypatch.setattr(bootstrap, "_ensure_agent_clis", REAL_ENSURE_AGENT_CLIS)
    _configure_fake_agent_install(monkeypatch, tmp_path, install_success=False)

    perform_dev_up(tmp_path, skip_repos=True, check=True)


def test_perform_dev_up_check_still_fails_for_other_doctor_issues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_dev_checkout(tmp_path)
    _create_reference_repo_dirs(tmp_path)
    skill_path = tmp_path / "ai/skills/repo-router/SKILL.md"
    skill_path.write_text("# broken\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "_ensure_agent_clis", REAL_ENSURE_AGENT_CLIS)
    _configure_fake_agent_install(monkeypatch, tmp_path, install_success=False)

    with pytest.raises(ScixError, match="Invalid skill file"):
        perform_dev_up(tmp_path, skip_repos=True, check=True)


def test_doctor_reports_invalid_skill_frontmatter(tmp_path: Path) -> None:
    copy_template_root(tmp_path)
    skill_path = tmp_path / "ai/skills/repo-router/SKILL.md"
    skill_path.write_text("# broken\n", encoding="utf-8")

    issues = doctor(tmp_path)

    assert any("Invalid skill file" in issue for issue in issues)
    assert not any("xenv" in issue for issue in issues)
    assert not any("pyenv" in issue for issue in issues)


def test_doctor_uses_nvm_based_agent_install_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_template_root(tmp_path)
    _create_reference_repo_dirs(tmp_path)
    real_which = shutil.which

    def fake_which(name: str) -> str | None:
        if name in {"codex", "claude"}:
            return None
        return real_which(name)

    monkeypatch.setattr(bootstrap.shutil, "which", fake_which)

    issues = doctor(tmp_path)

    assert any("nvm install --lts" in issue for issue in issues)
    assert any("@openai/codex" in issue for issue in issues)
    assert any("@anthropic-ai/claude-code" in issue for issue in issues)


def test_doctor_skips_agent_diagnosis_when_one_agent_cli_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_template_root(tmp_path)
    _create_reference_repo_dirs(tmp_path)
    real_which = shutil.which

    def fake_which(name: str) -> str | None:
        if name == "codex":
            return "/fake/bin/codex"
        if name == "claude":
            return None
        return real_which(name)

    monkeypatch.setattr(bootstrap.shutil, "which", fake_which)

    issues = doctor(tmp_path)

    assert issues == []


def test_guidance_skips_agent_warnings_when_one_agent_cli_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_template_root(tmp_path)
    _create_reference_repo_dirs(tmp_path)
    real_which = shutil.which

    def fake_which(name: str) -> str | None:
        if name == "claude":
            return "/fake/bin/claude"
        if name == "codex":
            return None
        return real_which(name)

    monkeypatch.setattr(bootstrap.shutil, "which", fake_which)

    up_notes = up_guidance(tmp_path)
    dev_notes = dev_up_guidance(tmp_path)

    assert not any("No agent CLI detected" in note for note in up_notes)
    assert not any("Neither Codex nor Claude is on PATH" in note for note in up_notes)
    assert not any("No agent CLI detected" in note for note in dev_notes)
    assert not any("Neither Codex nor Claude is on PATH" in note for note in dev_notes)


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

    perform_dev_up(tmp_path, skip_repos=True)

    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "custom contributor README\n"
    assert (tmp_path / "ai/policy/workspace.md").read_text(
        encoding="utf-8"
    ) == "custom workspace policy\n"
    assert (tmp_path / ".ai-root").exists()
    assert (tmp_path / "repos/README.md").exists()
    assert (tmp_path / "workspace/README.md").exists()
    assert (tmp_path / ".codex/config.toml").exists()
    assert (tmp_path / ".claude/settings.json").exists()


def test_scix_dev_command_bootstraps_contributor_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scix.cli import main

    copy_template_paths(tmp_path, ["ai"])
    (tmp_path / "src/scix").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'scix'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("custom contributor README\n", encoding="utf-8")
    (tmp_path / "ai/policy/workspace.md").write_text("custom workspace policy\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    result = main(["dev", "--skip-repos"])

    assert result == 0
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


def test_dev_setup_reports_missing_pyyaml_dependency() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    code = (
        "import os; import sys; "
        f"sys.path.insert(0, {str(repo_root / 'src').__repr__()}); "
        f"os.chdir({str(repo_root).__repr__()}); "
        "from scix.dev_setup import main; raise SystemExit(main(['--skip-repos']))"
    )
    result = subprocess.run(
        [sys.executable, "-S", "-c", code],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Missing dependency 'PyYAML'" in result.stdout
    assert "ModuleNotFoundError" not in result.stdout


def test_runtime_bootstrap_sources_use_nvm_and_do_not_reference_pyenv_or_sudo() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for relative_path in [
        Path("src/scix/bootstrap.py"),
        Path("src/scix/cli.py"),
        Path("src/scix/dev_setup.py"),
        Path("src/scix/constants.py"),
    ]:
        content = (repo_root / relative_path).read_text(encoding="utf-8").lower()
        assert "pyenv" not in content
        assert "sudo" not in content

    bootstrap_content = (repo_root / "src/scix/bootstrap.py").read_text(encoding="utf-8").lower()
    assert "nvm install --lts" in bootstrap_content
    assert "@openai/codex" in bootstrap_content
    assert "@anthropic-ai/claude-code" in bootstrap_content
