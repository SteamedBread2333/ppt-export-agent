# PPT Expert Agent — Production Specification v2

> Status: implemented v2 production system
> Scope: LangGraph agent, native analytical rendering, HITL design gates, and
> quality gates described below. Human pairwise preference (Section 21) remains
> an operational evaluation outside this package.
> Objective: produce presentations that equal or exceed expert-built consulting,
> research, strategy, product, and narrative decks while remaining editable,
> traceable, and reproducible.

---

## 1. Why v2 Is Necessary

Using the same language model does not produce the same presentation quality. The
decisive factor is the production system around the model: how it structures
evidence, chooses a visual grammar, composes each slide, renders data, and evaluates
the result.

### 1.1 Benchmark evidence

Two nine-slide A-share strategy decks were inspected:

- **Benchmark deck**: third-party agent output
- **Current deck**: PPT Expert Agent output

The benchmark contained:

- 556 editable shapes, averaging 61.8 per slide
- 242 text-bearing shapes
- 3 native charts and 1 native table
- 22 distinct font sizes from 7.5pt to 40pt
- 8 distinct slide-position signatures across 9 slides
- 3,154 explicit text characters
- no raster pictures; the visual system was predominantly native vector content

The current output contained:

- 65 shapes, averaging 7.2 per slide
- 37 text-bearing shapes
- no native charts and no tables
- only 8 distinct font sizes
- 6 slide-position signatures across 9 slides
- approximately 1,458 content characters
- 80 numeric tokens that were rendered without a single native chart or table
- 4 large raster images occupying approximately 310% of aggregate slide area
- raster media accounting for approximately 98.6% of the package size
- three uses of the same four-card geometry and two dense monolithic text slides

Shape count is not itself a quality target. It reveals a deeper difference:
the benchmark converted information into editable visual components, while the
current agent compressed information into generic text blocks and decorative
images.

The benchmark is not structurally ideal and should not be copied blindly. Its master
and four layouts are empty, most styling is applied directly, and all 556 objects are
slide-local. The cover alone uses 205 line segments. More than 70% of its text is
10.5pt or smaller. V2 must preserve its information-design quality while improving
maintainability, semantic structure, and presentation-distance readability.

### 1.2 Visible failure on the cover

The benchmark cover separates:

- research category and context
- time horizon
- decisive headline
- supporting thesis
- three KPI anchors
- an editable market trajectory
- disclaimer and authorship metadata

The current cover combines most of this into a centered paragraph over a large
image. It has weaker hierarchy, lower scanability, less usable whitespace, and no
analytical information design.

### 1.3 Typography finding

Both reviewed decks use PingFang SC extensively, so the quality gap does not come
from the family name alone. The benchmark pairs PingFang SC with Arial for numeric
content and uses a much richer hierarchy from 7.5pt to 40pt. The current deck uses
fewer levels and places long centered copy in shallow text boxes.

V2 must improve both:

- **font selection** — let the user approve a typography profile and choose a more
  distinctive default stack
- **typographic composition** — control script-specific fonts, numeric styling,
  line length, weight, leading, alignment, and hierarchy

### 1.4 Root causes

1. **The old rule “visuals before text” was interpreted as “generate images.”**
   Analytical decks need charts, diagrams, matrices, and KPI modules before they
   need illustrations.
2. **Six fixed layouts are too coarse.** They force unrelated content into the same
   geometry.
3. **STORY lacks evidence semantics.** It stores prose but not claims, metrics,
   comparisons, sources, or the intended visual encoding.
4. **DESIGN is a palette sheet, not a design system.** It lacks grid, component,
   hierarchy, chart, table, and spacing rules.
5. **Rendering is one-pass.** There is no rendered-slide critic that compares the
   result against the design intent.
6. **Validation checks correctness, not excellence.** A deck can pass while still
   looking generic.

---

## 2. Product North Star

PPT Expert is not a “text-to-slides” utility. It is a presentation production
system with five responsibilities:

1. **Editorial strategy** — determine the argument, sequence, and decision value.
2. **Information design** — map claims and evidence to the right visual form.
3. **Art direction** — create a coherent visual language and brand expression.
4. **Composition** — build editable, slide-specific layouts with strong hierarchy.
5. **Quality assurance** — render, inspect, score, repair, and deliver.

The output must be:

- useful in a real meeting
- understandable in five seconds per slide
- detailed enough for a reader who studies it
- editable in PowerPoint
- faithful to the user's evidence and outline
- visually coherent without appearing template-generated

