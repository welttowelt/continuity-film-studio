from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import test_project

import continuity_film_studio.heygen as heygen
from continuity_film_studio.cli import build_parser, run
from continuity_film_studio.io import read_json, write_json
from continuity_film_studio.models import StudioError
from continuity_film_studio.project import compile_prompt


def _forbid_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    def _refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the HeyGen API must not be called here")

    monkeypatch.setattr(heygen, "_request", _refuse)


def _configure_ralph(project: Path) -> None:
    heygen.configure_heygen(
        project,
        avatar_id="lk_ralph_look_1",
        voice_id="v_ralph_voice",
        avatar_name="Ralph",
        real_person=False,
        identity_authorized=False,
    )


def _talking_project(tmp_path: Path) -> tuple[Path, Path]:
    project, shot_path = test_project.ready_project(tmp_path)
    card = read_json(shot_path)
    card["dialogue"] = "The pipeline is the memory."
    write_json(shot_path, card)
    _configure_ralph(project)
    prompt_path = compile_prompt(project, shot_path)
    return project, prompt_path


def test_configure_refuses_unauthorized_real_person(tmp_path: Path) -> None:
    project, _ = test_project.ready_project(tmp_path)
    with pytest.raises(StudioError, match="identity authorization"):
        heygen.configure_heygen(
            project,
            avatar_id="lk_colleague",
            voice_id="v_colleague",
            avatar_name="Colleague",
            real_person=True,
            identity_authorized=False,
        )


def test_payload_refuses_presenter_without_rights_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, shot_path = test_project.ready_project(tmp_path)
    card = read_json(shot_path)
    card["dialogue"] = "Hello."
    write_json(shot_path, card)
    config_path = project / "config/project.json"
    config = read_json(config_path)
    config.setdefault("providers", {})["heygen"] = {"avatar_id": "lk_x", "voice_id": "v_x"}
    write_json(config_path, config)
    prompt_path = compile_prompt(project, shot_path)
    _forbid_requests(monkeypatch)
    with pytest.raises(StudioError, match="identity-rights record"):
        heygen.heygen_video_payload(prompt_path)


def test_payload_uses_configured_presenter_and_verbatim_dialogue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, prompt_path = _talking_project(tmp_path)
    _forbid_requests(monkeypatch)
    payload = heygen.heygen_video_payload(prompt_path)
    assert payload["type"] == "avatar"
    assert payload["avatar_id"] == "lk_ralph_look_1"
    assert payload["voice_id"] == "v_ralph_voice"
    assert payload["script"] == "The pipeline is the memory."
    assert payload["resolution"] == "1080p"
    assert payload["aspect_ratio"] == "16:9"
    assert payload["title"] == "SC01-SH01 v001"


def test_payload_refuses_silent_shots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project, shot_path = test_project.ready_project(tmp_path)
    _configure_ralph(project)
    prompt_path = compile_prompt(project, shot_path)
    _forbid_requests(monkeypatch)
    with pytest.raises(StudioError, match="empty dialogue"):
        heygen.heygen_video_payload(prompt_path)


def test_payload_requires_configured_presenter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project, shot_path = test_project.ready_project(tmp_path)
    card = read_json(shot_path)
    card["dialogue"] = "Hello."
    write_json(shot_path, card)
    prompt_path = compile_prompt(project, shot_path)
    _forbid_requests(monkeypatch)
    with pytest.raises(StudioError, match="heygen-configure"):
        heygen.heygen_video_payload(prompt_path)


def test_payload_inherits_the_source_state_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project, prompt_path = _talking_project(tmp_path)
    shot_path = project / "prompts/shot-cards/SC01-SH01.json"
    card = read_json(shot_path)
    card["acting"] = "Cal narrows his eyes."
    write_json(shot_path, card)
    _forbid_requests(monkeypatch)
    with pytest.raises(StudioError, match="source state changed"):
        heygen.heygen_video_payload(prompt_path)


