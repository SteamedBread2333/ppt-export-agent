from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ppt_expert.config import AgentConfig
from ppt_expert.models import ImageRequest

SchemaT = TypeVar("SchemaT", bound=BaseModel)
StructuredCallable = Callable[[str, type[SchemaT]], SchemaT | dict[str, Any] | Awaitable[Any]]
ImageCallable = Callable[[ImageRequest, Path], str | Path | bytes | Awaitable[Any]]


@dataclass(slots=True)
class HostRuntime:
    """Capabilities borrowed from the Agent host.

    `model` is the exact model object already owned by the host. No provider is
    constructed here. Hosts with a non-LangChain Agent can supply
    `structured_generate` to call that Agent in its native way.
    """

    model: Any | None = None
    structured_generate: StructuredCallable | None = None
    image_generate: ImageCallable | None = None

    async def generate_structured(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        current_prompt = prompt
        last_error: Exception | None = None
        for attempt in range(2):
            result = await self._invoke_structured(current_prompt, schema)
            try:
                return self._coerce(result, schema)
            except (ValidationError, ValueError, TypeError) as exc:
                last_error = exc
                current_prompt = (
                    f"{prompt}\n\n上次输出未通过 {schema.__name__} 校验：{exc}。"
                    "请只返回满足结构约束的完整结果。"
                )
        raise ValueError(f"Host output failed {schema.__name__} validation") from last_error

    async def _invoke_structured(self, prompt: str, schema: type[SchemaT]) -> Any:
        if self.structured_generate is not None:
            result = self.structured_generate(prompt, schema)
            return await result if inspect.isawaitable(result) else result

        if self.model is None:
            raise RuntimeError("HostRuntime requires model or structured_generate")

        if hasattr(self.model, "with_structured_output"):
            runnable = self.model.with_structured_output(schema)
            result = (
                await runnable.ainvoke(prompt)
                if hasattr(runnable, "ainvoke")
                else runnable.invoke(prompt)
            )
            return result

        if callable(self.model):
            result = self.model(prompt, schema)
            return await result if inspect.isawaitable(result) else result

        raise TypeError("Host model must support with_structured_output() or be callable")

    async def generate_image(self, request: ImageRequest, output_path: Path) -> Path | None:
        if self.image_generate is None:
            return None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = self.image_generate(request, output_path)
        result = await result if inspect.isawaitable(result) else result
        if isinstance(result, bytes):
            output_path.write_bytes(result)
            return output_path.resolve()
        if isinstance(result, (str, Path)):
            return Path(result).expanduser().resolve()
        if result is None and output_path.exists():
            return output_path.resolve()
        raise TypeError("Host image tool must return bytes, a path, or write output_path")

    @staticmethod
    def _coerce(result: Any, schema: type[SchemaT]) -> SchemaT:
        if isinstance(result, schema):
            return result
        if isinstance(result, BaseModel):
            return schema.model_validate(result.model_dump())
        if isinstance(result, str):
            return schema.model_validate(json.loads(result))
        return schema.model_validate(result)


@dataclass(frozen=True, slots=True)
class GraphContext:
    """Per-invocation dependencies; LangGraph never writes this to checkpoints."""

    host: HostRuntime
    config: AgentConfig
