import re
from pathlib import Path

from ppt_expert.models import RecipeId
from ppt_expert.recipes import tokens_for

_COMPOSE = [
    Path("src/ppt_expert/pptx/slides.py"),
    Path("src/ppt_expert/pptx/primitives.py"),
    Path("src/ppt_expert/pptx/renderer.py"),
]
_ALLOWED = {"#FFFFFF", "#000000"}


def test_compose_layer_has_no_recipe_hex_literals() -> None:
    blob = "\n".join(path.read_text(encoding="utf-8") for path in _COMPOSE)
    found = {item.upper() for item in re.findall(r"#[0-9A-Fa-f]{6}", blob)}
    assert found <= _ALLOWED


def test_consulting_tokens_expose_role_names() -> None:
    colors = tokens_for(RecipeId.CONSULTING).colors
    assert colors.bg == "#F7F8FA"
    assert colors.accent == "#1F4E79"
    assert colors.dark_bg == "#12263A"