### 2.1 Operating priority

The production priority is:

```text
factual correctness
→ narrative usefulness
→ visual quality
→ editability
→ token efficiency
→ latency
```

Latency is not a primary optimization target. The agent may spend additional time on
planning, candidate generation, rendering, comparison, and repair when those steps
materially improve quality.

Token efficiency must never be achieved by skipping evidence analysis, design
auditions, rendered review, or blocking validation. Savings must come from removing
duplicate context and moving deterministic work out of the model.

### 2.2 Deliberate quality mode

The default production profile is `deliberate`:

- plan globally before composing locally
- generate competing directions for high-impact decisions
- render before judging
- use independent editorial and visual review passes
- repair only the responsible layer
- stop when measured quality converges, not after a fixed single pass

The graph may use more wall-clock time, but every additional model call must have a
distinct role, new evidence, or a measurable evaluation purpose.

---

## 3. Core Production Principles

### 3.1 Meaning before decoration

For every slide:

```text
decision purpose → claim → evidence → visual encoding → composition → styling
```

Never select a layout or generate an image before understanding what the slide must
prove.

### 3.2 Visual-first means information-first

Use the visual form that best carries meaning:

- time series → line or area chart
- category comparison → bar or dot plot
- composition → stacked bar, treemap, or allocation strip
- scenarios → scenario matrix
- process → flow or sequence diagram
- hierarchy → tree or layered architecture
- recommendation → decision cards or priority matrix
- narrative/emotional moment → photography or illustration

AI imagery is one visual primitive, not the default visual system.

### 3.3 Vector-first, raster when justified

Prefer native PowerPoint shapes, text, tables, and charts because they are:

- editable
- crisp at any resolution
- brandable
- accessible to downstream users
- easier to validate

Use raster imagery for covers, atmosphere, people, products, locations, or artwork
that cannot be represented meaningfully as data or diagrams.

### 3.4 One slide, one governing message

Every slide must have one assertion-style headline. Supporting components may add
depth, but they must reinforce the headline rather than introduce a second story.

### 3.5 Consistency without repetition

Reuse tokens and components, not complete page geometry. A high-quality deck should
feel like one system with slide-specific compositions.

### 3.6 Rendered output is the truth

The `.pptx` object model is not sufficient evidence of quality. Every slide must be
rendered to an image and visually inspected before delivery.

### 3.7 Search before commitment

Important design decisions should not depend on the model's first answer.

Use bounded best-of-N search for:

- narrative spine
- cover concept
- executive-summary architecture
- the densest analytical slide
- scenario or recommendation structure
- closing synthesis

Generate structurally different candidates, reject invalid options with deterministic
rules, render the strongest finalists, and select by pairwise visual comparison.

### 3.8 Spend computation where quality is uncertain

Do not apply the same model budget to every slide. Allocate additional reasoning and
critique to slides with:

- high decision importance
- dense or conflicting evidence
- novel composition
- complex charts or tables
- weak critic confidence
- repeated repair failures

Stable footers, file conversion, geometry checks, color math, and format
normalization require no language-model call.

### 3.9 Preserve independent judgment

The generator must not be the sole judge of its own work. Editorial review, visual
review, data review, and final selection use separate prompts and isolated evidence
views, even when the host provides only one underlying model.

---

## 4. Deck-Type Router

The graph must classify the deck before planning visuals.

### 4.1 Supported archetypes

#### Strategy / research / consulting

Default grammar:

- assertion headlines
- KPI strips
- native charts
- comparison tables
- scenario matrices
- allocation diagrams
- source notes
- restrained imagery

#### Executive update / business review

Default grammar:

- scorecards
- variance bridges
- trends
- operating drivers
- risks and actions
- owner and timing metadata

#### Product / sales

Default grammar:

- customer problem
- product proof
- workflow diagrams
- screenshots or product imagery
- competitive differentiation
- case-study metrics

#### Training / education

Default grammar:

- concept framing
- progressive disclosure
- worked examples
- diagrams
- exercises and recap

#### Brand / keynote / narrative

Default grammar:

- large-scale imagery
- short copy
- pacing and emotional contrast
- cinematic hero moments
- minimal analytical density

### 4.2 Routing rule

The archetype controls:

- recommended slide families
- information density
- image-to-vector ratio
- typography scale
- chart frequency
- annotation depth
- expected source treatment

The previous universal 55–60% image rule is removed.

---

## 5. LangGraph Production Workflow

