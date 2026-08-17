from pathlib import Path

import pytest

from continuity_film_studio.io import write_json
from continuity_film_studio.models import StudioError
from continuity_film_studio.providers import higgsfield_args


def test_higgsfield_requires_explicit_attachment_mapping(tmp_path: Path) -> None:
    project = tmp_path / "production"
    (project / "config").mkdir(parents=True)
    write_json(project / "config/project.json", {"project_name": "Test"})
    prompt_path = project / "prompts/compiled/SC01-SH01-v001.json"
    reference = project / "references/cal.ref"
    reference.parent.mkdir(parents=True)
    reference.write_text("reference", encoding="utf-8")
    write_json(
        prompt_path,
        {
            "render_text": "Prompt",
            "attachments": [{"path": "references/cal.ref", "asset_tag": "@cal"}],
        },
    )
    with pytest.raises(StudioError, match="attachment map"):
        higgsfield_args(prompt_path, "live-model")

    args = higgsfield_args(prompt_path, "live-model", {"references/cal.ref": "--image"})
    assert args[-2:] == ["--image", str(reference)]


def test_higgsfield_rejects_non_flag_attachment_mapping(tmp_path: Path) -> None:
    project = tmp_path / "production"
    (project / "config").mkdir(parents=True)
    write_json(project / "config/project.json", {"project_name": "Test"})
    prompt_path = project / "prompts/compiled/SC01-SH01-v001.json"
    reference = project / "references/cal.ref"
    reference.parent.mkdir(parents=True)
    reference.write_text("reference", encoding="utf-8")
    write_json(prompt_path, {"render_text": "Prompt", "attachments": [{"path": "references/cal.ref"}]})
    with pytest.raises(StudioError, match="missing a CLI flag"):
        higgsfield_args(prompt_path, "live-model", {"references/cal.ref": "image"})

    with pytest.raises(StudioError, match="reserved CLI flag"):
        higgsfield_args(prompt_path, "live-model", {"references/cal.ref": "--prompt"})
