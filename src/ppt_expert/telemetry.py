from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

PROMPT_VERSION = "v2"


def record_metric(project_dir: str | Path, node: str, started: float, **fields: Any) -> None:
    path = Path(project_dir) / "metrics.jsonl"
    payload = {
        "node": node,
        "prompt_version": PROMPT_VERSION,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        **fields,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def prompt_tokens(prompt: str) -> int:
    return max(1, len(prompt) // 4)


def prompt_cache_key(prompt: str, schema_name: str) -> str:
    digest = hashlib.sha256(f"{PROMPT_VERSION}:{schema_name}:{prompt}".encode()).hexdigest()
    return digest
