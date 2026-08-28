from __future__ import annotations

import re
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.util import Emu, Inches, Pt

from ppt_expert.models import ChartSpec, DesignSpec, PageRole, StoryPage
from ppt_expert.pptx.primitives import speaker_notes

_R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
_R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
_SHAPE_TAILS = ("}sp", "}pic", "}graphicFrame", "}grpSp", "}cxnSp")
_SKIP_REL = ("slideLayout", "notesSlide", "slideMaster")
_CLONE_REL = (
    "chart",
    "package",
    "oleObject",
    "chartStyle",
    "chartColorStyle",
    "chartUserShapes",
)
_TITLE_TYPES = {
    PP_PLACEHOLDER.TITLE,
    PP_PLACEHOLDER.CENTER_TITLE,
    PP_PLACEHOLDER.VERTICAL_TITLE,
}
_BODY_TYPES = {
    PP_PLACEHOLDER.BODY,
    PP_PLACEHOLDER.OBJECT,
    PP_PLACEHOLDER.VERTICAL_BODY,
    PP_PLACEHOLDER.VERTICAL_OBJECT,
}
_CHROME_TYPES = {
    PP_PLACEHOLDER.FOOTER,
    PP_PLACEHOLDER.DATE,
    PP_PLACEHOLDER.SLIDE_NUMBER,
    PP_PLACEHOLDER.HEADER,
}


@dataclass
class SlideInfo:
    index: int
    text_count: int
    chart_count: int
    table_count: int
    picture_count: int


def edit_template(
    pages: list[StoryPage],
    design: DesignSpec,
    image_paths: dict[str, str],
    output_path: str | Path,
    template_path: str | Path,
) -> str:
    _ = design, image_paths
    output = Path(output_path)
    presentation = Presentation(str(template_path))
    if not presentation.slides:
        presentation.slides.add_slide(
            min(presentation.slide_layouts, key=lambda layout: len(layout.placeholders))
        )
    sources = _assign_sources(presentation, pages)
    for index in sources:
        _clone_slide(presentation, index)
    original = len(presentation.slides) - len(sources)
    for _ in range(original):
        _delete_slide(presentation, 0)
    for slide, page in zip(presentation.slides, pages, strict=True):
        _edit_slide(presentation, slide, page)
    presentation.core_properties.title = pages[0].title if pages else "Deck"
    presentation.core_properties.author = "PPT Expert"
    output.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(output)
    return str(output.resolve())


def _assign_sources(presentation, pages: list[StoryPage]) -> list[int]:
    inventory = [_info(slide, index) for index, slide in enumerate(presentation.slides)]
    if len(inventory) == len(pages):
        return [item.index for item in inventory]
    used: set[int] = set()
    assigned: list[int] = []
    last = max(len(inventory) - 1, 0)
    for page in pages:
        unused = [item for item in inventory if item.index not in used]
        pool = unused or inventory
        best = max(pool, key=lambda item: _score(item, page, last))
        assigned.append(best.index)
        if unused:
            used.add(best.index)
    return assigned


def _info(slide, index: int) -> SlideInfo:
    texts = charts = tables = pictures = 0
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False):
            texts += 1
        if getattr(shape, "has_chart", False):
            charts += 1
        if getattr(shape, "has_table", False):
            tables += 1
        if shape.shape_type in {MSO_SHAPE_TYPE.PICTURE, MSO_SHAPE_TYPE.LINKED_PICTURE}:
            pictures += 1
    return SlideInfo(index, texts, charts, tables, pictures)


def _score(info: SlideInfo, page: StoryPage, last_index: int) -> int:
    role = page.resolved_role()
    score = info.text_count
    if role == PageRole.COVER and info.index == 0:
        score += 8
    if role == PageRole.CLOSE and info.index == last_index:
        score += 8
    if page.chart:
        score += 12 if info.chart_count else -4
    if page.table:
        score += 10 if info.table_count else -2
    if page.image_id:
        score += 4 if info.picture_count else 0
    return score


