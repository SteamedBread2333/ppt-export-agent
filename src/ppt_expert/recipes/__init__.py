from __future__ import annotations

from ppt_expert.models import (
    ColorRoles,
    DesignTokens,
    FontRoles,
    IntentSlots,
    LayoutScheme,
    RecipeId,
    StyleBrief,
)

FOUNDATIONS = [
    "Visual proposition first: one sentence plus a tension decides later conflicts.",
    "Hierarchy before decoration: assertion, section label, evidence, footnote.",
    "Density is bandwidth, not smaller type.",
    "Think in vertical bands: context, assertion, rule, evidence, implication, folio.",
    "Background is a low-frequency identity layer or it is deleted.",
]

_KEYWORDS: dict[RecipeId, tuple[str, ...]] = {
    RecipeId.CONSULTING: (
        "研报",
        "研究",
        "策略",
        "咨询",
        "决策",
        "research",
        "strategy",
        "outlook",
        "consulting",
        "allocation",
    ),
    RecipeId.WORK_REPORT: (
        "汇报",
        "述职",
        "进度",
        "经营",
        "kpi",
        "operating",
        "status",
        "report",
    ),
    RecipeId.CIVIC: ("党建", "社区", "政务", "志愿", "civic", "community"),
    RecipeId.ART_MARKET: ("市集", "艺术", "海报", "策展", "art market", "poster"),
    RecipeId.EDITORIAL: ("画册", "展览", "杂志", "gallery", "editorial", "museum"),
    RecipeId.HISTORY: ("历史", "教学", "博物馆", "编年", "history", "classroom"),
}


def match_recipe(blob: str, intent: IntentSlots | None = None) -> RecipeId:
    recipe, _reason = match_recipe_with_reason(blob, intent)
    return recipe


def match_recipe_with_reason(blob: str, intent: IntentSlots | None = None) -> tuple[RecipeId, str]:
    text = blob.casefold()
    if intent is not None:
        text = f"{text} {intent.topic} {intent.audience} {intent.objective}".casefold()
    scored = [
        (recipe, [token for token in tokens if token.casefold() in text])
        for recipe, tokens in _KEYWORDS.items()
    ]
    scored.sort(key=lambda item: len(item[1]), reverse=True)
    winner, hits = scored[0]
    if not hits:
        return RecipeId.OPEN, "No recipe keywords matched; open brief is recommended."
    preview = ", ".join(hits[:4])
    return winner, f"Recommended from request cues: {preview}."


def recipe_choices(recommended: RecipeId) -> list[dict[str, object]]:
    ranked = [recommended, *[item for item in RecipeId if item != recommended]]
    return [
        {
            "id": recipe.value,
            "label": _LABELS[recipe],
            "proposition": tokens_for(recipe).visual_proposition,
            "layout_scheme": tokens_for(recipe).layout_scheme.value,
            "recommended": recipe == recommended,
        }
        for recipe in ranked
    ]


def tokens_for(recipe_id: RecipeId) -> DesignTokens:
    return _RECIPES[recipe_id]


def build_style_brief(intent: IntentSlots, recipe_id: RecipeId, mixing_note: str = "") -> StyleBrief:
    tokens = tokens_for(recipe_id)
    adjectives = _ADJECTIVES[recipe_id]
    return StyleBrief(
        adjectives=adjectives,
        tension=tokens.tension,
        density=intent.density,
        color_logic=(
            "Role-based: ink, ink2, muted, accent, semantic positive/caution/risk, "
            f"hairline, dark set. Accent {tokens.colors.accent}."
        ),
        type_logic=(
            f"Display {tokens.fonts.display}; body {tokens.fonts.cn}; "
            f"numerals {tokens.fonts.num}; protect short tokens as single-line."
        ),
        image_behavior=tokens.image_behavior,
        spatial_rhythm=_RHYTHM[recipe_id],
        recipe_id=recipe_id,
        visual_proposition=tokens.visual_proposition,
        mixing_note=mixing_note,
    )


