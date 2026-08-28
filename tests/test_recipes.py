from ppt_expert.models import IntentSlots, RecipeId
from ppt_expert.recipes import FOUNDATIONS, match_recipe, tokens_for


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