def _clone_slide(presentation, index: int) -> None:
    source = presentation.slides[index]
    dest = presentation.slides.add_slide(source.slide_layout)
    tree = dest.shapes._spTree
    for child in list(tree):
        if any(child.tag.endswith(tail) for tail in _SHAPE_TAILS):
            tree.remove(child)
    rid_map = _copy_relationships(source.part, dest.part)
    for child in source.shapes._spTree:
        if not any(child.tag.endswith(tail) for tail in _SHAPE_TAILS):
            continue
        copied = deepcopy(child)
        for node in copied.iter():
            for attr in (_R_EMBED, _R_ID):
                old = node.get(attr)
                if old in rid_map:
                    node.set(attr, rid_map[old])
        tree.append(copied)


def _copy_relationships(source_part, dest_part) -> dict[str, str]:
    mapping: dict[str, str] = {}
    package = dest_part.package
    for rel_id, rel in source_part.rels.items():
        if any(token in rel.reltype for token in _SKIP_REL):
            continue
        with suppress(Exception):
            if rel.is_external:
                mapping[rel_id] = dest_part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
                continue
            target = rel.target_part
            if _should_clone_rel(rel.reltype):
                target = _clone_part(package, target)
            mapping[rel_id] = dest_part.relate_to(target, rel.reltype)
    return mapping


def _should_clone_rel(reltype: str) -> bool:
    return any(token in reltype for token in _CLONE_REL)


def _clone_part(package, source):
    copied = type(source).load(
        package.next_partname(_partname_template(source.partname)),
        source.content_type,
        package,
        source.blob,
    )
    for rel in source.rels.values():
        with suppress(Exception):
            if rel.is_external:
                copied.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
            elif _should_clone_rel(rel.reltype):
                copied.relate_to(_clone_part(package, rel.target_part), rel.reltype)
            else:
                copied.relate_to(rel.target_part, rel.reltype)
    return copied


def _partname_template(partname) -> str:
    text = str(partname)
    numbered = re.sub(r"(\d+)(?=\.\w+$)", "%d", text, count=1)
    if "%d" in numbered:
        return numbered
    stem, dot, suffix = text.rpartition(".")
    if dot:
        return f"{stem}%d.{suffix}"
    return f"{text}%d"


def _delete_slide(presentation, index: int) -> None:
    slide_id = presentation.slides._sldIdLst[index]
    presentation.part.drop_rel(slide_id.rId)
    presentation.slides._sldIdLst.remove(slide_id)


def _edit_slide(presentation, slide, page: StoryPage) -> None:
    titles, subtitles, bodies = _classify_text(slide, presentation)
    if not titles:
        titles = [_add_title_box(presentation, slide)]
    _put_text(titles[0], page.title)
    extras = [page.eyebrow, page.subtitle]
    for shape, value in zip(titles[1:], extras, strict=False):
        if value:
            _put_text(shape, value)
    if subtitles:
        _put_text(subtitles[0], page.subtitle or page.eyebrow or page.takeaway)
    compact, flowing = _split_compact(bodies)
    kpi_bits = [bit for item in page.kpis for bit in (item.value, item.label) if bit]
    for shape, value in zip(compact, kpi_bits, strict=False):
        _put_text(shape, value)
    flowing = compact[len(kpi_bits) :] + flowing
    if not flowing:
        flowing = [_add_body_box(presentation, slide)]
    chunks = list(page.content)
    if page.takeaway:
        chunks.append(page.takeaway)
    if len(flowing) == 1:
        _put_paragraphs(flowing[0], chunks)
    else:
        for shape, value in zip(flowing, chunks, strict=False):
            _put_text(shape, value)
        if len(chunks) > len(flowing):
            _put_paragraphs(flowing[-1], chunks[len(flowing) - 1 :])
        for shape in flowing[len(chunks) :]:
            _put_text(shape, "")
    _replace_chart(slide, page.chart)
    _replace_table(slide, page)
    speaker_notes(slide, page)


