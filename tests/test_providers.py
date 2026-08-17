from pathlib import Path

import pytest

import continuity_film_studio.providers as providers
from continuity_film_studio.io import write_json
from continuity_film_studio.models import StudioError
from continuity_film_studio.providers import higgsfield_args


def test_higgsfield_requires_explicit_attachment_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "production"
    (project / "config").mkdir(parents=True)
    write_json(project / "config/project.json", {"project_name": "Test"})
    prompt_path = project / "prompts/compiled/SC01-SH01-v001.json"
    reference = project / "references/cal.ref"
    reference.parent.mkdir(parents=True)
    reference.write_text("reference", encoding="utf-8")
    prompt = {
        "render_text": "Prompt",
        "attachments": [{"path": "references/cal.ref", "asset_tag": "@cal"}],
    }
    write_json(prompt_path, prompt)
    monkeypatch.setattr(providers, "validate_render_prompt", lambda path: (project, prompt))
    with pytest.raises(StudioError, match="attachment map"):
        higgsfield_args(prompt_path, "live-model")

    args = higgsfield_args(prompt_path, "live-model", {"references/cal.ref": "--image"})
    assert args[-2:] == ["--image", str(reference)]


def test_higgsfield_rejects_non_flag_attachment_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "production"
    (project / "config").mkdir(parents=True)
    write_json(project / "config/project.json", {"project_name": "Test"})
    prompt_path = project / "prompts/compiled/SC01-SH01-v001.json"
    reference = project / "references/cal.ref"
    reference.parent.mkdir(parents=True)
    reference.write_text("reference", encoding="utf-8")
    prompt = {"render_text": "Prompt", "attachments": [{"path": "references/cal.ref"}]}
    write_json(prompt_path, prompt)
    monkeypatch.setattr(providers, "validate_render_prompt", lambda path: (project, prompt))
    with pytest.raises(StudioError, match="missing a CLI flag"):
        higgsfield_args(prompt_path, "live-model", {"references/cal.ref": "image"})

    with pytest.raises(StudioError, match="reserved CLI flag"):
        higgsfield_args(prompt_path, "live-model", {"references/cal.ref": "--prompt"})


def test_higgsfield_rejects_fabricated_prompt_without_project_gates(tmp_path: Path) -> None:
    project = tmp_path / "production"
    (project / "config").mkdir(parents=True)
    write_json(project / "config/project.json", {"project_name": "Test"})
    prompt_path = project / "prompts/compiled/SC01-SH01-v001.json"
    write_json(prompt_path, {"render_text": "Fabricated prompt", "attachments": []})

    with pytest.raises(StudioError, match="compiled prompt integrity"):
        higgsfield_args(prompt_path, "live-model")


def test_higgsfield_does_not_treat_generic_hf_binary_as_the_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(providers.shutil, "which", lambda name: "/fake/hf" if name == "hf" else None)
    monkeypatch.setattr(
        providers.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not run hf")),
    )

    assert providers.higgsfield_doctor()["installed"] is False