```text
intake
  → classify_deck
  → parse_evidence
  → build_narrative
  → inspect_references
  → propose_design_directions
  → render_design_audition
  → human_approve_direction
  → plan_slides
  → plan_visual_assets
  → generate_assets
  → compose_draft
  → render_preview
  → visual_critic
  → repair
  → validate
  → human_accept_deck
  → deliver
```

### 5.1 Intake

Collect:

- topic and objective
- audience and decision context
- presentation duration
- outline or source material
- required slide count
- brand/template files
- reference images or decks
- output language
- typography preference or approved corporate fonts
- data sensitivity
- delivery constraints

If audience, objective, or decision context is missing, pause with a focused
human-in-the-loop question.

### 5.2 Classify the deck

Produce:

- primary archetype
- optional secondary archetype
- information-density target
- expected visual forms
- tone and risk level

### 5.3 Parse evidence

Extract and normalize:

- claims
- facts
- metrics and units
- time periods
- comparisons
- scenarios
- recommendations
- risks
- sources
- confidence or uncertainty

Never invent a chart from prose unless the underlying values are explicit. If data
is unavailable, use a qualitative diagram and label it accordingly.

### 5.4 Build the narrative

Create a narrative spine:

```text
context → tension → evidence → interpretation → choice → action → risk
```

Each slide must define:

- role in the argument
- governing message
- required evidence
- transition from the previous slide
- intended audience takeaway

### 5.5 Inspect references

For templates:

- extract slide size, theme, masters, layouts, fonts, colors, and components
- identify reusable layout families
- distinguish brand rules from sample-slide content
- generate a contact sheet of representative slides

For images:

- extract palette, contrast, texture, geometry, visual weight, and mood
- detect whether the reference is suitable for a full deck or only a cover
- never reduce image analysis to dominant colors alone

### 5.6 Design audition

Do not ask the user to approve abstract palette cards only.

Render three representative slides for each candidate direction:

1. cover
2. analytical or content-dense slide
3. conclusion or recommendation slide

Each direction also includes a typography specimen rendered with real deck content:

- display headline
- assertion headline
- body paragraph
- labels and footnotes
- KPI numerals, percentages, and ranges
- mixed Chinese/Latin text when applicable

The user approves both the visual direction and typography profile after seeing them
applied to real content. The user may select a recommended profile, inherit the
linked template, or provide a custom installed font.

### 5.7 Plan slides

Generate a structured `SlideSpec` for every slide before rendering.

### 5.8 Compose the draft

Use a two-pass renderer:

1. **Structure pass** — grid, zones, components, charts, tables, and hierarchy
2. **Polish pass** — alignment, spacing, annotations, emphasis, and decorative detail

### 5.9 Render and critique

Render every slide to PNG, build a contact sheet, and evaluate both individual
slides and the entire deck.

### 5.10 Repair loop

Repair at the smallest responsible level:

- token issue → adjust design token
- component issue → adjust component
- slide issue → recompose one slide
- rhythm issue → reorder or vary a slide family
- narrative issue → return to narrative planning

Maximum automatic repair passes: three. Escalate unresolved trade-offs to the user.

### 5.11 Final human acceptance

Before delivery, show:

- contact sheet
- validation summary
- remaining warnings
- final file paths

Allow the user to approve, request targeted changes, or select slides for revision.

### 5.12 Candidate-search policy

Use three search depths:

#### Global decisions

Generate three to five candidates for narrative architecture and design direction.
Select through rubric scoring plus pairwise comparison.

#### Key slides

Generate two to four compositions for the cover, executive summary, densest
analytical slide, recommendation, and conclusion. Render finalists before selection.

#### Routine slides

Generate one semantic plan and one fallback family. Expand search only when
deterministic checks or the critic report low confidence.

Candidate diversity must be structural. Color-only or wording-only variations do
not count as independent candidates.

### 5.13 Token-efficient orchestration

Quality-preserving token controls:

1. **Canonical state** — store structured facts once and reference stable IDs instead
   of repeating source documents in every prompt.
2. **Hierarchical context** — retain a deck summary, section summaries, and
   slide-local evidence packets. Give each node only the smallest lossless packet it
   needs.
3. **Content-addressed cache** — cache model results by prompt version, schema,
   evidence IDs, design-system hash, and model identity.
4. **Delta repair** — send the current slide specification, rendered crop, and issue
   list; never resend the entire deck for a local defect.
5. **Batch compatible work** — plan similar routine slides together, while keeping
   high-risk slides independent.
