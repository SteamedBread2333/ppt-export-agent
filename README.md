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
- **Human-directed art direction** — pauses for style, typography, and reference
  approval with LangGraph human-in-the-loop interrupts.
- **Template-aware generation** — extracts colors, fonts, masters, and layout
  relationships from an existing `.pptx`.
- **Reference-driven styling** — derives a semantic palette from one or more images.
- **Deterministic rendering** — produces editable PowerPoint files with
  `python-pptx`.
- **Production safeguards** — validates fidelity, assets, fonts, palette usage,
  element bounds, and text-density risk.
- **Durable execution** — resumes interrupted or failed work from SQLite checkpoints.

## Architecture

```text
Brief / Outline / References
              │
              ▼
     Parse · Brief · Evidence
              │
              ▼
   Inspect Template / Images ───────┐
              │                     │
              ▼                     │
      Human Style Approval          │
              │                     │
              ▼                     │
     Typography Approval            │
              │                     │
              ▼                     │
   STORY + DESIGN + Composition     │
              │                     │
              ▼                     │
   Vector-first Visual Plan         │
              │                     │
              ▼                     │
      Host Image Generation         │
              │                     │
              ▼                     │
        PPTX Composition            │
              │                     │
              ▼                     │
 Validate ── Critique ── Repair ◄───┘
              │
              ▼
     Draft Approval + Reports
```

`HostRuntime` is injected through LangGraph's `context_schema`. It is never
serialized into a checkpoint; SQLite stores only portable workflow state.
Optional `critique_images` lets the host visually review the contact sheet.

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

    # Display the style previews, then resume with the chosen direction.
    pending = await agent.resume(pending["thread_id"], "B")
    # Approve a typography specimen. Modern Consulting is the default recommendation.
    result = await agent.resume(
        pending["thread_id"],
        {"action": "use", "profile": "recommended"},
    )
    result = await agent.resume(result["thread_id"], {"action": "approve"})
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

The graph pauses with a `reference_confirmation` interrupt. After `use` or
`adjust`, it still pauses for typography approval. `ignore` returns to the
standard four-style selection. The host can submit one of three decisions:

```python
# Use the extracted direction as-is.
result = await agent.resume(pending["thread_id"], {"action": "use"})

# Refine selected tokens before continuing.
result = await agent.resume(
    pending["thread_id"],
    {
        "action": "adjust",
        "style": {"primary": "#123456", "accent": "#F2A900"},
    },
)

# Ignore references and continue to the standard four-style selection.
next_step = await agent.resume(pending["thread_id"], {"action": "ignore"})
```

When a template is approved, sample slides are removed while theme, master, and
layout relationships are retained. The output is normalized to a 16:9 canvas.

## Asset Normalization

Image tools are not always honest about file formats. Some write JPEG bytes to a
`.png` path; others silently produce a sibling `.jpg`, `.jpeg`, or `.webp`.

PPT Expert detects the actual format with Pillow, discovers alternate sibling files,
and normalizes every generated asset to a real PNG before composition.

## Command Line

Run the fully offline demo:

```bash
ppt-expert demo --style A
```

Run the demo with visual references:

```bash
ppt-expert demo \
  --template references/brand-template.pptx \
  --reference-image references/key-visual.png \
  --reference-action use
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
├── outline.json
├── STORY.md
├── DESIGN.md
├── story.json
├── design.json
├── references.json
├── reference-selection.json
├── style-previews/
├── reference-preview/
├── assets/
├── <project>.pptx
├── VALIDATION.md
└── validation.json
```

LibreOffice enables PDF previews. When `pdftoppm` is also available, the agent emits
one PNG preview per slide. Preview tooling is optional and never blocks PPTX
delivery.

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

The suite covers checkpointed interrupts, reference approval, template reuse,
layout rendering, image fallback and format normalization, validation, and the
repair route.