def _add_title_box(presentation, slide):
    margin = int(Inches(0.6))
    inner = presentation.slide_width - 2 * margin
    shape = slide.shapes.add_textbox(Emu(margin), Inches(0.45), Emu(inner), Inches(1.1))
    shape.text_frame.word_wrap = True
    shape.text_frame.paragraphs[0].font.size = Pt(28)
    return shape


def _add_body_box(presentation, slide):
    margin = int(Inches(0.6))
    inner = presentation.slide_width - 2 * margin
    shape = slide.shapes.add_textbox(
        Emu(margin),
        Inches(1.8),
        Emu(inner),
        presentation.slide_height - int(Inches(2.4)),
    )
    shape.text_frame.word_wrap = True
    return shape


def _classify_text(slide, presentation) -> tuple[list, list, list]:
    titles: list = []
    subtitles: list = []
    bodies: list = []
    slide_h = presentation.slide_height.inches
    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False):
            continue
        if _is_chrome(shape, slide_h):
            continue
        if getattr(shape, "is_placeholder", False):
            kind = shape.placeholder_format.type
            if kind in _CHROME_TYPES:
                continue
            if kind in _TITLE_TYPES:
                titles.append(shape)
                continue
            if kind == PP_PLACEHOLDER.SUBTITLE:
                subtitles.append(shape)
                continue
            if kind in _BODY_TYPES:
                bodies.append(shape)
                continue
        bodies.append(shape)
    bodies.sort(key=lambda shape: (shape.top, shape.left))
    if not titles:
        band = [shape for shape in bodies if shape.top.inches < 1.7]
        if band:
            chosen = max(band, key=lambda shape: shape.width)
            titles.append(chosen)
            bodies.remove(chosen)
    return titles, subtitles, bodies


def _is_chrome(shape, slide_h: float) -> bool:
    bottom = shape.top.inches + shape.height.inches
    return shape.height.inches < 0.38 and bottom > slide_h - 0.5


def _split_compact(shapes: list) -> tuple[list, list]:
    compact = [shape for shape in shapes if shape.height.inches <= 0.72]
    flowing = [shape for shape in shapes if shape.height.inches > 0.72]
    return compact, flowing


def _put_text(shape, text: str) -> None:
    frame = shape.text_frame
    frame.word_wrap = True
    paragraphs = list(frame.paragraphs)
    if not paragraphs:
        frame.text = text
        return
    _put_run(paragraphs[0], text)
    for paragraph in paragraphs[1:]:
        _put_run(paragraph, "")


def _put_paragraphs(shape, items: list[str]) -> None:
    frame = shape.text_frame
    frame.word_wrap = True
    while len(frame.paragraphs) < len(items):
        frame.add_paragraph()
    for index, paragraph in enumerate(frame.paragraphs):
        _put_run(paragraph, items[index] if index < len(items) else "")


def _put_run(paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
        return
    paragraph.text = text


def _replace_chart(slide, spec: ChartSpec | None) -> None:
    if spec is None:
        return
    for shape in slide.shapes:
        if not getattr(shape, "has_chart", False):
            continue
        data = CategoryChartData()
        data.categories = spec.categories
        for series in spec.series:
            data.add_series(series.name, series.values)
        with suppress(Exception):
            shape.chart.replace_data(data)
            return


def _replace_table(slide, page: StoryPage) -> None:
    spec = page.table
    if spec is None:
        return
    for shape in slide.shapes:
        if not getattr(shape, "has_table", False):
            continue
        table = shape.table
        for index, header in enumerate(spec.headers):
            if index < len(table.columns):
                table.cell(0, index).text = header
        for row_index, row in enumerate(spec.rows, 1):
            if row_index >= len(table.rows):
                break
            for col_index, value in enumerate(row):
                if col_index < len(table.columns):
                    table.cell(row_index, col_index).text = value
        return
