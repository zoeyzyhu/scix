"""Generation helpers for Codex and Claude workspace files."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from .constants import REQUIRED_ROOT_PATHS, ROOT_MARKER
from .exceptions import CheckFailedError, ScixError

AUTO_GEN_HEADER = "<!-- AUTO-GENERATED FILE. EDIT ai/policy/* OR ai/agents/roles.yaml INSTEAD. -->"
EDITABLE_AI_DIRS = ("agents", "hooks", "policy", "skills")
PACKAGED_TEMPLATE_AI = Path("src/scix/assets/template_root/ai")
PACKAGED_GENERATED_PLACEHOLDER = Path("generated/repos/.gitkeep")


def find_workspace_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ROOT_MARKER).exists():
            return candidate
    raise ScixError(f"Could not find {ROOT_MARKER} from {current}")


def ensure_workspace_shape(root: Path) -> None:
    missing = [path for path in REQUIRED_ROOT_PATHS if not (root / path).exists()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise ScixError(f"Workspace is missing required files: {joined}")


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ScixError(f"Expected a mapping in {path}")
    return data


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def sync_workspace(root: Path | None = None, check: bool = False) -> list[Path]:
    root = find_workspace_root(root)
    ensure_workspace_shape(root)

    changed: list[Path] = []
    _sync_packaged_template_ai(root, changed, check)

    repo_map = load_yaml(root / "ai/policy/repos.yaml")
    roles = load_yaml(root / "ai/agents/roles.yaml").get("roles", {})
    workspace_md = read_text(root / "ai/policy/workspace.md")
    rules_md = read_text(root / "ai/policy/rules.md")
    commands_md = read_text(root / "ai/policy/commands.md")
    skills_dir = root / "ai/skills"
    skills = sorted(path.name for path in skills_dir.iterdir() if path.is_dir())

    _write_or_check(
        root / "AGENTS.md",
        render_workspace_doc(
            tool_name="Codex",
            title="AGENTS.md",
            workspace_md=workspace_md,
            rules_md=rules_md,
            commands_md=commands_md,
            repo_map=repo_map,
            skills=skills,
        ),
        changed,
        check,
    )
    _write_or_check(
        root / "CLAUDE.md",
        render_workspace_doc(
            tool_name="Claude",
            title="CLAUDE.md",
            workspace_md=workspace_md,
            rules_md=rules_md,
            commands_md=commands_md,
            repo_map=repo_map,
            skills=skills,
        ),
        changed,
        check,
    )
    _write_or_check(root / ".codex/config.toml", render_codex_config(), changed, check)
    _write_or_check(
        root / ".claude/settings.json",
        render_claude_settings(),
        changed,
        check,
    )

    _sync_generated_tree(skills_dir, root / ".agents/skills", changed, check)
    _sync_generated_tree(skills_dir, root / ".claude/skills", changed, check)

    for role_name, spec in sorted(roles.items()):
        _write_or_check(
            root / ".codex/agents" / f"{role_name}.toml",
            render_codex_agent(role_name, spec),
            changed,
            check,
        )
        _write_or_check(
            root / ".claude/agents" / f"{role_name}.md",
            render_claude_agent(role_name, spec),
            changed,
            check,
        )

    for repo_name, spec in sorted((repo_map.get("repos") or {}).items()):
        overlay_dir = root / "ai/generated/repos" / repo_name
        agents_text = render_repo_overlay(repo_name, spec, tool_name="Codex")
        claude_text = render_repo_overlay(repo_name, spec, tool_name="Claude")
        _write_or_check(overlay_dir / "AGENTS.md", agents_text, changed, check)
        _write_or_check(overlay_dir / "CLAUDE.md", claude_text, changed, check)

        repo_root = root / (spec.get("path") or f"repos/{repo_name}")
        if repo_root.exists() and repo_root.is_dir():
            _write_or_check(repo_root / "AGENTS.md", agents_text, changed, check)
            _write_or_check(repo_root / "CLAUDE.md", claude_text, changed, check)

    return changed


def _sync_packaged_template_ai(root: Path, changed: list[Path], check: bool) -> None:
    template_ai = root / PACKAGED_TEMPLATE_AI
    if not template_ai.exists():
        return

    for directory_name in EDITABLE_AI_DIRS:
        _sync_text_tree(
            root / "ai" / directory_name,
            template_ai / directory_name,
            changed,
            check,
        )

    generated_dir = template_ai / "generated/repos"
    _write_or_check(generated_dir / ".gitkeep", "", changed, check)
    for extra_path in sorted(path for path in generated_dir.rglob("*") if path.is_file()):
        if extra_path.relative_to(generated_dir) == Path(".gitkeep"):
            continue
        _remove_or_check(extra_path, changed, check)
    _prune_empty_dirs(generated_dir)


def _sync_text_tree(source_dir: Path, target_dir: Path, changed: list[Path], check: bool) -> None:
    source_files = sorted(path for path in source_dir.rglob("*") if path.is_file())
    target_files = {
        path.relative_to(target_dir): path for path in target_dir.rglob("*") if path.is_file()
    }

    for source_path in source_files:
        relative_path = source_path.relative_to(source_dir)
        _write_or_check(
            target_dir / relative_path,
            source_path.read_text(encoding="utf-8"),
            changed,
            check,
        )
        target_files.pop(relative_path, None)

    for extra_path in sorted(target_files.values()):
        _remove_or_check(extra_path, changed, check)
    _prune_empty_dirs(target_dir)


def _remove_or_check(path: Path, changed: list[Path], check: bool) -> None:
    if check:
        raise CheckFailedError(f"Generated file is stale: {path}")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    changed.append(path)


def render_workspace_doc(
    *,
    tool_name: str,
    title: str,
    workspace_md: str,
    rules_md: str,
    commands_md: str,
    repo_map: dict,
    skills: list[str],
) -> str:
    repos = repo_map.get("repos") or {}
    lines = [
        AUTO_GEN_HEADER,
        f"# {title}",
        "",
        f"This file is generated for {tool_name}.",
        "",
        "## Workspace Purpose",
        workspace_md,
        "",
        "## Hard Rules",
        rules_md,
        "",
        "## Repo Routing",
    ]
    for repo_name, spec in sorted(repos.items()):
        owns = ", ".join(spec.get("owns") or [])
        path = spec.get("path", f"repos/{repo_name}")
        lines.append(f"- `{repo_name}` at `{path}` owns: {owns}")
        for hint in spec.get("consult_when") or []:
            lines.append(f"  consult when: {hint}")
    lines.extend(
        [
            "",
            "## Common Commands",
            commands_md,
            "",
            "## Shared Skills",
        ]
    )
    for skill in skills:
        lines.append(f"- `{skill}`")
    return "\n".join(lines).strip() + "\n"


def render_repo_overlay(repo_name: str, spec: dict, *, tool_name: str) -> str:
    owns = spec.get("owns") or []
    consult = spec.get("consult_when") or []
    notes = spec.get("notes") or []
    lines = [
        AUTO_GEN_HEADER,
        f"# Repo Policy: {repo_name}",
        "",
        f"This file is generated for {tool_name}.",
        "",
        "## This Repo Owns",
    ]
    for item in owns:
        lines.append(f"- {item}")
    lines.extend(["", "## Inspect This Repo First When"])
    for item in consult:
        lines.append(f"- {item}")
    if notes:
        lines.extend(["", "## Notes"])
        for item in notes:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Guardrails",
            "- Modify this repo only when it is the primary repo for the task.",
            "- Read neighboring tests and examples before making changes.",
            "- Report cross-repo compatibility risks in your summary.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_codex_config() -> str:
    return (
        'model = "gpt-5.4"\n'
        'approval_policy = "on-request"\n'
        'sandbox_mode = "workspace-write"\n'
        'project_root_markers = [".ai-root", ".git"]\n'
        "project_doc_max_bytes = 65536\n"
    )


def render_claude_settings() -> str:
    payload = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "./ai/hooks/pre_tool_guard.sh"}],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Edit",
                    "hooks": [{"type": "command", "command": "./ai/hooks/post_edit_format.sh"}],
                }
            ],
            "Stop": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": "./ai/hooks/session_context.sh"}],
                }
            ],
        }
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_codex_agent(role_name: str, spec: dict) -> str:
    description = spec.get("purpose", "")
    tools = spec.get("tools") or []
    sandbox = spec.get("sandbox", "workspace-write")
    model_hint = spec.get("model_hint", "default")
    prompt = spec.get("prompt", "")
    tools_list = ", ".join(f'"{item}"' for item in tools)
    return (
        f'description = "{description}"\n'
        f'sandbox_mode = "{sandbox}"\n'
        f'model_hint = "{model_hint}"\n'
        f"tools = [{tools_list}]\n"
        'prompt = """\n'
        f"{prompt}\n"
        '"""\n'
    )


def render_claude_agent(role_name: str, spec: dict) -> str:
    tools = ", ".join(spec.get("tools") or [])
    description = spec.get("purpose", "")
    prompt = (spec.get("prompt") or "").strip()
    return f"---\nname: {role_name}\ndescription: {description}\ntools: {tools}\n---\n\n{prompt}\n"


def _prune_empty_dirs(root: Path) -> None:
    directories = sorted(
        (candidate for candidate in root.rglob("*") if candidate.is_dir()),
        reverse=True,
    )
    for path in directories:
        if not any(path.iterdir()):
            path.rmdir()


def _write_or_check(path: Path, content: str, changed: list[Path], check: bool) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        return
    if check:
        raise CheckFailedError(f"Generated file is stale or missing: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if path.suffix == ".sh":
        path.chmod(0o755)
    changed.append(path)


def _sync_generated_tree(source: Path, target: Path, changed: list[Path], check: bool) -> None:
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        destination = target / relative
        if path.is_dir():
            if not check:
                destination.mkdir(parents=True, exist_ok=True)
            continue
        expected = path.read_text(encoding="utf-8")
        _write_or_check(destination, expected, changed, check)
