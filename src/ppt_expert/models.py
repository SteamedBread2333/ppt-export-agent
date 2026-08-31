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


class RecipeId(StrEnum):
    CONSULTING = "consulting"
    WORK_REPORT = "work_report"
    CIVIC = "civic"
    ART_MARKET = "art_market"
    EDITORIAL = "editorial"
    HISTORY = "history"
    OPEN = "open"


class LayoutScheme(StrEnum):
    RULES = "rules"
    STACK = "stack"
    BANNER = "banner"
    BLOCKS = "blocks"
    SPREAD = "spread"
    SPINE = "spine"


class PageRole(StrEnum):
    COVER = "cover"
    OVERVIEW = "overview"
    CONTEXT = "context"
    EVIDENCE = "evidence"
    STRUCTURE = "structure"
    EXPANSION = "expansion"
    SCENARIO = "scenario"
    CLOSE = "close"


class IntentSlots(BaseModel):
    topic: str
    audience: str = ""
    objective: str = ""
    slide_count: int = Field(default=8, ge=1, le=40)
    editable: bool = True
    delivery_format: str = "pptx"
    density: Literal["low", "medium", "high"] = "medium"

    def needs_confirmation(self) -> bool:
        return not self.topic.strip() or not self.audience.strip() or not self.objective.strip()


