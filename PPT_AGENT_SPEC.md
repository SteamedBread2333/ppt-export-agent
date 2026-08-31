# PPT Expert Agent — Production Specification

> Status: implemented six-phase production system
> Engine: Python 3.11+, LangGraph, python-pptx, host-injected `HostRuntime`
> Scope: recipe-led art direction, role-named tokens, narrative page compose,
> zero-render text guards, montage review, XML package audit, and HITL gates
> described below. Human pairwise preference remains an operational evaluation
> outside this package.

---

## 1. Product

PPT Expert is not a text-to-slides utility. It is a host-native presentation
studio: the calling application already owns the model and optional image tools;
this package orchestrates production, rendering, validation, and delivery.

The engine is **Python + python-pptx**. Node / PptxGenJS is not part of the
runtime. The four-layer design system (tokens, primitives, page compose, LIGHT /
DARK masters) is the python-pptx equivalent of that architecture.

### 1.1 Operating priority

```text
factual correctness
→ narrative usefulness
→ visual quality
→ editability
→ token efficiency
→ latency
```

Latency is not the primary target. Token savings must come from structured
state, deterministic tools, and page-level repair — never from skipping
evidence, guards, or package audit.

### 1.2 What this system replaced

The previous v2 main path (four style cards A/B/C/D, typography HITL, and
quality ≥ 90 as the delivery gate) is retired. Quality scoring remains an
auxiliary critic for the strategy benchmark CLI. Delivery is gated by:

1. recipe confirmation before typesetting
2. text guards and volume review
3. XML package audit
4. human `delivery_confirmation`

---

## 2. North Star

The output must be:

- useful in a real meeting
- scannable in a few seconds per slide
- detailed enough for a reader who studies it
- editable in PowerPoint
- faithful to the user's outline and evidence
- visually coherent without looking like a cycling template

### 2.1 Meaning before decoration

```text
decision purpose → claim → evidence → visual encoding → composition → styling
```

Never pick a silhouette or generate an image before knowing what the slide must
prove.

### 2.2 Visual-first means information-first

- time series → line or area chart
- category comparison → column or bar
- composition → allocation strip
- scenarios → scenario matrix
- process → sequence / milestones
- recommendation → decision modules
- atmosphere → photography only when the recipe's image behavior allows it

AI imagery is one primitive, not the default visual system. Consulting /
research recipes are **vector-first**: native charts and tables carry evidence;
ImageGen must not stand in for a chart.

### 2.3 Hierarchy and vertical bands

Four readable layers: **assertion → section label → evidence → footnote**.

Think in bands, not a global grid that forces every page into one silhouette:

```text
context → assertion → rule → evidence → implication → folio
```

On 16:9 widescreen (13.33 × 7.5 in): the title band completes in the upper
10–13%; evidence extends to 88–92%; the folio sits in a locked safety band.
Header rule `y` and footer `y` are tokens, not per-slide guesses.

### 2.4 Density is bandwidth

Density is chosen from audience and occasion (keynote low, operating review
medium, decision memo high). High density means more structured evidence, not
smaller type.

### 2.5 Background is a low-frequency identity layer

A motif must do identity, hierarchy, navigation, or balance. Otherwise delete
it. Dark masters are reserved for cover and close (bookend rhythm).

---

## 3. Style Recipes

Match **one** recipe from the request and intent slots. If nothing fits, use
`open` and record a mixing note. Recipes are prompts, not cages: content and
audience override recipe defaults when they conflict.

| `RecipeId`     | Typical work                         | Visual proposition                          |
|----------------|--------------------------------------|---------------------------------------------|
| `consulting`   | Research, strategy, decision files   | Analytical, compressed, calm                |
| `work_report`  | Status, KPI, operating reviews       | Ordered, restrained, scannable              |
| `civic`        | Community, civic, ceremonial         | Ceremonial, grounded, contemporary          |
| `art_market`   | Posters, campaigns, markets          | Vivid, curated, structured loudness         |
| `editorial`    | Gallery, museum, magazine            | Quiet, cultural, spatial                    |
| `history`      | Teaching, chronology, museums        | Scholarly, narrative, period-aware          |
| `open`         | No canonical match                   | Clear, composed, purpose-built              |