6. **Deterministic preflight** — use code for statistics, chart suitability,
   geometry, contrast, font checks, image normalization, and file validation.
7. **Progressive visual review** — review a contact sheet first; send full-resolution
   slide images only for flagged or high-impact slides.
8. **Stable prompt prefixes** — keep system and rubric prefixes identical so host
   providers can reuse prompt caches.
9. **No transcript replay** — persist approved structured artifacts and concise
   decision rationales instead of complete reasoning histories.
10. **Budget telemetry** — record input tokens, output tokens, cache hits, retries,
    quality gain, and elapsed time for every model call.

Token budgets are soft ceilings. A node may exceed its budget when a blocking
quality issue remains, but it must record the reason and expected quality gain.

### 5.14 Convergence and stopping

Continue repair only when the expected quality gain justifies another pass.

Stop when all conditions hold:

- no blocking issue remains
- quality threshold is met
- two consecutive passes improve the overall score by less than two points
- the latest pass introduces no regression
- human approval has been obtained

Escalate instead of looping when two repairs fail for the same root cause.

---

## 6. Human-in-the-Loop Gates

### Gate A: brief confirmation

Trigger when objective, audience, or scope is materially ambiguous.

### Gate B: reference interpretation

Show extracted template and image characteristics. Actions:

- use
- adjust
- ignore

### Gate C: design audition

Show real-content sample slides rather than palette-only cards. Actions:

- approve direction
- choose or change typography profile
- inherit typography from the linked template
- provide a custom font
- merge selected traits
- request another direction

### Gate D: draft review

Show a full-deck contact sheet and quality score. Actions:

- approve
- revise selected slides
- revise global system

### Gate E: final acceptance

Confirm delivery after all blocking checks pass.

All gates use LangGraph `interrupt()` and resume with the same `thread_id`.

---

## 7. Data Contracts

### 7.1 `DeckBrief`

```yaml
objective: string
audience: string
decision_context: string
duration_minutes: integer
language: string
slide_count: integer
primary_archetype: enum
secondary_archetype: enum | null
density: low | medium | high
brand_constraints: object
reference_files: list[path]
```

### 7.2 `EvidenceItem`

```yaml
id: string
kind: claim | metric | quote | event | recommendation | risk
statement: string
value: number | null
unit: string | null
period: string | null
comparison: object | null
source: string | null
confidence: confirmed | estimated | illustrative
```

### 7.3 `SlideSpec`

```yaml
number: integer
section: string
purpose: string
headline: string
takeaway: string
evidence_ids: list[string]
slide_family: enum
visual_form: enum
composition: object
components: list[ComponentSpec]
chart: ChartSpec | null
table: TableSpec | null
artwork: ArtworkSpec | null
annotations: list[string]
source_note: string | null
density_budget: object
transition: string
```

### 7.4 `DesignSystem`

```yaml
canvas:
  ratio: 16:9
  safe_margin: number
grid:
  columns: 12
  gutter: number
  baseline: number
typography:
  display: FontToken
  headline: FontToken
  subhead: FontToken
  body: FontToken
  label: FontToken
  footnote: FontToken
palette:
  canvas: color
  surface: color
  primary_text: color
  secondary_text: color
  accent: color
  positive: color
  negative: color
  warning: color
chart_theme: object
table_theme: object
components: object
image_treatment: object
```

### 7.5 `TypographyProfile`

```yaml
id: string
name: string
source: recommended | template | custom
language: string
display:
  latin_family: string
  east_asian_family: string
  fallbacks: list[string]
headline:
  latin_family: string
  east_asian_family: string
  fallbacks: list[string]
body:
  latin_family: string
  east_asian_family: string
  fallbacks: list[string]
numeric:
  family: string
  tabular_figures: boolean
scale:
  display: number
  headline: number
  component_title: number
  body: number
  label: number
  footnote: number
weights: object
line_heights: object
installed: boolean
glyph_coverage_valid: boolean
user_approved: boolean
```

### 7.6 `QualityReport`

```yaml
score: 0..100
blocking_issues: list[Issue]
warnings: list[Issue]
slide_scores: list[SlideQuality]
dimensions:
  narrative: 0..100
  evidence: 0..100
  hierarchy: 0..100
  composition: 0..100
  typography: 0..100
  data_visualization: 0..100
  consistency: 0..100
  editability: 0..100
  accessibility: 0..100
```

### 7.7 `ExecutionMetrics`

