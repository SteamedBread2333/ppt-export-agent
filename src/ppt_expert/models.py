from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field, field_validator


class LayoutType(StrEnum):
    HERO = "hero"
    LEFT_IMAGE = "left_image"
    RIGHT_IMAGE = "right_image"
    TOP_IMAGE = "top_image"
    TEXT = "text"
    DATA_CARDS = "data_cards"


class SlideFamily(StrEnum):
    COVER = "cover"
    SECTION = "section"
    EXECUTIVE_SUMMARY = "executive_summary"
    KPI_STRIP = "kpi_strip"
    CHART_INTERPRETATION = "chart_interpretation"
    DUAL_CHART = "dual_chart"
    TABLE_COMPARISON = "table_comparison"
    SCENARIO_MATRIX = "scenario_matrix"
    ALLOCATION = "allocation"
    WATERFALL = "waterfall"
    HEATMAP = "heatmap"
    TIMELINE = "timeline"
    PILLARS = "pillars"
    QUOTE = "quote"
    CONCLUSION = "conclusion"
    APPENDIX = "appendix"
    HERO = "hero"
    LEFT_IMAGE = "left_image"
    RIGHT_IMAGE = "right_image"
    TOP_IMAGE = "top_image"
    TEXT = "text"
    DATA_CARDS = "data_cards"


class DeckArchetype(StrEnum):
    STRATEGY = "strategy"
    RESEARCH = "research"
    PRODUCT = "product"
    NARRATIVE = "narrative"
    OPERATING = "operating"


class VisualForm(StrEnum):
    KPI = "kpi"
    CHART = "chart"
    TABLE = "table"
    MATRIX = "matrix"
    ALLOCATION = "allocation"
    WATERFALL = "waterfall"
    HEATMAP = "heatmap"
    TIMELINE = "timeline"
    DIAGRAM = "diagram"
    QUOTE = "quote"
    NARRATIVE = "narrative"


class ChartType(StrEnum):
    LINE = "line"
    COLUMN = "column"
    BAR = "bar"
    AREA = "area"


class OutlinePage(BaseModel):
    number: int = Field(ge=1)
    title: str = Field(min_length=1)
    core_content: list[str] = Field(min_length=1)
    section: str = ""


class OutlinePlan(BaseModel):
    title: str
    audience: str = ""
    purpose: str = ""
    pages: list[OutlinePage] = Field(min_length=1)

    @field_validator("pages")
    @classmethod
    def contiguous_pages(cls, pages: list[OutlinePage]) -> list[OutlinePage]:
        expected = list(range(1, len(pages) + 1))
        actual = [page.number for page in pages]
        if actual != expected:
            raise ValueError(f"page numbers must be contiguous: expected {expected}, got {actual}")
        return pages