Each recipe encodes: three adjectives, a tension, role-named color tokens,
font roles (`cn` / `num` / `display`), image behavior, a **body layout scheme**,
and a visual proposition used to settle later design conflicts.

| Recipe         | Body layout |
|----------------|-------------|
| `consulting`   | `rules` — type, hairlines, column rules |
| `work_report`  | `stack` — operational bands, not a plus-sign grid |
| `civic`        | `banner` — full-width ceremonial bands |
| `art_market`   | `blocks` — gapped poster fills |
| `editorial`    | `spread` — wide gutter, asymmetric columns |
| `history`      | `spine` — vertical chronology |
| `open`         | `spread` — purpose-built columns |

Five foundations are always in force (see `FOUNDATIONS` in
`ppt_expert.recipes`):

1. Visual proposition first.
2. Hierarchy before decoration.
3. Density is bandwidth, not smaller type.
4. Think in vertical bands.
5. Background is identity or it is deleted.

---

## 4. Six-Phase Production Graph

```text
parse_intent
      │
      ├─ slots incomplete → intent_confirmation → match_recipe
      └─ slots complete   → match_recipe
                                │
                          confirm_recipe  (HITL: all recipes; match is recommended)
                                │
                          survey_env
                                │
                          plan_narrative
                                │
                          build_pptx
                                │
                          guard_text
                                ├─ warnings → repair_guards → build_pptx
                                └─ clean    → render_overview
                                                    │
                                              inspect_reps
                                                    ├─ blocking page issues → repair_pages → build_pptx
                                                    └─ ok → xml_audit
                                                                  ├─ invalid → repair_pages → build_pptx
                                                                  └─ ok → confirm_delivery
                                                                                ├─ revise → repair_pages → build_pptx
                                                                                └─ approve → cleanup → END
```

Implemented nodes live in `ppt_expert.graph.build_graph`.

### Phase 1 — Intent and recipe

1. `parse_intent` fills `IntentSlots` and `OutlinePlan` in **one** structured
   host call, then writes `intent.json`, `outline.json`, and `foundations.json`.
2. `confirm_intent` interrupts only when topic, audience, or objective is empty.
3. `match_recipe` selects the closest `RecipeId` and writes `StyleBrief` plus
   `tokens.json` / `style-brief.json`. The match is a **recommendation**, not a
   silent commit.
4. `confirm_recipe` **always** interrupts. The payload lists every recipe;
   `recommended` / `reason` mark the match; `options[0]` is that recommendation.
   Actions: a recipe id, or `use` to accept the recommendation.

This is the last preparation before typesetting.

### Phase 2 — Environment

`survey_environment` requires `soffice` / `libreoffice`, `pdftoppm` (poppler),
and PIL. Missing tools abort the run. There is no degraded visual path.

Results go to `environment.json` with `visual_review: full`.

Project directory (physical form):

```text
<project>/
  tokens.json
  primitives and slides provided by code
  render/          # PDF, montage; intermediate pg-*.png removed on cleanup
  <name>.pptx
```

### Phase 3 — Design system encoding

Renderer split (`ppt_expert.pptx`):

1. **Tokens** — `C` roles (`bg`, `surface`, `ink`, `ink2`, `muted`, `accent`,
   `positive`, `caution`, `risk`, `hairline`, plus the dark set), `F` (`cn`,
   `num`, `display`), `PAGE` (`w=13.33`, `h=7.5`, `mx`, locked header/footer
   y). Palette literals live in recipes; compose code must not scatter hex.
