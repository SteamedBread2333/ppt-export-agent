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


class ReferenceAnalysis(BaseModel):
    source_type: Literal["template", "images", "mixed"]
    template_path: str | None = None
    image_paths: list[str] = Field(default_factory=list)
    preview_paths: list[str] = Field(default_factory=list)
    style: StyleOption
    title_font: str | None = None
    body_font: str | None = None
    notes: list[str] = Field(default_factory=list)


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


class StoryPage(BaseModel):
    number: int = Field(ge=1)
    title: str
    content: list[str] = Field(min_length=1)
    visual_direction: str
    layout: LayoutType
    image_id: str | None = None
    section: str = ""


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


class ArtifactBundle(BaseModel):
    project_dir: str
    pptx_path: str
    story_path: str
    design_path: str
    report_path: str
    preview_paths: list[str] = Field(default_factory=list)


class PPTAgentState(TypedDict, total=False):
    request: str
    project_name: str
    project_dir: str
    template_path: str | None
    reference_images: list[str]
    reference_analysis: dict[str, Any]
    reference_decision: str
    outline: dict[str, Any]
    styles: list[dict[str, Any]]
    style_preview_paths: list[str]
    selected_style: dict[str, Any]
    story: list[dict[str, Any]]
    design: dict[str, Any]
    image_plan: list[dict[str, Any]]
    image_paths: dict[str, str]
    pptx_path: str
    validation: dict[str, Any]
    repair_attempts: int
    artifacts: dict[str, Any]


def absolute(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())
