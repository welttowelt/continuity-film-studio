from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .io import read_json
from .models import StudioError

RESERVED_ATTACHMENT_FLAGS = {"--execute", "--json", "--model", "--prompt", "--wait"}


def _find_project_root(prompt_path: Path) -> Path:
    for candidate in prompt_path.resolve().parents:
        if (candidate / "config/project.json").is_file():
            return candidate
    raise StudioError("compiled prompt is not inside a continuity film project")


def higgsfield_doctor() -> dict[str, Any]:
    binary = shutil.which("higgsfield") or shutil.which("hf")
    if not binary:
        return {
            "installed": False,
            "authenticated": False,
            "next": "Install the official CLI, then run `higgsfield auth login`.",
        }
    version = subprocess.run([binary, "version"], check=False, capture_output=True, text=True)
    status = subprocess.run([binary, "account", "status"], check=False, capture_output=True, text=True)
    return {
        "installed": version.returncode == 0,
        "authenticated": status.returncode == 0,
        "version": version.stdout.strip() or version.stderr.strip(),
        "next": None if status.returncode == 0 else "Run `higgsfield auth login` interactively.",
    }


def higgsfield_model_catalog() -> Any:
    binary = shutil.which("higgsfield") or shutil.which("hf")
    if not binary:
        raise StudioError("Higgsfield CLI is not installed")
    result = subprocess.run([binary, "model", "list", "--json"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise StudioError(result.stderr.strip() or "unable to read Higgsfield model catalog")
    return json.loads(result.stdout)


def higgsfield_args(prompt_path: Path, model: str, attachment_map: dict[str, str] | None = None) -> list[str]:
    prompt = read_json(prompt_path)
    if not model:
        raise StudioError("a model name is required")
    attachments = prompt.get("attachments", [])
    if attachments and attachment_map is None:
        raise StudioError(
            "compiled prompt has reference attachments; provide a model-specific attachment map "
            "after inspecting `higgsfield model get <model> --json`"
        )
    binary = shutil.which("higgsfield") or shutil.which("hf") or "higgsfield"
    args = [
        binary,
        "generate",
        "create",
        model,
        "--prompt",
        prompt["render_text"],
        "--wait",
        "--json",
    ]
    project = _find_project_root(prompt_path)
    for attachment in attachments:
        relative_path = attachment["path"]
        flag = (attachment_map or {}).get(relative_path)
        if not flag or not flag.startswith("--"):
            raise StudioError(f"attachment map is missing a CLI flag for: {relative_path}")
        if flag in RESERVED_ATTACHMENT_FLAGS:
            raise StudioError(f"attachment map uses a reserved CLI flag: {flag}")
        absolute_path = (project / relative_path).resolve()
        try:
            absolute_path.relative_to(project.resolve())
        except ValueError as exc:
            raise StudioError(f"attachment path escapes the project: {relative_path}") from exc
        if not absolute_path.is_file():
            raise StudioError(f"attachment file is missing: {absolute_path}")
        args.extend([flag, str(absolute_path)])
    return args


def execute_higgsfield(prompt_path: Path, model: str, attachment_map: dict[str, str] | None = None) -> int:
    if not (shutil.which("higgsfield") or shutil.which("hf")):
        raise StudioError("Higgsfield CLI is not installed")
    args = higgsfield_args(prompt_path, model, attachment_map)
    return subprocess.run(args, check=False).returncode