class ColorRoles(BaseModel):
    bg: str
    surface: str
    ink: str
    ink2: str
    muted: str
    accent: str
    positive: str
    caution: str
    risk: str
    hairline: str
    dark_bg: str
    dark_ink: str
    dark_muted: str
    dark_accent: str
    dark_hairline: str

    @field_validator(
        "bg",
        "surface",
        "ink",
        "ink2",
        "muted",
        "accent",
        "positive",
        "caution",
        "risk",
        "hairline",
        "dark_bg",
        "dark_ink",
        "dark_muted",
        "dark_accent",
        "dark_hairline",
    )
    @classmethod
    def valid_hex(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must be #RRGGBB")
        int(value[1:], 16)
        return value


class FontRoles(BaseModel):
    cn: str = "PingFang SC"
    num: str = "Arial"
    display: str = "PingFang SC"


class PageMetrics(BaseModel):
    w: float = 13.333
    h: float = 7.5
    mx: float = 0.62
    header_nav_y: float = 0.30
    header_title_y: float = 0.52
    header_title_h: float = 0.48
    header_rule_y: float = 1.10
    content_top: float = 1.42
    content_bottom: float = 6.72
    implication_y: float = 6.36
    footer_y: float = 7.12


class DesignTokens(BaseModel):
    recipe_id: RecipeId
    colors: ColorRoles
    fonts: FontRoles
    page: PageMetrics = Field(default_factory=PageMetrics)
    visual_proposition: str
    tension: str
    image_behavior: str = "vector_first"
    layout_scheme: LayoutScheme = LayoutScheme.RULES

    def palette_hex(self) -> set[str]:
        values = list(self.colors.model_dump().values()) + ["#FFFFFF", "#000000"]
        return {item.upper() for item in values}

    def to_design_spec(self) -> DesignSpec:
        colors = self.colors
        return DesignSpec(
            style_name=self.recipe_id.value,
            mood=self.visual_proposition,
            primary=colors.accent,
            secondary=colors.ink2,
            background=colors.bg,
            text=colors.ink,
            accent=colors.accent,
            title_font=self.fonts.display,
            body_font=self.fonts.cn,
            latin_font=self.fonts.num,
            east_asian_font=self.fonts.cn,
            numeric_font=self.fonts.num,
            muted=colors.muted,
            surface=colors.surface,
            positive=colors.positive,
            negative=colors.risk,
            warning=colors.caution,
            illustration_style=self.image_behavior,
            typography_profile=self.recipe_id.value,
            token_palette=list(self.palette_hex()),
        )


class StyleBrief(BaseModel):
    adjectives: list[str] = Field(min_length=3, max_length=3)
    tension: str
    density: Literal["low", "medium", "high"] = "medium"
    color_logic: str
    type_logic: str
    image_behavior: str
    spatial_rhythm: str
    recipe_id: RecipeId
    visual_proposition: str
    mixing_note: str = ""


class GuardWarning(BaseModel):
    page: int
    token: str
    box_width: float
    recommended: float
    message: str


class GuardReport(BaseModel):
    warnings: list[GuardWarning] = Field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.warnings


class EnvironmentReport(BaseModel):
    soffice: bool = True
    pdftoppm: bool = True
    pil: bool = True
    visual_review: Literal["full"] = "full"


class VolumeReview(BaseModel):
    rhythm_ok: bool = True
    no_adjacent_repeat: bool = True
    no_empty_bottom: bool = True
    chrome_locked: bool = True
    representative_pages: list[int] = Field(default_factory=list)
    issues: list[QualityIssue] = Field(default_factory=list)
    montage_path: str = ""
    pdf_path: str = ""


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
    token_palette: list[str] = Field(default_factory=list)

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
        return {item.upper() for item in values if item} | {
            item.upper() for item in self.token_palette if item
        }

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
    role: PageRole | None = None
    speaker_notes: str = ""

    def resolved_family(self) -> SlideFamily:
        if self.family is not None:
            return self.family
        return SlideFamily(self.layout.value)

    def resolved_role(self) -> PageRole:
        if self.role is not None:
            return self.role
        family = self.resolved_family()
        mapping = {
            SlideFamily.COVER: PageRole.COVER,
            SlideFamily.HERO: PageRole.COVER,
            SlideFamily.EXECUTIVE_SUMMARY: PageRole.OVERVIEW,
            SlideFamily.KPI_STRIP: PageRole.OVERVIEW,
            SlideFamily.CHART_INTERPRETATION: PageRole.CONTEXT,
            SlideFamily.DUAL_CHART: PageRole.STRUCTURE,
            SlideFamily.TABLE_COMPARISON: PageRole.EVIDENCE,
            SlideFamily.WATERFALL: PageRole.EVIDENCE,
            SlideFamily.HEATMAP: PageRole.EVIDENCE,
            SlideFamily.ALLOCATION: PageRole.STRUCTURE,
            SlideFamily.TIMELINE: PageRole.STRUCTURE,
            SlideFamily.PILLARS: PageRole.EXPANSION,
            SlideFamily.DATA_CARDS: PageRole.EXPANSION,
            SlideFamily.SCENARIO_MATRIX: PageRole.SCENARIO,
            SlideFamily.CONCLUSION: PageRole.CLOSE,
            SlideFamily.QUOTE: PageRole.CLOSE,
            SlideFamily.SECTION: PageRole.OVERVIEW,
            SlideFamily.APPENDIX: PageRole.EVIDENCE,
        }
        if family in mapping:
            return mapping[family]
        if self.scenarios:
            return PageRole.SCENARIO
        if self.chart:
            return PageRole.CONTEXT
        if self.table:
            return PageRole.EVIDENCE
        if self.allocation:
            return PageRole.STRUCTURE
        return PageRole.EXPANSION

    def is_dark(self) -> bool:
        return self.resolved_role() in {PageRole.COVER, PageRole.CLOSE}

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


class StoryDraft(BaseModel):
    pages: list[StoryPage] = Field(min_length=1)


class IntentOutline(BaseModel):
    intent: IntentSlots
    outline: OutlinePlan


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
    montage_path: str = ""
    delivery_path: str = ""


class PPTAgentState(TypedDict, total=False):
    request: str
    project_name: str
    project_dir: str
    template_path: str | None
    reference_images: list[str]
    intent: dict[str, Any]
    recipe_id: str
    match_reason: str
    style_brief: dict[str, Any]
    environment: dict[str, Any]
    outline: dict[str, Any]
    evidence: list[dict[str, Any]]
    story: list[dict[str, Any]]
    design: dict[str, Any]
    tokens: dict[str, Any]
    image_plan: list[dict[str, Any]]
    image_paths: dict[str, str]
    pptx_path: str
    guards: dict[str, Any]
    review: dict[str, Any]
    validation: dict[str, Any]
    montage_path: str
    delivery_decision: str
    delivery_notes: str
    repair_attempts: int
    artifacts: dict[str, Any]


def absolute(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


VolumeReview.model_rebuild()