def _t(
    recipe_id: RecipeId,
    colors: dict[str, str],
    proposition: str,
    tension: str,
    fonts: FontRoles | None = None,
    image_behavior: str = "vector_first",
    layout_scheme: LayoutScheme = LayoutScheme.RULES,
) -> DesignTokens:
    return DesignTokens(
        recipe_id=recipe_id,
        colors=ColorRoles(**colors),
        fonts=fonts or FontRoles(),
        visual_proposition=proposition,
        tension=tension,
        image_behavior=image_behavior,
        layout_scheme=layout_scheme,
    )


_RECIPES = {
    RecipeId.CONSULTING: _t(
        RecipeId.CONSULTING,
        {
            "bg": "#F7F8FA",
            "surface": "#EEF1F4",
            "ink": "#1B242C",
            "ink2": "#44505C",
            "muted": "#6B7785",
            "accent": "#1F4E79",
            "positive": "#2F6F4E",
            "caution": "#C47B17",
            "risk": "#A61B1B",
            "hairline": "#D5DCE3",
            "dark_bg": "#12263A",
            "dark_ink": "#F4F8FB",
            "dark_muted": "#9BB0C1",
            "dark_accent": "#F29E4C",
            "dark_hairline": "#2A4158",
        },
        "Analytical, compressed, calm. The page reads as a decision file.",
        "Rigorous but readable",
        layout_scheme=LayoutScheme.RULES,
    ),
    RecipeId.WORK_REPORT: _t(
        RecipeId.WORK_REPORT,
        {
            "bg": "#FBF8F4",
            "surface": "#F3EEE6",
            "ink": "#1C1917",
            "ink2": "#44403C",
            "muted": "#78716C",
            "accent": "#B45309",
            "positive": "#3F7D4E",
            "caution": "#C47B17",
            "risk": "#B42318",
            "hairline": "#E7E0D6",
            "dark_bg": "#1C1917",
            "dark_ink": "#FAFAF9",
            "dark_muted": "#A8A29E",
            "dark_accent": "#F59E0B",
            "dark_hairline": "#44403C",
        },
        "Ordered, restrained, scannable. Status, gap, owner, next step.",
        "Authoritative but operational",
        layout_scheme=LayoutScheme.STACK,
    ),
    RecipeId.CIVIC: _t(
        RecipeId.CIVIC,
        {
            "bg": "#F8F1E8",
            "surface": "#F1E4D4",
            "ink": "#2B1616",
            "ink2": "#5C3333",
            "muted": "#8A6A5A",
            "accent": "#8F1D22",
            "positive": "#3F6F4E",
            "caution": "#C9A227",
            "risk": "#8F1D22",
            "hairline": "#E2D2C0",
            "dark_bg": "#4A1418",
            "dark_ink": "#F8F1E8",
            "dark_muted": "#D4B8A0",
            "dark_accent": "#C9A227",
            "dark_hairline": "#6B2A2E",
        },
        "Ceremonial, grounded, contemporary community presence.",
        "Ritual but not a festival poster",
        image_behavior="photography_when_justified",
        layout_scheme=LayoutScheme.BANNER,
    ),
    RecipeId.ART_MARKET: _t(
        RecipeId.ART_MARKET,
        {
            "bg": "#F7F4EE",
            "surface": "#FFFFFF",
            "ink": "#111111",
            "ink2": "#3F3F3F",
            "muted": "#6F6F6F",
            "accent": "#FF3D00",
            "positive": "#0F766E",
            "caution": "#F5C518",
            "risk": "#111111",
            "hairline": "#111111",
            "dark_bg": "#111111",
            "dark_ink": "#F7F4EE",
            "dark_muted": "#C4C4C4",
            "dark_accent": "#FF3D00",
            "dark_hairline": "#3F3F3F",
        },
        "Vivid, curated, poster energy with recoverable order.",
        "Loud but structured",
        image_behavior="campaign_imagery",
        layout_scheme=LayoutScheme.BLOCKS,
    ),
    RecipeId.EDITORIAL: _t(
        RecipeId.EDITORIAL,
        {
            "bg": "#F5F3EE",
            "surface": "#EDEAE3",
            "ink": "#1A1A1A",
            "ink2": "#4A4A4A",
            "muted": "#7A7A7A",
            "accent": "#5C4033",
            "positive": "#3F6F4E",
            "caution": "#A16207",
            "risk": "#7F1D1D",
            "hairline": "#D9D4CA",
            "dark_bg": "#1A1A1A",
            "dark_ink": "#F5F3EE",
            "dark_muted": "#B0A89C",
            "dark_accent": "#C4B5A5",
            "dark_hairline": "#3A3A3A",
        },
        "Quiet, cultural, spatial. Image, type, and sequence as exhibition.",
        "Generous but precise",
        image_behavior="large_crop_photography",
        layout_scheme=LayoutScheme.SPREAD,
    ),
    RecipeId.HISTORY: _t(
        RecipeId.HISTORY,
        {
            "bg": "#F3E6D0",
            "surface": "#E8D5B5",
            "ink": "#1C140E",
            "ink2": "#4A3728",
            "muted": "#7A624C",
            "accent": "#3F6F6A",
            "positive": "#3F6F6A",
            "caution": "#A33B2B",
            "risk": "#A33B2B",
            "hairline": "#D7C4A4",
            "dark_bg": "#2A1C12",
            "dark_ink": "#F3E6D0",
            "dark_muted": "#C4A882",
            "dark_accent": "#C6A15B",
            "dark_hairline": "#4A3728",
        },
        "Scholarly, narrative, period-aware without costume-drama decoration.",
        "Historical atmosphere but classroom-clear",
        fonts=FontRoles(cn="PingFang SC", num="Arial", display="Songti SC"),
        image_behavior="maps_artifacts_no_fake_inscriptions",
        layout_scheme=LayoutScheme.SPINE,
    ),
    RecipeId.OPEN: _t(
        RecipeId.OPEN,
        {
            "bg": "#F6F7F9",
            "surface": "#ECEFF3",
            "ink": "#1F2933",
            "ink2": "#3E4C59",
            "muted": "#7B8794",
            "accent": "#326891",
            "positive": "#2F6F4E",
            "caution": "#C47B17",
            "risk": "#A61B1B",
            "hairline": "#D9E2EC",
            "dark_bg": "#102A43",
            "dark_ink": "#F0F4F8",
            "dark_muted": "#9FB3C8",
            "dark_accent": "#F0B429",
            "dark_hairline": "#243B53",
        },
        "Clear, composed, purpose-built. Invented when no recipe fully fits.",
        "Distinctive but not template-like",
        layout_scheme=LayoutScheme.SPREAD,
    ),
}

