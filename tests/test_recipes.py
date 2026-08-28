from ppt_expert.models import IntentSlots, LayoutScheme, RecipeId
from ppt_expert.recipes import FOUNDATIONS, match_recipe, recipe_choices, tokens_for


def test_recipe_keywords_select_consulting_civic_and_history() -> None:
    assert match_recipe("写一份A股策略研报", IntentSlots(topic="策略", audience="CIO", objective="配置")) == RecipeId.CONSULTING
    assert match_recipe("社区党建活动方案", IntentSlots(topic="党建", audience="居民", objective="动员")) == RecipeId.CIVIC
    assert match_recipe("明清海禁历史教学", IntentSlots(topic="历史", audience="学生", objective="理解因果")) == RecipeId.HISTORY


def test_foundations_and_role_named_tokens() -> None:
    assert len(FOUNDATIONS) == 5
    tokens = tokens_for(RecipeId.CONSULTING)
    names = set(tokens.colors.model_dump())
    assert {"bg", "surface", "ink", "ink2", "muted", "accent", "positive", "caution", "risk", "hairline"} <= names
    assert tokens.page.w == 13.333
    assert tokens.page.h == 7.5


def test_unmatched_request_uses_open_recipe() -> None:
    assert match_recipe("birthday invitation", IntentSlots(topic="party", audience="friends", objective="rsvp")) == RecipeId.OPEN


def test_recipe_choices_put_the_match_first_as_recommended() -> None:
    options = recipe_choices(RecipeId.CONSULTING)
    assert options[0]["id"] == "consulting"
    assert options[0]["recommended"] is True
    assert {item["id"] for item in options} == {item.value for item in RecipeId}
    assert sum(1 for item in options if item["recommended"]) == 1


def test_each_recipe_has_its_own_body_layout() -> None:
    schemes = {recipe: tokens_for(recipe).layout_scheme for recipe in RecipeId}
    assert schemes[RecipeId.CONSULTING] == LayoutScheme.RULES
    assert schemes[RecipeId.WORK_REPORT] == LayoutScheme.STACK
    assert schemes[RecipeId.CIVIC] == LayoutScheme.BANNER
    assert schemes[RecipeId.ART_MARKET] == LayoutScheme.BLOCKS
    assert schemes[RecipeId.EDITORIAL] == LayoutScheme.SPREAD
    assert schemes[RecipeId.HISTORY] == LayoutScheme.SPINE
    assert schemes[RecipeId.OPEN] == LayoutScheme.SPREAD
    assert len(set(schemes.values())) >= 5
