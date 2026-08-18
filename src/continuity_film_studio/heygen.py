from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .io import append_jsonl, read_json, read_jsonl, utc_now, write_json
from .models import StudioError
from .project import ensure_project, validate_render_prompt

API_BASE = "https://api.heygen.com"
API_KEY_ENV = "HEYGEN_API_KEY"
RESOLUTIONS = ("720p", "1080p", "4k")
ASPECT_RATIOS = ("16:9", "9:16", "4:5", "5:4", "1:1")
EXPRESSIVENESS_LEVELS = ("high", "medium", "low")
FIT_MODES = ("contain", "cover")
VOICE_SPEED_RANGE = (0.5, 1.5)
VOICE_PITCH_RANGE = (-50, 50)
ENGINE_UNIT_KEYS = ("stability", "similarity_boost", "style")


def _api_key() -> str:
    value = os.environ.get(API_KEY_ENV, "").strip()
    if not value:
        raise StudioError(
            f"set {API_KEY_ENV} in the environment first; the key value never belongs in project files"
        )
    return value


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=body,
        method=method,
        headers={
            "x-api-key": _api_key(),
            "accept": "application/json",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise StudioError(f"HeyGen API {exc.code} on {method} {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise StudioError(f"HeyGen API unreachable: {exc.reason}") from exc


def _unwrap(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data", raw)
    return data if isinstance(data, dict) else raw


def heygen_doctor() -> dict[str, Any]:
    if not os.environ.get(API_KEY_ENV, "").strip():
        return {
            "configured": False,
            "authenticated": False,
            "next": f"Create an API key in the HeyGen app settings and export it as {API_KEY_ENV}.",
        }
    account = _unwrap(_request("GET", "/v3/users/me"))
    subscription = account.get("subscription", {})
    credits = subscription.get("credits", {}) if isinstance(subscription, dict) else {}
    premium = credits.get("premium_credits", {}) if isinstance(credits, dict) else {}
    return {
        "configured": True,
        "authenticated": True,
        "plan": subscription.get("plan") if isinstance(subscription, dict) else None,
        "premium_credits_remaining": premium.get("remaining") if isinstance(premium, dict) else None,
        "next": None,
    }


def heygen_avatar_looks(group_id: str | None = None) -> list[dict[str, Any]]:
    looks: list[dict[str, Any]] = []
    token: str | None = None
    while True:
        query: dict[str, str] = {"limit": "50"}
        if group_id:
            query["group_id"] = group_id
        if token:
            query["token"] = token
        raw = _request("GET", f"/v3/avatars/looks?{urllib.parse.urlencode(query)}")
        rows = raw.get("data", [])
        looks.extend(row for row in rows if isinstance(row, dict))
        token = raw.get("next_token")
        if not raw.get("has_more") or not token:
            return looks


def heygen_voices() -> list[dict[str, Any]]:
    raw = _request("GET", "/v3/voices")
    rows = raw.get("data", [])
    return [row for row in rows if isinstance(row, dict)]


def _checked_number(value: Any, low: float, high: float, description: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise StudioError(f"{description} must be a number between {low} and {high}")
    return value


def _validated_engine_settings(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StudioError("engine settings must be a JSON object of ElevenLabs tuning fields")
    unknown = sorted(set(value) - {"engine_type", "model", *ENGINE_UNIT_KEYS, "use_speaker_boost"})
    if unknown:
        raise StudioError(f"unsupported engine settings keys: {', '.join(unknown)}")
    if value.get("engine_type", "elevenlabs") != "elevenlabs":
        raise StudioError("engine settings pass through to the elevenlabs engine only")
    settings: dict[str, Any] = {"engine_type": "elevenlabs"}
    if "model" in value:
        model = value["model"]
        if not isinstance(model, str) or not model.strip():
            raise StudioError("engine settings model must be a non-empty string")
        settings["model"] = model.strip()
    for key in ENGINE_UNIT_KEYS:
        if key in value:
            settings[key] = _checked_number(value[key], 0, 1, f"engine settings {key}")
    if "use_speaker_boost" in value:
        if not isinstance(value["use_speaker_boost"], bool):
            raise StudioError("engine settings use_speaker_boost must be true or false")
        settings["use_speaker_boost"] = value["use_speaker_boost"]
    return settings


def _validated_voice_settings(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StudioError("voice settings must be an object")
    unknown = sorted(set(value) - {"speed", "pitch", "engine_settings"})
    if unknown:
        raise StudioError(f"unsupported voice settings keys: {', '.join(unknown)}")
    if not value:
        raise StudioError("voice settings must set at least one of speed, pitch, or engine_settings")
    settings: dict[str, Any] = {}
    if "speed" in value:
        settings["speed"] = _checked_number(value["speed"], *VOICE_SPEED_RANGE, "voice speed")
    if "pitch" in value:
        settings["pitch"] = _checked_number(value["pitch"], *VOICE_PITCH_RANGE, "voice pitch")
    if "engine_settings" in value:
        settings["engine_settings"] = _validated_engine_settings(value["engine_settings"])
    return settings


def _validated_expressiveness(value: Any) -> str:
    if value not in EXPRESSIVENESS_LEVELS:
        raise StudioError(f"expressiveness must be one of: {', '.join(EXPRESSIVENESS_LEVELS)}")
    return value


def _validated_fit(value: Any) -> str:
    if value not in FIT_MODES:
        raise StudioError(f"fit must be one of: {', '.join(FIT_MODES)}")
    return value


def configure_heygen(
    project: Path,
    *,
    avatar_id: str,
    voice_id: str,
    avatar_name: str | None,
    real_person: bool,
    identity_authorized: bool,
    speed: float | None = None,
    pitch: float | None = None,
    engine_settings: dict[str, Any] | None = None,
    expressiveness: str | None = None,
    fit: str | None = None,
    caption_srt: bool = False,
) -> None:
    project = ensure_project(project)
    if not avatar_id.strip() or not voice_id.strip():
        raise StudioError("heygen configuration requires a non-empty avatar id and voice id")
    if real_person and not identity_authorized:
        raise StudioError(
            "a real-person presenter requires explicit identity authorization before it can be configured"
        )
    config_path = project / "config/project.json"
    config = read_json(config_path)
    providers = config.setdefault("providers", {})
    entry: dict[str, Any] = {
        "enabled": True,
        "avatar_id": avatar_id.strip(),
        "voice_id": voice_id.strip(),
        "avatar_name": avatar_name,
        "presenter_rights": {
            "real_person": real_person,
            "identity_authorized": identity_authorized,
        },
        "discover_live_catalog": True,
    }
    voice_settings: dict[str, Any] = {}
    if speed is not None:
        voice_settings["speed"] = speed
    if pitch is not None:
        voice_settings["pitch"] = pitch
    if engine_settings is not None:
        voice_settings["engine_settings"] = engine_settings
    if voice_settings:
        entry["voice_settings"] = _validated_voice_settings(voice_settings)
    if expressiveness is not None:
        entry["expressiveness"] = _validated_expressiveness(expressiveness)
    if fit is not None:
        entry["fit"] = _validated_fit(fit)
    if caption_srt:
        entry["caption"] = {"file_format": "srt"}
    providers["heygen"] = entry
    write_json(config_path, config)


def heygen_video_payload(prompt_path: Path, *, resolution: str = "1080p") -> dict[str, Any]:
    project, prompt = validate_render_prompt(prompt_path)
    card = read_json((project / prompt["source_shot_card"]).resolve())
    dialogue = str(card.get("dialogue", "")).strip()
    if not dialogue:
        raise StudioError(
            "the HeyGen lane renders performed dialogue and this shot card has an empty dialogue field; "
            "use the Higgsfield lane for silent shots"
        )
    if resolution not in RESOLUTIONS:
        raise StudioError(f"unsupported resolution: {resolution} (choose from {', '.join(RESOLUTIONS)})")
    config = read_json(project / "config/project.json")
    provider = config.get("providers", {}).get("heygen", {})
    chosen_avatar = str(provider.get("avatar_id") or "").strip()
    chosen_voice = str(provider.get("voice_id") or "").strip()
    if not chosen_avatar or not chosen_voice:
        raise StudioError("no HeyGen presenter is configured for this project. Run heygen-configure first")
    rights = provider.get("presenter_rights")
    if not isinstance(rights, dict):
        raise StudioError(
            "the configured HeyGen presenter has no identity-rights record. Rerun heygen-configure"
        )
    if rights.get("real_person") and not rights.get("identity_authorized"):
        raise StudioError("the configured presenter is a real person without identity authorization")
    aspect_ratio = config.get("working_defaults", {}).get("frame_format", "16:9")
    if aspect_ratio not in ASPECT_RATIOS:
        aspect_ratio = "16:9"
    payload: dict[str, Any] = {
        "type": "avatar",
        "avatar_id": chosen_avatar,
        "voice_id": chosen_voice,
        "script": dialogue,
        "title": f"{prompt['shot_id']} v{int(prompt['version']):03d}",
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "output_format": "mp4",
    }
    if provider.get("voice_settings") is not None:
        payload["voice_settings"] = _validated_voice_settings(provider["voice_settings"])
    if provider.get("expressiveness") is not None:
        payload["expressiveness"] = _validated_expressiveness(provider["expressiveness"])
    if provider.get("fit") is not None:
        payload["fit"] = _validated_fit(provider["fit"])
    caption = provider.get("caption")
    if caption is not None:
        if not isinstance(caption, dict) or caption.get("file_format") != "srt":
            raise StudioError('caption must be {"file_format": "srt"}')
        payload["caption"] = {"file_format": "srt"}
    return payload


def _submissions_path(project: Path) -> Path:
    return project / "docs/heygen-submissions.jsonl"


def execute_heygen(prompt_path: Path, *, resolution: str = "1080p") -> dict[str, Any]:
    payload = heygen_video_payload(prompt_path, resolution=resolution)
    project, prompt = validate_render_prompt(prompt_path)
    data = _unwrap(_request("POST", "/v3/videos", payload))
    video_id = data.get("video_id")
    if not video_id:
        raise StudioError(f"HeyGen did not return a video id: {json.dumps(data)[:200]}")
    append_jsonl(
        _submissions_path(project),
        {
            "video_id": video_id,
            "shot_id": prompt["shot_id"],
            "prompt_file": prompt.get("source_shot_card"),
            "prompt_sha256": prompt.get("render_text_sha256"),
            "avatar_id": payload["avatar_id"],
            "voice_id": payload["voice_id"],
            "created_at": utc_now(),
        },
    )
    return {"video_id": video_id, "status": data.get("status")}


def _clean_video_id(video_id: str) -> str:
    value = video_id.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise StudioError(
            "video id must start with a letter or digit and may contain only letters, digits, "
            "underscores, and hyphens"
        )
    return value


def heygen_video_status(video_id: str) -> dict[str, Any]:
    return _unwrap(_request("GET", f"/v3/videos/{_clean_video_id(video_id)}"))


def download_heygen_video(project: Path, video_id: str) -> Path:
    project = ensure_project(project)
    video_id = _clean_video_id(video_id)
    submissions = read_jsonl(_submissions_path(project))
    if not any(row.get("video_id") == video_id for row in submissions):
        raise StudioError(
            f"video {video_id} has no gated submission record in this project; "
            "only videos submitted through heygen-render --execute can enter generations/"
        )
    status = heygen_video_status(video_id)
    if status.get("status") != "completed":
        detail = status.get("failure_message") or status.get("status") or "unknown"
        raise StudioError(f"video {video_id} is not ready to download: {detail}")
    url = str(status.get("video_url", ""))
    if not url.startswith("https://"):
        raise StudioError(f"video {video_id} has no https download url")
    output_dir = project / "generations" / "heygen"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{video_id}.mp4"
    if output.exists():
        raise StudioError(f"download target already exists and will not be overwritten: {output}")
    temporary = output.with_suffix(".mp4.part")
    try:
        with urllib.request.urlopen(url, timeout=300) as response, temporary.open("wb") as handle:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                handle.write(chunk)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output
