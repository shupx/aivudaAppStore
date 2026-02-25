from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException


def now_ts() -> int:
    return int(time.time())


def parse_json_field(raw: str, *, field_name: str, default: Any) -> Any:
    text = raw.strip() if raw else ""
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 不是合法 JSON: {exc}") from exc


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def normalize_platform(os_name: str, arch: str) -> tuple[str, str]:
    normalized_os = os_name.strip().lower()
    normalized_arch = arch.strip().lower()
    if not normalized_os or not normalized_arch:
        raise HTTPException(status_code=400, detail="os 与 arch 不能为空")
    return normalized_os, normalized_arch


def validate_runtime(runtime: str) -> str:
    normalized = runtime.strip().lower()
    if normalized not in {"host", "docker", "podman"}:
        raise HTTPException(status_code=400, detail="runtime 仅支持 host/docker/podman")
    return normalized