2. **Primitives** — `header` (nav + assertion + locked hairline), `footer`,
   `panel`, `mini_label`, `implication`, `stat_card`, `progress`, `hairline` /
   `vline`, `token()` (short-number wrap protection), `chart_base`, cover/close
   motif.
3. **Compose** — named by narrative role, not a six-`LayoutType` loop (see
   Section 6). Coordinates stay local to the page function.
4. **Entry** — LIGHT master for body pages; DARK for cover and close. Core
   properties: title, subject, author.

The host model plans **task and evidence per page**. It does not invent slide
coordinates.

### Phase 4 — Build and zero-render guards

`guard_text` inspects the pptx **without** a bitmap render. It flags short
tokens (percentages, amounts, quarters, weeks, dates, page-like numerals) that
would wrap vertically in a narrow box.

`token()` sets `wrap=False` and widens within the canvas. `repair_guards`
rebuilds until clean or `max_repair_attempts`. Shrinking type is a last resort.

When `template_path` is set, wrap-width rebuild is skipped so in-place template
edits are not destroyed.

Writes `guards.json`.

### Phase 5 — Visual review

Every run renders the contact sheet. Missing LibreOffice or pdftoppm is a
hard error.

1. `soffice` → PDF → `pdftoppm -r 70` → PIL montage `render/montage.png`
2. Four representative pages (cover, densest, special-element, close) are
   inspected in the pptx package — assertion title, overflow, columns,
   implication — without a second hi-res raster. Vision reviews the montage.

`HostRuntime.critique_images` (or a vision-capable `host.model`) **must**
review that montage. Findings keep the critic's severity. Errors route to
`repair_pages`, then rebuild (compose, or native-edit into template boxes).

Deterministic volume checks (geometry / roles), then four questions on
representatives:

1. Is the title an assertion or a topic? (`topic_title` is an error: rewrite
   copy, then rebuild. On a template, native-edit writes the new title into the
   existing box.)
2. Overflow / overlap?
3. Column alignment?
4. Does the implication bar hug the folio safety band?

Also: dark bookends, adjacent silhouette repeat, empty lower third, footer
lock, conflicting KPI labels.

Native-edit skips recipe-token geometry (`card_soup`, cramped header, empty
bottom, footer lock) so brand art is not punished. Montage render and vision
critique still run on template decks.

Repair **only affected pages** (`merge_repaired_pages`), then rebuild. The
repair host call receives failing pages in full and compact locked-page
context; it does not regenerate the design spec (tokens already won).

### Phase 6 — XML audit, delivery, cleanup

Unzip-level checks:

- slide XML count equals the outline
- each slide has a `notesSlide` (speaker intent)
- native chart parts ≥ narrative requirement (skipped for native-edit templates)
- no `undefined` / `NaN` / `[object`
- package size sane (no duplicated bitmaps)

HITL `delivery_confirmation` shows validation + review + montage path.
Actions: `approve` | `revise`.

`cleanup` deletes `render/pg-*.png` and `hi-pg*.png`, **keeps** montage, PDF,
and pptx, and writes `DELIVERY.md` (visual notes, editability / design system,
data provenance).

---

## 5. Human-in-the-Loop Gates

All gates use LangGraph `interrupt()` and resume on the same `thread_id`.

| Type                     | When                         | Actions                         |
|--------------------------|------------------------------|---------------------------------|
| `intent_confirmation`    | Topic / audience / objective empty | `continue`, `edit`        |
| `recipe_confirmation`    | After match, before compose  | recipe id, or `use` for the recommendation |
| `delivery_confirmation`  | After XML audit              | `approve`, `revise`             |

There is no style-card gate, no typography-specimen gate, and no
`draft_confirmation` quality-score gate.

Template / reference images are an optional **native-edit** branch at
`build_pptx` (Section 10). They do not replace recipe confirmation.

---

## 6. Narrative Page Roles

`StoryPage.role` is the compose router. `LayoutType` remains on the model for
compatibility; it must not drive geometry.

