# PPT Expert Agent

<p align="center">
  <strong>A host-native, stateful presentation studio built with LangGraph.</strong>
</p>

<p align="center">
  Turn a brief, outline, reference image, or existing PowerPoint template into a
  polished, validated <code>.pptx</code>—without introducing another model provider.
</p>

<p align="center">
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="LangGraph" src="https://img.shields.io/badge/Orchestration-LangGraph-1C3C3C">
</p>

---

## Why PPT Expert

Most presentation generators stop at content. PPT Expert treats a deck as a
production workflow: narrative, art direction, visual assets, layout, validation,
revision, and delivery.

- **Host-native intelligence** — reuses the model and image tools already owned by
  the calling application.
- **Six-phase production** — intent, recipe, design system, guards, rendered
  review, XML delivery; not a one-shot text-to-slides pass.
- **Recipe-led art direction** — six style recipes (consulting, work report, civic,
  art market, editorial, history) plus an open brief, confirmed before typesetting.
- **Token and primitive rendering** — role-named colors, locked header/footer,
  native charts and modules via python-pptx.
- **Durable execution** — resumes interrupted or failed work from SQLite checkpoints.

The production contract is [`PPT_AGENT_SPEC.md`](PPT_AGENT_SPEC.md).

## Architecture

```text
User request
      │
      ▼
Parse intent (topic / audience / objective / form)
      │
      ▼
Match recipe + write style brief  ── HITL confirm
      │
      ▼
Survey environment (soffice / pdftoppm / PIL)
      │
      ▼
Plan narrative page roles
      │
      ▼
Encode tokens → compose primitives → build pptx
      │
      ▼
Text guards (zero-render) ── widen / rebuild
      │
      ▼
Montage review + representative pages
      │
      ▼
XML package audit
      │
      ▼
Delivery confirmation + cleanup
```

`HostRuntime` is injected through LangGraph's `context_schema`. It is never
serialized into a checkpoint; SQLite stores only portable workflow state.

Interrupts: `intent_confirmation` (only if topic/audience/objective are empty),
`recipe_confirmation` (all recipes listed; the match is marked recommended),
then `delivery_confirmation` (`approve` or `revise`). Recipes: `consulting`,
`work_report`, `civic`, `art_market`, `editorial`, `history`, plus `open` when
nothing fits. Resume with `{"action": "use"}` for the recommendation, or a
recipe id to override.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick Start

Pass the exact LangChain model already used by the host:

```python
from pathlib import Path

from ppt_expert import AgentConfig, HostRuntime, create_ppt_agent

runtime = HostRuntime(
    model=host_model,
    image_generate=host_image_tool,
)
config = AgentConfig(output_root=Path("outputs"))

async with create_ppt_agent(runtime, config) as agent:
    pending = await agent.start(
        "Create a 12-slide annual business review for the executive team.",
        project_name="annual-business-review",
    )

    # Choose a style. `use` accepts the recommended match; a recipe id overrides.
    pending = await agent.resume(pending["thread_id"], {"action": "use"})
    # Approve delivery after montage + XML audit (`approve` or `revise`).
    result = await agent.resume(pending["thread_id"], {"action": "approve"})
    print(result["artifacts"]["pptx_path"])
```

## Bring Your Own Host Agent

Non-LangChain hosts can expose their existing capabilities as callables. PPT Expert
does not create another model client or read provider API keys.

```python
async def generate_with_host(prompt, schema):
    return await current_host_agent.run(prompt, response_schema=schema)


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
    critique_images=host_vision_tool,  # optional contact-sheet critic
)
```

If the host has no image tool, the workflow creates palette-aware abstract
placeholders and still completes the deck.

## Templates and Visual References

Associate a PowerPoint template, reference images, or both:

```python
pending = await agent.start(
    "Create a product launch presentation.",
    template_path="references/brand-template.pptx",
    reference_images=[
        "references/key-visual.png",
        "references/campaign-poster.jpg",
    ],
)
```

The graph pauses for `recipe_confirmation` with every recipe as an option and
the matcher’s guess marked recommended. A template is applied as the native-edit
branch during `build_pptx`. Reference images do not replace the recipe gate.
Consulting recipes stay vector-first and do not use ImageGen in place of charts.

```python
pending = await agent.resume(pending["thread_id"], {"action": "use"})
result = await agent.resume(pending["thread_id"], {"action": "approve"})
```

When a template is supplied, sample slides are removed while theme, master, and
layout relationships are retained. The output is normalized to a 16:9 canvas.

## Asset Normalization

Image tools are not always honest about file formats. Some write JPEG bytes to a
`.png` path; others silently produce a sibling `.jpg`, `.jpeg`, or `.webp`.

PPT Expert detects the actual format with Pillow, discovers alternate sibling files,
and normalizes every generated asset to a real PNG before composition.

## Command Line

Run the fully offline demo:

```bash
ppt-expert demo --recipe use --delivery approve
```

Run the demo with a template (native-edit branch):

```bash
ppt-expert demo \
  --recipe use \
  --delivery approve \
  --template references/brand-template.pptx \
  --reference-image references/key-visual.png
```

Validate or rebuild an existing project:

```bash
ppt-expert validate outputs/<project-directory>
ppt-expert rebuild outputs/<project-directory>
```

Watch STORY, DESIGN, and asset files; rebuild and validate after every change:

```bash
ppt-expert watch outputs/<project-directory>
```

## Output Contract

```text
outputs/<project-thread>/
├── intent.json
├── foundations.json
├── outline.json
├── style-brief.json
├── tokens.json
├── environment.json
├── guards.json
├── review.json
├── STORY.md
├── DESIGN.md
├── story.json
├── design.json
├── assets/
├── render/                 # montage.png, optional PDF; hi-res pg-*.png removed on cleanup
├── <project>.pptx
├── VALIDATION.md
├── validation.json
└── DELIVERY.md
```

LibreOffice + `pdftoppm` enable a 70dpi montage and 130dpi representative pages.
If they are missing, the run still completes and `environment.json` records
`visual_review: degraded`.

## Host Capability Contract

The text capability must return structured output:

- LangChain models use `with_structured_output(PydanticSchema)`.
- Other hosts return a Pydantic model, dictionary, or JSON string from
  `structured_generate`.

The image capability receives an `ImageRequest` and target path. It may return
bytes, return an existing path, or write directly to the target.

## Quality Gates

```bash
pytest
ruff check .
```

The suite covers recipe matching, token/primitive rendering, short-number
guards, environment degradation, XML package audit, template reuse, checkpointed
`recipe_confirmation` / `delivery_confirmation` interrupts, per-recipe body
layout, and page-level repair.

See [`PPT_AGENT_SPEC.md`](PPT_AGENT_SPEC.md) for recipes, page roles, HITL
payloads, and delivery gates.