class StyleOption(BaseModel):
    key: Literal["A", "B", "C", "D"]
    name: str
    mood: str
    primary: str
    secondary: str
    background: str
    text: str
    accent: str

    @field_validator("primary", "secondary", "background", "text", "accent")
    @classmethod
    def valid_hex(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must be #RRGGBB")
        int(value[1:], 16)
        return value


class StyleOptions(BaseModel):
    options: list[StyleOption] = Field(min_length=4, max_length=4)

    @field_validator("options")
    @classmethod
    def unique_keys(cls, values: list[StyleOption]) -> list[StyleOption]:
        if {item.key for item in values} != {"A", "B", "C", "D"}:
            raise ValueError("style keys must be A, B, C and D")
        return values


class TypographyProfile(BaseModel):
    id: str
    name: str
    mood: str
    latin_font: str
    east_asian_font: str
    numeric_font: str
    fallbacks: list[str] = Field(default_factory=list)
    recommended: bool = False
    installed: bool = True
    specimen_path: str | None = None


class KPIItem(BaseModel):
    value: str
    label: str
    note: str = ""


class ChartSeries(BaseModel):
    name: str
    values: list[float] = Field(min_length=1)


class ChartSpec(BaseModel):
    chart_type: ChartType = ChartType.LINE
    title: str = ""
    categories: list[str] = Field(min_length=1)
    series: list[ChartSeries] = Field(min_length=1)


class TableSpec(BaseModel):
    headers: list[str] = Field(min_length=1)
    rows: list[list[str]] = Field(min_length=1)
    highlight_row: int | None = None


class AllocationItem(BaseModel):
    label: str
    percent: float = Field(ge=0, le=100)
    note: str = ""


class ScenarioColumn(BaseModel):
    name: str
    probability: str
    trigger: str = ""
    outcome: str = ""
    implication: str = ""
    featured: bool = False


class WaterfallItem(BaseModel):
    label: str
    value: float
    total: bool = False


class HeatmapSpec(BaseModel):
    rows: list[str] = Field(min_length=1)
    columns: list[str] = Field(min_length=1)
    values: list[list[float]] = Field(min_length=1)


class Milestone(BaseModel):
    label: str
    date: str = ""
    note: str = ""


class DeckBrief(BaseModel):
    objective: str
    audience: str = ""
    decision_context: str = ""
    duration_minutes: int = 20
    language: str = "en"
    slide_count: int = 1
    primary_archetype: DeckArchetype = DeckArchetype.RESEARCH
    secondary_archetype: DeckArchetype | None = None
    density: Literal["low", "medium", "high"] = "medium"

    def needs_confirmation(self) -> bool:
        return not self.audience.strip() or not self.objective.strip()


class EvidenceItem(BaseModel):
    id: str
    kind: Literal["claim", "metric", "quote", "event", "recommendation", "risk"] = "claim"
    statement: str
    value: float | None = None
    unit: str = ""
    period: str = ""
    source: str | None = None
    confidence: Literal["confirmed", "estimated", "illustrative"] = "estimated"


class EvidenceBundle(BaseModel):
    items: list[EvidenceItem] = Field(default_factory=list)


class SlideQuality(BaseModel):
    page: int
    score: int = Field(ge=0, le=100)
    family: str
    issues: list[str] = Field(default_factory=list)


class ReferenceAnalysis(BaseModel):
    source_type: Literal["template", "images", "mixed"]
    template_path: str | None = None
    image_paths: list[str] = Field(default_factory=list)
    preview_paths: list[str] = Field(default_factory=list)
    style: StyleOption
    title_font: str | None = None
    body_font: str | None = None
    notes: list[str] = Field(default_factory=list)
    layout_families: list[str] = Field(default_factory=list)


class DesignSpec(BaseModel):
    style_name: str
    mood: str
    primary: str
    secondary: str
    background: str
    text: str
    accent: str
    title_font: str = "PingFang SC"
    body_font: str = "PingFang SC"
    title_font_fallbacks: list[str] = Field(
        default_factory=lambda: ["Microsoft YaHei", "Arial"]
    )
    body_font_fallbacks: list[str] = Field(
        default_factory=lambda: ["Microsoft YaHei", "Arial"]
    )
    title_size: int = Field(default=30, ge=24, le=52)
    body_size: int = Field(default=18, ge=12, le=28)
    illustration_style: str
    forbidden_elements: list[str] = Field(
        default_factory=lambda: [
            "text",
            "watermarks",
            "signatures",
            "identifiable faces",
        ]
    )
    muted: str | None = None
    surface: str | None = None
    latin_font: str | None = None
    east_asian_font: str | None = None
    numeric_font: str | None = None
    typography_profile: str = "modern_consulting"
    positive: str | None = None
    negative: str | None = None
    warning: str | None = None
    grid_columns: int = 12
    grid_gutter: float = 0.16
    safe_margin: float = 0.62

    @field_validator("muted", "surface", "positive", "negative", "warning")
    @classmethod
    def optional_hex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.upper()
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must be #RRGGBB")
        int(value[1:], 16)
        return value

    def palette_hex(self) -> set[str]:
        values = [
            self.primary,
            self.secondary,
            self.background,
            self.text,
            self.accent,
            "#FFFFFF",
            self.muted,
            self.surface,
            self.positive,
            self.negative,
            self.warning,
        ]
        return {item.upper() for item in values if item}

    def allowed_font_names(self) -> set[str]:
        names = [
            self.title_font,
            self.body_font,
            *self.title_font_fallbacks,
            *self.body_font_fallbacks,
            self.latin_font,
            self.east_asian_font,
            self.numeric_font,
        ]
        return {name.casefold() for name in names if name}


class StoryPage(BaseModel):
    number: int = Field(ge=1)
    title: str
    content: list[str] = Field(min_length=1)
    visual_direction: str
    layout: LayoutType
    image_id: str | None = None
    section: str = ""
    family: SlideFamily | None = None
    eyebrow: str = ""
    subtitle: str = ""
    takeaway: str = ""
    source_note: str = ""
    kpis: list[KPIItem] = Field(default_factory=list)
    chart: ChartSpec | None = None
    table: TableSpec | None = None
    allocation: list[AllocationItem] = Field(default_factory=list)
    scenarios: list[ScenarioColumn] = Field(default_factory=list)
    waterfall: list[WaterfallItem] = Field(default_factory=list)
    heatmap: HeatmapSpec | None = None
    milestones: list[Milestone] = Field(default_factory=list)
    quote: str = ""
    chart_secondary: ChartSpec | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    visual_form: VisualForm | None = None
    confidence: Literal["confirmed", "estimated", "illustrative"] = "estimated"
    purpose: str = ""
    composition: str = ""

    def resolved_family(self) -> SlideFamily:
        if self.family is not None:
            return self.family
        return SlideFamily(self.layout.value)

    def needs_artwork(self) -> bool:
        if not self.image_id:
            return False
        family = self.resolved_family()
        return family in {
            SlideFamily.HERO,
            SlideFamily.LEFT_IMAGE,
            SlideFamily.RIGHT_IMAGE,
            SlideFamily.TOP_IMAGE,
        }


class StoryDesignBundle(BaseModel):
    pages: list[StoryPage] = Field(min_length=1)
    design: DesignSpec


class ImageRequest(BaseModel):
    image_id: str
    page_numbers: list[int]
    prompt: str
    width: int = 1536
    height: int = 1024
    transparent: bool = False


class ImagePlan(BaseModel):
    images: list[ImageRequest] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    code: str
    message: str
    page: int | None = None
    severity: Literal["error", "warning"] = "error"


class ValidationReport(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    pptx_path: str


class QualityIssue(BaseModel):
    code: str
    message: str
    page: int | None = None
    severity: Literal["error", "warning"] = "warning"
    cause: str = ""
    repair_scope: Literal["token", "component", "slide", "rhythm", "narrative"] = "slide"
    acceptance: str = ""


class VisionCritique(BaseModel):
    score: int = Field(ge=0, le=100)
    issues: list[QualityIssue] = Field(default_factory=list)
    notes: str = "completed"


class QualityReport(BaseModel):
    score: int = Field(ge=0, le=100)
    blocking_issues: list[QualityIssue] = Field(default_factory=list)
    warnings: list[QualityIssue] = Field(default_factory=list)
    dimensions: dict[str, int] = Field(default_factory=dict)
    critic_scores: dict[str, int] = Field(default_factory=dict)
    slide_scores: list[SlideQuality] = Field(default_factory=list)
    contact_sheet_path: str = ""
    delivery: Literal["final", "reviewable_draft"] = "reviewable_draft"
    vision_review: str = "structural_only"


class ArtifactBundle(BaseModel):
    project_dir: str
    pptx_path: str
    story_path: str
    design_path: str
    report_path: str
    preview_paths: list[str] = Field(default_factory=list)
    quality_path: str = ""
    contact_sheet_path: str = ""


class PPTAgentState(TypedDict, total=False):
    request: str
    project_name: str
    project_dir: str
    template_path: str | None
    reference_images: list[str]
    reference_analysis: dict[str, Any]
    reference_decision: str
    outline: dict[str, Any]
    brief: dict[str, Any]
    evidence: list[dict[str, Any]]
    styles: list[dict[str, Any]]
    style_preview_paths: list[str]
    selected_style: dict[str, Any]
    typography_profiles: list[dict[str, Any]]
    typography_preview_paths: list[str]
    selected_typography: dict[str, Any]
    story: list[dict[str, Any]]
    design: dict[str, Any]
    image_plan: list[dict[str, Any]]
    image_paths: dict[str, str]
    pptx_path: str
    validation: dict[str, Any]
    quality: dict[str, Any]
    contact_sheet_path: str
    draft_decision: str
    draft_notes: str
    repair_attempts: int
    composition_path: str
    artifacts: dict[str, Any]


def absolute(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())