| Role        | Job                                              |
|-------------|--------------------------------------------------|
| `cover`     | Dark motif, assertion, KPI anchors               |
| `overview`  | Judgment panels + optional numeric strip         |
| `context`   | Trend chart + observation rail                   |
| `evidence`  | Table / chart / waterfall / heatmap + implication |
| `structure` | Dual panels or allocation strip                  |
| `expansion` | Multi-column logic / metric / risk (not empty pillars) |
| `scenario`  | Scenario columns; featured base case highlighted |
| `close`     | Dark bookend, next steps, optional milestones    |

Adjacent pages must not share a silhouette (evidence repeats are allowed).
Cover and close use the dark master.

---

## 7. Data Contracts

Canonical Pydantic models live in `ppt_expert.models`.

### 7.1 `IntentSlots`

```yaml
topic: string
audience: string
objective: string
slide_count: 1..40
editable: bool
delivery_format: string   # typically pptx
density: low | medium | high
```

### 7.2 `StyleBrief`

```yaml
adjectives: [string, string, string]
tension: string
density: low | medium | high
color_logic: string
type_logic: string
image_behavior: string
spatial_rhythm: string
recipe_id: RecipeId
visual_proposition: string
mixing_note: string
```

### 7.3 `DesignTokens`

Role-named `ColorRoles`, `FontRoles`, `PageMetrics`, plus proposition, tension,
and image behavior. `to_design_spec()` projects into the existing `DesignSpec`
used by validation and documents.

### 7.4 `StoryPage` (narrative fields)

Keep outline fidelity: number, title, core content. Production fields:

```yaml
role: cover | overview | context | evidence | structure | expansion | scenario | close
eyebrow: string
subtitle: string
takeaway: string          # implication bar
source_note: string
speaker_notes: string     # required in the package
kpis, chart, chart_secondary, table, allocation, scenarios
waterfall, heatmap, milestones
image_id: string | null   # only when recipe image_behavior allows
```

### 7.5 Reports

- `EnvironmentReport` — tool flags + `visual_review`
- `GuardReport` — short-token warnings
- `VolumeReview` — rhythm, adjacent silhouette, empty bottom, chrome lock,
  representative pages, montage/pdf paths
- `ValidationReport` — structural + package audit
- `ArtifactBundle` — pptx, STORY, DESIGN, VALIDATION, montage, `DELIVERY.md`

`HostRuntime` is **not** checkpointed. SQLite stores only portable JSON state.

---

## 8. Native Visualization

Analytical pages use python-pptx native objects:

- line / column / bar / area charts (`chart_base`)
- comparison tables
- waterfall bars
- heatmaps as native tables
- allocation strips
- scenario columns
- KPI `stat_card`s

Charts are themed from tokens (accent, positive, caution, ink2). Consulting
fixtures must not set `image_id` on evidence pages.

---

## 9. Images and Normalization

Images generate only when a page has `image_id` and the recipe allows it.

The asset layer:

- detects actual format from bytes
- discovers `.jpg` / `.jpeg` / `.webp` siblings
- normalizes to PNG before composition
- falls back to a palette placeholder if the host has no image tool

---

## 10. Templates and References

Optional `template_path` and `reference_images` on `start()`:

- template: take pages from the deck, clone if the outline is longer, edit
  titles / body / charts / tables in place; keep slide size, theme, master, and
  decorative shapes. Do not extract the template as a style source and do not
  compose recipe pages onto a blank 16:9 canvas.
- XML audit skips recipe palette / font / chart-count checks for this branch;
  volume review skips token geometry (`card_soup`, cramped header, empty bottom,
  footer lock). Overflow and `topic_title` still apply; repaired copy is written
  into the existing template boxes.
- references: do not skip recipe confirmation; consulting stays vector-first

This is the “native-edit an existing deck” branch, not a fourth HITL style
audition.