def test_execute_posts_the_gated_payload_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project, prompt_path = _talking_project(tmp_path)
    calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def _record(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        calls.append((method, path, payload))
        return {"data": {"video_id": "v_test_123", "status": "waiting"}}

    monkeypatch.setattr(heygen, "_request", _record)
    result = heygen.execute_heygen(prompt_path)
    assert result == {"video_id": "v_test_123", "status": "waiting"}
    assert len(calls) == 1
    method, path, payload = calls[0]
    assert (method, path) == ("POST", "/v3/videos")
    assert payload is not None and payload["script"] == "The pipeline is the memory."
    submissions = heygen.read_jsonl(heygen._submissions_path(project))
    assert len(submissions) == 1
    assert submissions[0]["video_id"] == "v_test_123"
    assert submissions[0]["shot_id"] == "SC01-SH01"


def test_doctor_reports_missing_key_without_calling_the_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(heygen.API_KEY_ENV, raising=False)
    _forbid_requests(monkeypatch)
    report = heygen.heygen_doctor()
    assert report["configured"] is False
    assert heygen.API_KEY_ENV in report["next"]


def test_configure_rejects_blank_ids(tmp_path: Path) -> None:
    project, _ = test_project.ready_project(tmp_path)
    with pytest.raises(StudioError, match="non-empty avatar id"):
        heygen.configure_heygen(
            project,
            avatar_id=" ",
            voice_id="v_x",
            avatar_name=None,
            real_person=False,
            identity_authorized=False,
        )


RALPH_ENGINE_SETTINGS = {
    "model": "eleven_multilingual_v2",
    "stability": 0.35,
    "similarity_boost": 0.8,
    "style": 0.2,
    "use_speaker_boost": True,
}


def test_configure_stores_voice_tuning_and_payload_carries_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, shot_path = test_project.ready_project(tmp_path)
    card = read_json(shot_path)
    card["dialogue"] = "The pipeline is the memory."
    write_json(shot_path, card)
    heygen.configure_heygen(
        project,
        avatar_id="lk_ralph_look_1",
        voice_id="v_ralph_voice",
        avatar_name="Ralph",
        real_person=False,
        identity_authorized=False,
        speed=1.1,
        pitch=-2,
        engine_settings=dict(RALPH_ENGINE_SETTINGS),
        expressiveness="high",
    )
    prompt_path = compile_prompt(project, shot_path)
    _forbid_requests(monkeypatch)
    payload = heygen.heygen_video_payload(prompt_path)
    assert payload["voice_settings"] == {
        "speed": 1.1,
        "pitch": -2,
        "engine_settings": {"engine_type": "elevenlabs", **RALPH_ENGINE_SETTINGS},
    }
    assert payload["expressiveness"] == "high"


def test_payload_omits_tuning_that_was_never_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, prompt_path = _talking_project(tmp_path)
    _forbid_requests(monkeypatch)
    payload = heygen.heygen_video_payload(prompt_path)
    assert "voice_settings" not in payload
    assert "expressiveness" not in payload


@pytest.mark.parametrize(
    ("tuning", "message"),
    [
        ({"speed": 1.6}, "voice speed"),
        ({"speed": True}, "voice speed"),
        ({"pitch": 51}, "voice pitch"),
        ({"expressiveness": "maximum"}, "expressiveness must be one of"),
        ({"engine_settings": {"reverb": 1}}, "unsupported engine settings keys: reverb"),
        ({"engine_settings": {"engine_type": "fish"}}, "elevenlabs engine only"),
        ({"engine_settings": {"stability": 1.5}}, "engine settings stability"),
        ({"engine_settings": {"model": " "}}, "non-empty string"),
        ({"engine_settings": {"use_speaker_boost": "yes"}}, "true or false"),
        ({"engine_settings": []}, "JSON object"),
    ],
)
def test_configure_rejects_invalid_voice_tuning(tmp_path: Path, tuning: dict[str, Any], message: str) -> None:
    project, _ = test_project.ready_project(tmp_path)
    _configure_ralph(project)
    before = read_json(project / "config/project.json")
    with pytest.raises(StudioError, match=message):
        heygen.configure_heygen(
            project,
            avatar_id="lk_ralph_look_1",
            voice_id="v_ralph_voice",
            avatar_name="Ralph",
            real_person=False,
            identity_authorized=False,
            **tuning,
        )
    assert read_json(project / "config/project.json") == before


def test_payload_rechecks_hand_edited_voice_tuning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project, shot_path = test_project.ready_project(tmp_path)
    card = read_json(shot_path)
    card["dialogue"] = "Hello."
    write_json(shot_path, card)
    config_path = project / "config/project.json"
    config = read_json(config_path)
    config.setdefault("providers", {})["heygen"] = {
        "avatar_id": "lk_x",
        "voice_id": "v_x",
        "presenter_rights": {"real_person": False, "identity_authorized": False},
        "voice_settings": {"speed": 3.0},
    }
    write_json(config_path, config)
    prompt_path = compile_prompt(project, shot_path)
    _forbid_requests(monkeypatch)
    with pytest.raises(StudioError, match="voice speed"):
        heygen.heygen_video_payload(prompt_path)


def test_retuning_the_voice_invalidates_compiled_prompts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, prompt_path = _talking_project(tmp_path)
    _forbid_requests(monkeypatch)
    assert "voice_settings" not in heygen.heygen_video_payload(prompt_path)
    heygen.configure_heygen(
        project,
        avatar_id="lk_ralph_look_1",
        voice_id="v_ralph_voice",
        avatar_name="Ralph",
        real_person=False,
        identity_authorized=False,
        speed=0.9,
    )
    with pytest.raises(StudioError, match="source state changed"):
        heygen.heygen_video_payload(prompt_path)


def test_cli_configure_wires_voice_tuning_flags(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    project, _ = test_project.ready_project(tmp_path)
    argv = [
        "heygen-configure",
        str(project),
        "--avatar-id",
        "lk_ralph_look_1",
        "--voice-id",
        "v_ralph_voice",
        "--avatar-name",
        "Ralph",
        "--platform-persona",
        "--speed",
        "1.1",
        "--pitch",
        "-2",
        "--expressiveness",
        "high",
        "--engine-settings-json",
        '{"stability": 0.35, "use_speaker_boost": true}',
    ]
    assert run(build_parser().parse_args(argv)) == 0
    provider = read_json(project / "config/project.json")["providers"]["heygen"]
    assert provider["voice_settings"] == {
        "speed": 1.1,
        "pitch": -2.0,
        "engine_settings": {"engine_type": "elevenlabs", "stability": 0.35, "use_speaker_boost": True},
    }
    assert provider["expressiveness"] == "high"
    capsys.readouterr()


def test_cli_configure_rejects_invalid_engine_settings_json(tmp_path: Path) -> None:
    project, _ = test_project.ready_project(tmp_path)
    argv = [
        "heygen-configure",
        str(project),
        "--avatar-id",
        "lk_ralph_look_1",
        "--voice-id",
        "v_ralph_voice",
        "--platform-persona",
        "--engine-settings-json",
        "{not json",
    ]
    with pytest.raises(StudioError, match="not valid JSON"):
        run(build_parser().parse_args(argv))


def _record_submission(project: Path, video_id: str) -> None:
    heygen.append_jsonl(
        heygen._submissions_path(project),
        {"video_id": video_id, "shot_id": "SC01-SH01", "created_at": "2026-08-17T00:00:00+00:00"},
    )


def test_download_refuses_unfinished_videos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project, _ = test_project.ready_project(tmp_path)
    _record_submission(project, "v_test_123")

    def _processing(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"data": {"status": "processing"}}

    monkeypatch.setattr(heygen, "_request", _processing)
    with pytest.raises(StudioError, match="not ready to download"):
        heygen.download_heygen_video(project, "v_test_123")


def test_download_refuses_videos_without_a_gated_submission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _ = test_project.ready_project(tmp_path)
    _forbid_requests(monkeypatch)
    with pytest.raises(StudioError, match="no gated submission record"):
        heygen.download_heygen_video(project, "v_from_somewhere_else")


def test_download_rejects_traversal_video_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project, _ = test_project.ready_project(tmp_path)
    _forbid_requests(monkeypatch)
    with pytest.raises(StudioError, match="letters, digits"):
        heygen.download_heygen_video(project, "../../escape")
    with pytest.raises(StudioError, match="letters, digits"):
        heygen.download_heygen_video(project, "-rf")