```yaml
run_id: string
node: string
purpose: string
model_identity: string
prompt_version: string
input_tokens: integer
output_tokens: integer
cached_tokens: integer
cache_hit: boolean
latency_ms: integer
retry_count: integer
quality_before: number | null
quality_after: number | null
artifact_hashes: list[string]
```

Use these metrics to optimize duplicate work and context size. Never rank a cheaper
run above a higher-quality run solely because it used fewer tokens.

---

## 8. Slide-Family System

Replace six rigid layouts with composable slide families.

### 8.1 Foundation families

- title / cover
- section divider
- executive summary
- assertion + evidence
- conclusion / call to action
- appendix

### 8.2 Analytical families

- KPI strip + trend
- chart + interpretation rail
- dual-chart comparison
- chart + driver cards
- valuation or benchmark table
- scenario matrix
- allocation bar or portfolio map
- risk heatmap
- waterfall / bridge
- timeline with milestones

### 8.3 Strategic families

- strategic pillars
- option comparison
- priority matrix
- recommendation stack
- operating model
- capability architecture
- roadmap

### 8.4 Narrative families

- full-bleed hero
- image + assertion
- quote or testimony
- before / after
- visual sequence

### 8.5 Composition rules

- use a 12-column grid
- align all major edges to grid lines
- define safe zones and minimum gutters
- cap the number of focal regions
- reserve whitespace intentionally
- vary composition across adjacent slides
- keep recurring navigation and footer elements stable

The renderer chooses and parameterizes a family from slide semantics. It does not
select layouts by cycling through a fixed list.

---

## 9. Native Data-Visualization Engine

Analytical decks require a first-class chart and table system.

### 9.1 Required chart forms

- line and area
- grouped and stacked bar
- dot plot
- waterfall
- allocation strip
- slope chart
- range plot
- scatter and quadrant
- heatmap
- small multiples

### 9.2 Chart design rules

- lead with the insight, not the chart type
- label decisive values directly
- remove unnecessary borders, legends, and gridlines
- use accent color only for the series that proves the headline
- annotate inflection points and thresholds
- preserve units and periods
- include source and confidence status
- avoid 3D charts
- avoid pie charts when comparison precision matters

### 9.3 Table design rules

- use tables for lookup and precise comparison, not decoration
- align numbers by decimal position where practical
- apply semantic color sparingly
- highlight one governing row or column
- separate labels, values, deltas, and notes
- keep the table editable

### 9.4 Diagram rules

Build diagrams from semantic nodes and edges. Use:

- consistent node roles
- directional flow
- meaningful grouping
- no crossing connectors when a reroute is possible
- a limited hierarchy depth

---

## 10. Component Library

Create reusable native PowerPoint components:

- eyebrow / section label
- assertion headline
- subtitle
- KPI tile
- metric delta
- insight callout
- interpretation rail
- source note
- page index
- legend
- recommendation card
- risk badge
- scenario card
- allocation segment
- chart annotation

Each component defines:

- semantic role
- minimum and maximum dimensions
- padding
- typography token
- allowed color roles
- overflow behavior
- alignment anchors

Components must remain editable and must not be flattened into images.

---

## 11. Typography and Information Hierarchy

### 11.1 Required hierarchy

Use at least five functional levels where the deck requires them:

1. display
2. assertion headline
3. component title
4. body or value
5. label / source / footnote

### 11.2 Rules

- use assertion headlines for analytical slides
- limit line length and avoid centered paragraphs
- never use shrink-to-fit as the primary layout strategy
- recompute composition before reducing body type
- preserve a minimum readable body size
- use tabular numerals for KPI-heavy decks when available
- use font weight and spacing before introducing additional colors

### 11.3 Language-aware typography

Select font families and line-height rules based on output language. Validate the
actual fonts on the target system and define explicit fallbacks.

### 11.4 Human typography selection

Typography is a human-in-the-loop decision, not a hidden configuration default.

Before full production, render three typography specimens with the user's actual
headline, body copy, metrics, percentages, and mixed-language content. Offer:

1. **Modern Consulting** — neutral, precise, high-density, strong numerals
2. **Editorial Authority** — serif-led headlines with restrained sans-serif body
3. **Executive Technology** — geometric display type with a highly legible body
4. **Template / Brand** — typography inherited from the approved source
5. **Custom** — an installed family or user-supplied font package

The chosen profile is persisted in `DesignSystem` and requires explicit approval.

### 11.5 Recommended default stacks

The default is selected dynamically from fonts that are actually available. The
preferred high-quality multilingual stack is:

