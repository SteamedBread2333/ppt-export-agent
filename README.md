# PPT Expert Agent

一个由 LangGraph 编排、复用宿主 Agent 当前模型与图片工具的 PPT 制作 SDK。
它不会创建或配置 OpenAI、通义等模型 Client；调用方把自己已经在使用的模型对象
放进 `HostRuntime`，工作流用该模型完成提纲、风格、STORY、DESIGN 和图片提示词生成。

## 工作流

```text
提纲解析 → 四套风格 → 用户确认 → STORY/DESIGN → 先生成配图
        → python-pptx 排版 → 自动校验 → 有限修复 → 交付
```

风格确认使用 LangGraph `interrupt()`；状态保存在 SQLite，可以使用相同
`thread_id` 跨进程恢复。输出包括 `.pptx`、`STORY.md`、`DESIGN.md`、
风格预览和校验报告。

`HostRuntime` 通过 LangGraph 的 `context_schema` 在每次调用时注入，不会被序列化
到 SQLite checkpoint；checkpoint 仅保存可恢复的业务状态。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 在宿主 Agent 中使用

宿主使用 LangChain `BaseChatModel` 时，可以直接传入同一个模型实例：

```python
from pathlib import Path

from ppt_expert import AgentConfig, HostRuntime, create_ppt_agent

# host_model 是宿主已经创建并正在使用的模型，不由 PPT Agent 创建。
runtime = HostRuntime(
    model=host_model,
    # image_tool 也是宿主已有工具。它可以返回图片 bytes/路径，
    # 或直接将图片写入 output_path。
    image_generate=host_image_tool,
)
config = AgentConfig(output_root=Path("outputs"))

async with create_ppt_agent(runtime, config) as agent:
    pending = await agent.start(
        "制作一份 12 页的年度业务复盘，面向管理层",
        project_name="年度业务复盘",
    )
    # 把 pending["request"]["preview_paths"] 展示给用户并取得 A/B/C/D。
    result = await agent.resume(pending["thread_id"], "B")
    print(result["artifacts"]["pptx_path"])
```

### 关联模板或参考图片

用户可传入一个 `.pptx` 模板、若干参考图片，或同时传入两者：

```python
pending = await agent.start(
    "制作新品发布会 PPT",
    template_path="references/brand-template.pptx",
    reference_images=["references/key-visual.png", "references/poster.jpg"],
)
```

Agent 会提取模板的母版、字体和颜色，并从图片提取主色板，随后通过 Human in the
Loop 返回 `reference_confirmation`：

```python
# 直接采用参考风格和模板
result = await agent.resume(pending["thread_id"], {"action": "use"})

# 调整提取结果后采用
result = await agent.resume(
    pending["thread_id"],
    {
        "action": "adjust",
        "style": {"primary": "#123456", "accent": "#F2A900"},
    },
)

# 忽略参考内容，回到常规 A/B/C/D 风格选择
next_step = await agent.resume(pending["thread_id"], {"action": "ignore"})
```

确认使用 `.pptx` 模板后，生成器会清除模板示例页但保留其主题、母版和版式关系，
再创建新的 16:9 演示文稿。参考图片会直接决定提取色板，并作为确认界面的预览。

非 LangChain 宿主可把自己的 Agent 调用包装为一个 callable。这里不是另建模型
Client，而是把宿主的既有调用能力借给工作流：

```python
async def generate_with_host(prompt, schema):
    raw = await current_host_agent.run(prompt, response_schema=schema)
    return raw

async def generate_image_with_host(request, output_path):
    image_bytes = await current_host_agent.image_tool(
        prompt=request.prompt,
        width=request.width,
        height=request.height,
    )
    output_path.write_bytes(image_bytes)
    return output_path

runtime = HostRuntime(
    structured_generate=generate_with_host,
    image_generate=generate_image_with_host,
)
```

宿主没有生图工具时，Agent 会生成与锁定色板一致的抽象占位图，PPT 流程仍可完成。

## 本地验收

离线 demo 不调用任何模型 API：

```bash
ppt-expert demo --style A
pytest
```

带参考内容运行离线流程：

```bash
ppt-expert demo \
  --template references/brand-template.pptx \
  --reference-image references/key-visual.png \
  --reference-action use
```

重新校验已有任务：

```bash
ppt-expert validate outputs/<project-directory>
```

一次性从 `story.json`、`design.json` 与配图重建 PPTX 并校验（供宿主 Agent
文件驱动调用）：

```bash
ppt-expert rebuild outputs/<project-directory>
```

持续监听 `story.json`、`design.json` 与配图；发生变化后自动重建 PPTX 并重新校验：

```bash
ppt-expert watch outputs/<project-directory>
```

## 输出目录

```text
outputs/<project-thread>/
├── outline.json
├── STORY.md
├── DESIGN.md
├── story.json
├── design.json
├── references.json               # 关联参考时生成
├── reference-selection.json      # HITL 决策
├── style-previews/
├── assets/
├── <project>.pptx
├── VALIDATION.md
└── validation.json
```

若系统安装 LibreOffice，会尝试生成 PDF 预览；同时安装 `pdftoppm` 时还会逐页生成
PNG 预览。缺少这些外部程序不影响 PPTX 交付。

## 宿主能力契约

- 文本模型必须支持结构化输出。LangChain 模型使用
  `with_structured_output(PydanticSchema)`；其他宿主通过 `structured_generate` 返回
  Pydantic 模型、字典或 JSON 字符串。
- 图片工具接收 `ImageRequest` 和目标路径，返回图片 bytes、已有图片路径，或写入目标路径。
- 图片工具即使把 JPEG 数据写进 `.png` 路径，或改写为同名 `.jpg/.jpeg/.webp`，
  资产层也会用 Pillow 自动识别并规范化为真正的 PNG 后再交给渲染器。
- `HostRuntime` 不进入 LangGraph checkpoint，SQLite 中只保存可序列化业务状态。