---

## 11. Host Runtime

```python
HostRuntime(
    model=...,                      # LangChain, with_structured_output
    structured_generate=...,        # or a callable (prompt, schema) -> model
    image_generate=...,             # optional
    critique_images=...,            # required contact-sheet critic (or vision model)
)
```

No provider clients and no API keys in this package.

---

## 12. Public SDK

```python
from ppt_expert import AgentConfig, HostRuntime, create_ppt_agent

async with create_ppt_agent(runtime, config) as agent:
    pending = await agent.start(request, project_name=..., template_path=..., reference_images=...)
    pending = await agent.resume(pending["thread_id"], {"action": "use"})
    result = await agent.resume(pending["thread_id"], {"action": "approve"})
```

CLI:

```bash
./scripts/bootstrap.sh
ppt-expert doctor
ppt-expert setup
ppt-expert demo --recipe use --delivery approve
ppt-expert benchmark
ppt-expert validate <project>
ppt-expert rebuild <project>
ppt-expert watch <project>
```

---

## 13. Output Contract

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
├── STORY.md / story.json
├── DESIGN.md / design.json
├── assets/
├── render/                 # montage.png, optional PDF
├── <project>.pptx
├── VALIDATION.md / validation.json
├── DELIVERY.md
└── metrics.jsonl
```

---

## 14. Validation and Acceptance

### 14.1 Delivery gates (blocking)

- outline fidelity (count, titles, core facts)
- missing required native charts
- out-of-bounds shapes
- palette / font contract
- package: slide XML count, notes parts, unresolved placeholders
- text overflow risk (body copy budget)

### 14.2 Auxiliary quality score

`score_deck` still scores narrative, evidence, hierarchy, composition,
typography, data visualization, consistency, editability, and accessibility.
The strategy benchmark CLI may require score ≥ 90. **The graph does not block
delivery on that score.**

### 14.3 Consulting strategy fixture

A nine-slide consulting deck must include:

- cover with assertion + KPI anchors
- at least three native charts
- at least one native table
- a scenario matrix with a featured base case
- an allocation structure
- source notes on analytical pages
- no ImageGen as primary evidence
- varied families / roles; cover and close as bookends

### 14.4 Automated suite (CI)

- recipe keywords: 研报 → `consulting`, 党建 → `civic`, 历史 → `history`
- compose modules contain no recipe hex besides `#FFFFFF` / `#000000`
- header title `y` and footer `y` lock across a volume
- four-theme expansion is hierarchical, not tall empty pillars
- `36.8%` is single-line (`wrap=False`)
- missing soffice or pdftoppm: the graph fails; montage review is mandatory
- XML notes present, no `NaN` / `undefined` / `[object`
- demo e2e interrupts are `recipe_confirmation` (options + recommended) then
  `delivery_confirmation` (`intent_confirmation` only when slots are empty)

Human blind preference is **not** a unit test.

---

## 15. LangGraph State

Checkpointed keys include: request, project paths, intent, recipe, style brief,
tokens, environment, outline, evidence, story, design, image paths, pptx path,
guards, review, validation, montage, delivery decision, repair attempts,
artifacts.

Conditional routes:

```text
incomplete slots → intent_confirmation
recipe unconfirmed → recipe_confirmation (choose among all recipes; match is recommended)
guard warnings → rebuild
review / XML errors → page-level repair (max attempts)
delivery revise → page-level repair
approve → cleanup
```

---

## 16. Definition of Done

The production system is complete when:

- the main graph is the six-phase path above, not one-shot STORY → render
- a recipe (or open brief) is confirmed before typesetting
- compose is role-named and token-driven
- short numeric tokens cannot stack vertically in narrow boxes
- LibreOffice and pdftoppm are required; montage review is mandatory
- XML audit and speaker notes are delivery gates
- repair changes only failing pages
- consulting evidence is native and editable
- the automated suite in Section 14.4 passes