```text
Latin display and numerals:
Inter → Aptos Display → Avenir Next → Arial

Chinese display and headlines:
Source Han Sans SC → Noto Sans CJK SC → HarmonyOS Sans SC
→ MiSans → PingFang SC → Microsoft YaHei

Chinese body:
Source Han Sans SC → Noto Sans CJK SC → PingFang SC
→ Microsoft YaHei → SimHei

Editorial Chinese headlines:
Source Han Serif SC → Noto Serif CJK SC → Songti SC → SimSun
```

`Modern Consulting` is the default recommendation when Inter plus Source Han Sans
SC or Noto Sans CJK SC are installed. Otherwise:

- macOS defaults to Avenir Next for Latin/numerals and PingFang SC for Chinese
- Windows defaults to Aptos/Aptos Display for Latin/numerals and Microsoft YaHei
  for Chinese
- Linux defaults to Inter and Noto Sans CJK SC

Do not claim a font is active merely because it appears in the fallback chain.

### 11.6 Script-specific font application

PowerPoint text runs must set script-specific typefaces:

- `a:latin` for Latin characters
- `a:ea` for East Asian characters
- `a:cs` for complex scripts where required

Use a dedicated numeric family only when its glyph metrics and license are valid.
Apply tabular figures to KPI tiles, tables, and axes when available.

### 11.7 Font validation and packaging

Before rendering:

- scan installed font files and PostScript names
- validate glyph coverage for every character used in the deck
- validate required weights, not only the family name
- verify that numeric and Chinese baselines align
- reject synthetic bold or italic
- compare line wrapping in the final rendering environment

Never silently substitute a missing font. Pause for user approval when the chosen
profile is unavailable.

Open-licensed fonts may be offered as an optional project font pack, but the agent
must record license metadata and must not redistribute restricted corporate or
system fonts.

### 11.8 Typographic composition

Font family selection cannot compensate for weak composition:

- use mixed alignment intentionally; reserve centered text for short ceremonial copy
- keep analytical headlines left-aligned by default
- use display faces sparingly
- separate headline, evidence, interpretation, and source through scale and spacing
- keep KPI numerals visually distinct from their labels
- tune Chinese leading and paragraph spacing independently from Latin defaults
- prohibit long paragraphs inside shallow hero text boxes

---

## 12. Image and Artwork Pipeline

### 12.1 When to use imagery

Use imagery when it contributes:

- emotion
- place
- people
- product context
- atmosphere
- metaphor

Do not use imagery merely to fill empty space on an analytical slide.

### 12.2 Prompt contract

Every prompt includes:

- purpose in the slide
- composition and focal placement
- camera or perspective
- palette and lighting
- style consistency token
- negative space requirement
- prohibited text, logos, signatures, and watermarks
- treatment of identifiable people

### 12.3 Technical normalization

The asset layer must:

- detect actual file format from bytes
- discover `.jpg`, `.jpeg`, or `.webp` siblings when `.png` was requested
- normalize final assets to real PNG files
- preserve alpha when present
- crop with focal awareness
- record provenance and prompt hash

---

## 13. Template and Reference Intelligence

### 13.1 Template reuse

Do not merely copy template colors.

Extract:

- slide masters and layouts
- recurring component geometry
- typography roles
- spacing rhythm
- shape treatments
- chart and table themes
- background systems
- page furniture

Map generated `SlideSpec` objects to the closest reusable template family. Create a
new layout only when no suitable family exists.

### 13.2 Reference-deck analysis

When a reference deck is provided:

- render all slides
- build a contact sheet
- cluster slide families
- infer grid and margins
- infer typography hierarchy
- measure image/vector/chart ratios
- identify repeated components
- distinguish brand language from topic-specific content

### 13.3 Image-reference analysis

Analyze:

- semantic mood
- geometry
- dominant and supporting colors
- contrast
- texture
- visual density
- focal position
- suitable usage scope

Palette extraction alone is insufficient.

---

## 14. Rendering Architecture

### 14.1 Constraint-based layout

Each component declares preferred, minimum, and maximum bounds. The layout engine
solves:

- grid placement
- alignment
- spacing
- collision avoidance
- hierarchy
- aspect-ratio preservation
- text fit

If content does not fit:

1. shorten non-essential copy
2. change component arrangement
3. switch to a more suitable slide family
4. split the slide with user approval
5. reduce type only within safe limits

### 14.2 Layering

Use a stable layer order:

```text
background
→ structural surfaces
→ data and diagrams
→ imagery
→ annotations
→ text
→ navigation and source notes
```