_ADJECTIVES = {
    RecipeId.CONSULTING: ["analytical", "compressed", "calm"],
    RecipeId.WORK_REPORT: ["ordered", "restrained", "scannable"],
    RecipeId.CIVIC: ["ceremonial", "grounded", "contemporary"],
    RecipeId.ART_MARKET: ["vivid", "playful", "curated"],
    RecipeId.EDITORIAL: ["quiet", "cultural", "spatial"],
    RecipeId.HISTORY: ["scholarly", "narrative", "period-aware"],
    RecipeId.OPEN: ["clear", "composed", "purpose-built"],
}

_LABELS = {
    RecipeId.CONSULTING: "Consulting — decision file",
    RecipeId.WORK_REPORT: "Work report — operating status",
    RecipeId.CIVIC: "Civic — ceremonial community",
    RecipeId.ART_MARKET: "Art market — poster campaign",
    RecipeId.EDITORIAL: "Editorial — gallery / magazine",
    RecipeId.HISTORY: "History — chronology / classroom",
    RecipeId.OPEN: "Open brief — purpose-built",
}

_RHYTHM = {
    RecipeId.CONSULTING: (
        "Title, pause, hairline columns of assertions; implication hugs the folio."
    ),
    RecipeId.WORK_REPORT: (
        "Stacked operational bands (status, owner, next), not a newspaper cross."
    ),
    RecipeId.CIVIC: (
        "Ceremonial full-width banners and a stamp number; photography when justified."
    ),
    RecipeId.ART_MARKET: "Gapped poster blocks, one loud fill; no shared hairline cross.",
    RecipeId.EDITORIAL: (
        "Asymmetric columns with a wide gutter; type and crop, not a plus-sign grid."
    ),
    RecipeId.HISTORY: "A vertical spine of episodes; chronology, not a 2×2 cross.",
    RecipeId.OPEN: (
        "Purpose-built columns with a pause under the title; invent only what the brief needs."
    ),
}
