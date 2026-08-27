from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Self

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from ppt_expert.config import AgentConfig
from ppt_expert.graph import build_graph
from ppt_expert.runtime import GraphContext, HostRuntime


class PPTExpertAgent:
    def __init__(self, host_runtime: HostRuntime, config: AgentConfig | None = None) -> None:
        self.runtime = host_runtime
        self.config = config or AgentConfig()
        self._context = GraphContext(host=self.runtime, config=self.config)
        self._saver_context = None
        self._graph = None

    async def __aenter__(self) -> Self:
        await self._ensure_graph()
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.close()

    async def start(
        self,
        request: str,
        *,
        project_name: str | None = None,
        thread_id: str | None = None,
        template_path: str | Path | None = None,
        reference_images: Iterable[str | Path] = (),
    ) -> dict[str, Any]:
        graph = await self._ensure_graph()
        thread_id = thread_id or uuid.uuid4().hex
        safe_name = _safe_name(project_name or _guess_name(request))
        project_dir = (self.config.output_root / f"{safe_name}-{thread_id[:8]}").resolve()
        project_dir.mkdir(parents=True, exist_ok=True)
        template = _reference_path(template_path, {".pptx"}) if template_path else None
        images = [
            _reference_path(path, {".png", ".jpg", ".jpeg", ".webp"})
            for path in reference_images
        ]
        result = await graph.ainvoke(
            {
                "request": request,
                "project_name": safe_name,
                "project_dir": str(project_dir),
                "template_path": template,
                "reference_images": images,
            },
            config=self._run_config(thread_id),
            context=self._context,
        )
        return _response(thread_id, result)

    async def resume(self, thread_id: str, value: Any) -> dict[str, Any]:
        graph = await self._ensure_graph()
        result = await graph.ainvoke(
            Command(resume=value),
            config=self._run_config(thread_id),
            context=self._context,
        )
        return _response(thread_id, result)

    async def state(self, thread_id: str) -> dict[str, Any]:
        graph = await self._ensure_graph()
        snapshot = await graph.aget_state(self._run_config(thread_id))
        return dict(snapshot.values)

    async def close(self) -> None:
        if self._saver_context is not None:
            await self._saver_context.__aexit__(None, None, None)
            self._saver_context = None
            self._graph = None

    async def _ensure_graph(self):
        if self._graph is None:
            self.config.ensure_directories()
            checkpoint = str(self.config.checkpoint_path.expanduser().resolve())
            self._saver_context = AsyncSqliteSaver.from_conn_string(checkpoint)
            saver = await self._saver_context.__aenter__()
            self._graph = build_graph(saver)
        return self._graph

    @staticmethod
    def _run_config(thread_id: str) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": thread_id}}


def create_ppt_agent(
    host_runtime: HostRuntime, config: AgentConfig | None = None
) -> PPTExpertAgent:
    return PPTExpertAgent(host_runtime=host_runtime, config=config)


def _response(thread_id: str, result: dict[str, Any]) -> dict[str, Any]:
    interrupts = result.get("__interrupt__", ())
    if interrupts:
        return {
            "status": "interrupted",
            "thread_id": thread_id,
            "request": interrupts[0].value,
        }
    return {
        "status": "completed",
        "thread_id": thread_id,
        "artifacts": result.get("artifacts", {}),
        "validation": result.get("validation", {}),
    }


def _guess_name(request: str) -> str:
    first_line = request.strip().splitlines()[0] if request.strip() else "presentation"
    return first_line[:40]


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value, flags=re.UNICODE).strip("-_")
    return cleaned or "presentation"


def _reference_path(value: str | Path, extensions: set[str]) -> str:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Reference file does not exist: {path}")
    if path.suffix.lower() not in extensions:
        allowed = ", ".join(sorted(extensions))
        raise ValueError(f"Unsupported reference file {path.name}; expected {allowed}")
    return str(path)
