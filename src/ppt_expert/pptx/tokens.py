"""Role-named design tokens. Palette literals live in recipes; compose code uses names."""

from ppt_expert.models import ColorRoles, DesignTokens, FontRoles, PageMetrics, RecipeId
from ppt_expert.recipes import tokens_for

PAGE = PageMetrics()
F = FontRoles()
C_ROLES = tuple(ColorRoles.model_fields)
DARK_ROLES = ("dark_bg", "dark_ink", "dark_muted", "dark_accent", "dark_hairline")

__all__ = ["C_ROLES", "DARK_ROLES", "PAGE", "DesignTokens", "F", "RecipeId", "tokens_for"]
