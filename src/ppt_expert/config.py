from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AgentConfig:
    output_root: Path = field(default_factory=lambda: Path.cwd() / "outputs")
    checkpoint_path: Path = field(default_factory=lambda: Path.cwd() / ".ppt-expert.sqlite3")
    max_repair_attempts: int = 3

    def ensure_directories(self) -> None:
        self.output_root.expanduser().resolve().mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