### 14.3 Editability

Charts, tables, labels, and diagrams should remain native PowerPoint objects wherever
the library permits. Rasterize only elements that cannot be represented reliably.

---

## 15. Visual Critic

The host model must critique rendered slide images, not only JSON state.

### 15.1 Slide-level review

Evaluate:

- five-second comprehension
- message prominence
- visual evidence
- alignment
- whitespace
- contrast
- text density
- chart legibility
- balance
- obvious template repetition
- rendering defects

### 15.2 Deck-level review

Evaluate the contact sheet for:

- narrative pacing
- section transitions
- visual rhythm
- density variation
- overused slide families
- color consistency
- repeated hero treatments
- weak opening or ending

### 15.3 Critic output

Every issue must include:

- slide number
- severity
- observed problem
- probable cause
- recommended repair scope
- measurable acceptance condition

Vague feedback such as “make it more professional” is invalid.

### 15.4 Independent review panel

Run four isolated reviews:

1. **Executive editor** — tests message clarity, decision value, and narrative.
2. **Information designer** — tests whether evidence uses the correct visual form.
3. **Art director** — tests hierarchy, composition, rhythm, and brand coherence.
4. **Production engineer** — tests editability, semantics, rendering, and file health.

Each reviewer sees only the evidence required for its role and scores independently.
The final quality score uses the conservative aggregate, not the generator's own
score.

Any disagreement greater than 15 points triggers a focused adjudication pass.

### 15.5 Pairwise selection

Absolute scoring is often unstable. When two valid candidates remain, show them
side-by-side with identical content and ask:

- which communicates the governing message faster?
- which makes the evidence easier to verify?
- which has stronger hierarchy and less decoration?
- which remains more editable and reusable?

Record the winning candidate and a short decision rationale for future retrieval.

### 15.6 Adversarial review

Before final acceptance, run a red-team pass that searches specifically for:

- unsupported claims
- misleading chart scales
- decorative visuals masquerading as evidence
- inconsistent numbers across slides
- weak assumptions hidden in footnotes
- accessibility failures
- generic AI patterns
- technically valid but visually poor layouts

The red-team pass can block delivery.

---

## 16. Validation and Quality Gates

### 16.1 Structural validation

- slide count and order
- title and fact fidelity
- source completeness
- file integrity
- valid image assets
- no out-of-bounds elements
- no unintended overlaps
- valid theme colors and fonts
- semantic PowerPoint bullets instead of literal bullet glyphs
- accurate presentation metadata, slide dimensions, timestamps, and authorship
- meaningful alt text for images, charts, and diagrams
- valid notes, hyperlinks, and embedded-workbook relationships

### 16.2 Visual validation

- rendered text is not clipped
- minimum type sizes are respected
- the approved typography profile is applied without silent substitution
- East Asian, Latin, and numeric runs use the intended script-specific families
- required glyphs and font weights are available
- contrast meets accessibility targets
- chart labels remain legible
- grid edges align within tolerance
- spacing tokens are respected
- no stretched or low-resolution images
- no visible watermarks
- typography remains readable at the declared viewing distance
- repeated component groups are centered and aligned to the global grid

### 16.3 Editorial validation

- every slide has one governing message
- every claim has evidence or an explicit confidence label
- no unsupported precision
- no duplicate slide purpose
- conclusions follow from evidence

### 16.4 Acceptance threshold

Delivery requires:

- no blocking issue
- overall quality score of at least 90 in deliberate mode
- no quality dimension below 82
- evidence, editability, and rendered-visual checks completed independently
- no unresolved red-team finding
- no regression against the current golden benchmark
- explicit human acceptance

An 85–89 score may be shown as a reviewable draft but must not be labeled final.

---

## 17. Benchmark-Specific Acceptance Test

For a nine-slide strategy deck comparable to the reviewed benchmark:

- cover includes headline, thesis, KPI anchors, context, and disclaimer
- user-approved typography creates distinct headline, body, label, and numeric roles
- executive summary converts conclusions into structured modules
- at least three evidence slides use native charts when source values exist
- quantitative comparisons are visually encoded rather than left as numeric prose
- valuation or benchmark comparison uses an editable table or equivalent precise
  comparison component
- scenario analysis uses a matrix, not a bullet list
- allocation is shown as an editable visual structure
- every analytical slide includes interpretation, not only data
- source notes and confidence labels are visible
- no analytical slide uses a decorative full-bleed image as its primary evidence
- adjacent slides do not repeat identical geometry
- recurring components use semantic grouping, masters, or reusable builders rather
  than hundreds of individually maintained decorative objects
