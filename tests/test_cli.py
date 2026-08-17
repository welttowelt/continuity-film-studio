from __future__ import annotations

import json
from pathlib import Path

import pytest

import continuity_film_studio.providers as providers
from continuity_film_studio.cli import build_parser, main, run
from continuity_film_studio.io import write_json
from continuity_film_studio.models import StudioError


def run_cli(*argv: str) -> int:
    return run(build_parser().parse_args(list(argv)))


def _forbidden_subprocess(*args: object, **kwargs: object) -> None:
    raise AssertionError("subprocess must not run during a preview")


def test_init_template_gate_and_audit_flow(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    project = tmp_path / "production"
    assert run_cli("init", str(project), "--name", "Test") == 0
    assert run_cli("shot-template", str(project), "--shot-id", "SC01-SH01") == 0
    with pytest.raises(StudioError, match="without --force"):
        run_cli("shot-template", str(project), "--shot-id", "SC01-SH01")
    assert run_cli("shot-template", str(project), "--shot-id", "SC01-SH01", "--force") == 0
    shot = project / "prompts/shot-cards/SC01-SH01.json"
    assert run_cli("gate", str(project), "--shot", str(shot)) == 2
    assert run_cli("audit", str(project)) == 0
    capsys.readouterr()


def test_template_commands_require_a_project(tmp_path: Path) -> None:
    with pytest.raises(StudioError, match="not a continuity film project"):
        run_cli("shot-template", str(tmp_path / "nowhere"), "--shot-id", "SC01-SH01")


def test_render_previews_without_subprocess_and_executes_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    project = tmp_path / "production"
    (project / "config").mkdir(parents=True)
    write_json(project / "config/project.json", {"project_name": "Test"})
    prompt_path = project / "prompts/compiled/SC01-SH01-v001.json"
    write_json(prompt_path, {"render_text": "Prompt", "attachments": []})

    monkeypatch.setattr(providers.subprocess, "run", _forbidden_subprocess)
    assert run_cli("higgsfield-render", "--prompt", str(prompt_path), "--model", "test-model") == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview[1:3] == ["generate", "create"]
    assert "--wait" in preview

    calls: list[list[str]] = []

    class _Result:
        returncode = 0

    def _record(args: list[str], check: bool = False) -> _Result:
        calls.append(list(args))
        return _Result()

    monkeypatch.setattr(providers.shutil, "which", lambda name: "/fake/higgsfield")
    monkeypatch.setattr(providers.subprocess, "run", _record)
    assert (
        run_cli("higgsfield-render", "--prompt", str(prompt_path), "--model", "test-model", "--execute") == 0
    )
    assert len(calls) == 1


def test_main_maps_studio_errors_to_exit_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["continuity-film", "audit", str(tmp_path / "missing")])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