- bullets, notes, alt text, and document metadata use native PowerPoint semantics
- all slides pass rendered-image review

The benchmark should be exceeded through:

- stronger source traceability
- more reliable editability
- explicit uncertainty handling
- brand/template intelligence
- targeted human control
- reproducible generation and repair

---

## 18. Host Runtime Contract

The agent reuses the calling host's capabilities.

### 18.1 Structured generation

The host supplies:

```python
generate_structured(prompt, schema) -> BaseModel | dict | JSON
```

### 18.2 Image generation

The host optionally supplies:

```python
generate_image(request, output_path) -> bytes | path | None
```

### 18.3 Vision critique

The host should supply a multimodal capability:

```python
critique_images(prompt, image_paths, schema) -> QualityReport
```

If the host lacks vision support, the agent performs structural validation and must
surface the missing visual-review capability as a delivery warning.

---

## 19. LangGraph State and Routing

### 19.1 State

The checkpointed state contains only JSON-serializable data:

- brief
- archetype
- evidence
- narrative
- reference analysis
- approved design system
- slide specifications
- asset plan and paths
- rendered preview paths
- quality reports
- repair history
- execution metrics and cache references
- artifacts

Host clients and tools remain in runtime context and are never checkpointed.

### 19.2 Conditional routes

```text
missing brief data → interrupt
reference supplied → inspect → interrupt
direction not approved → redesign
asset failure → retry → fallback
structural failure → targeted repair
visual score below threshold → visual repair
narrative failure → narrative replan
quality passed → final human acceptance
```

---

## 20. Implementation Roadmap

Construction must proceed in this order.

### Phase 0: evaluation and observability

- establish benchmark prompts, golden contact sheets, and human preference records
- add per-node latency, token, cache, retry, and quality-gain telemetry
- version prompts, schemas, design systems, and critic rubrics
- make every later phase measurable before expanding capability

### Phase 1: semantic planning

- add `DeckBrief`, `EvidenceItem`, `SlideSpec`, `DesignSystem`, and `QualityReport`
- add deck-type classification
- replace prose-only STORY generation with claim/evidence/visual-form planning

### Phase 2: visual system

- implement 12-column grid and spacing tokens
- implement installed-font discovery, glyph coverage, and script-specific font runs
- add typography profiles, rendered specimens, and a human approval interrupt
- build native component library
- replace rigid layout cycling with semantic slide-family routing

### Phase 3: analytical graphics

- implement native chart theme and chart builders
- implement editable tables, scenario matrices, allocation visuals, and risk maps

### Phase 4: design audition

- render real-content sample slides before approval
- add design-direction merge and revision actions
- add bounded best-of-N composition search for key slides
- add deterministic pruning and pairwise finalist selection

### Phase 5: rendered visual QA

- render every slide to PNG
- build contact sheets
- add independent editorial, information-design, art-direction, and production critics
- add pairwise comparison and adversarial red-team review
- implement targeted repair routing

### Phase 6: template intelligence

- infer reusable template components and slide families
- map slide specifications to existing masters and layouts

### Phase 7: benchmark harness

- store representative benchmark tasks
- score structure, editability, visual quality, and narrative performance
- prevent regressions with golden contact sheets and measurable thresholds

### Phase 8: token-efficient production

- add canonical evidence IDs and hierarchical context packets
- add content-addressed model and render caches
- add slide-local delta repair
- add contact-sheet-first progressive visual review
- enforce token telemetry and quality-per-token regression tests

---

## 21. Definition of Done

The v2 agent is complete only when:

- an analytical deck no longer defaults to illustration-led slides
- charts and tables are selected from evidence semantics
- sample content slides are approved before full production
- typography is rendered with real content and explicitly approved by the user
- script-specific fonts and fallbacks pass installation and glyph checks
- each slide is composed from editable components on a grid
- every slide is rendered and visually critiqued
- repair targets the responsible layer instead of regenerating the whole deck
- template references influence structure, not only palette
- key slides are selected from rendered structural alternatives, not first drafts
- independent critics and red-team review pass at the deliberate-mode threshold
- token savings come from caching, compact context, deterministic tools, and delta
  repair without reducing quality scores
- a benchmark strategy deck passes the acceptance test in Section 17
- human reviewers prefer v2 output to both the current output and the benchmark in
  blind pairwise evaluation — this last gate is an operational study, not a unit
  test in this repository
