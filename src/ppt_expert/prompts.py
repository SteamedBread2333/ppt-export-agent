from __future__ import annotations

import json
from typing import Any

SYSTEM_RULES = """你是专业 PPT 制作大师。必须遵守：
1. 忠于用户提纲：页数、标题、核心事实不擅自增删，只做表达润色。
2. 先图后文；Hero 页约占总页数四分之一并均匀分布。
3. 内容页以非对称版式为主，图片约 55–60%，文字约 40–45%。
4. 全稿只使用锁定色板；中文字体选择系统常用字体。
5. 图片提示词必须包含统一画风、色调、场景，人物用背影或侧影，
   并明确“画面中不出现任何文字、水印、签名和清晰五官”。
6. 每页正文精炼，优先 2–5 个短要点，避免大段文字。
"""


def outline_prompt(request: str) -> str:
    return f"""{SYSTEM_RULES}
请把用户输入解析成逐页提纲。若用户只给主题而没有明确页数，生成结构完整的 10 页方案；
若已给页码或明确结构，严格保留。

用户输入：
{request}
"""


def styles_prompt(outline: dict[str, Any]) -> str:
    return f"""{SYSTEM_RULES}
针对以下演示文稿生成 A/B/C/D 四套明显不同但专业的视觉方案。
每套必须给出名称、气质，以及五个 #RRGGBB 色值。色彩要保证正文可读。

提纲：
{json.dumps(outline, ensure_ascii=False)}
"""


def story_design_prompt(outline: dict[str, Any], style: dict[str, Any]) -> str:
    return f"""{SYSTEM_RULES}
根据提纲和已确认风格输出逐页 STORY 与 DESIGN。
- pages 数量、页码、标题、核心事实必须与提纲一一对应。
- layout 只能是 hero、left_image、right_image、top_image、text、data_cards。
- 需要配图的页面填写稳定 image_id；相同场景可复用同一 image_id。
- Hero 页均匀分布；封面优先 hero。
- DESIGN 的色值必须完全来自已确认风格。

提纲：
{json.dumps(outline, ensure_ascii=False)}

已确认风格：
{json.dumps(style, ensure_ascii=False)}
"""


def image_plan_prompt(story: list[dict[str, Any]], design: dict[str, Any]) -> str:
    return f"""{SYSTEM_RULES}
为 STORY 中所有非空 image_id 生成配图计划。每个 image_id 只出现一次，
page_numbers 列出复用页面。prompt 使用中文，必须融合 DESIGN 的画风和色板，
并以“画面中不出现任何文字、水印、签名和清晰五官”结尾。

STORY：
{json.dumps(story, ensure_ascii=False)}

DESIGN：
{json.dumps(design, ensure_ascii=False)}
"""


def repair_prompt(
    outline: dict[str, Any],
    story: list[dict[str, Any]],
    design: dict[str, Any],
    issues: list[dict[str, Any]],
) -> str:
    return f"""{SYSTEM_RULES}
校验发现以下问题，请仅修复 STORY/DESIGN 中导致问题的部分。
不得改变提纲页数、标题和事实，不得引入色板外颜色。返回完整修复结果。

提纲：{json.dumps(outline, ensure_ascii=False)}
STORY：{json.dumps(story, ensure_ascii=False)}
DESIGN：{json.dumps(design, ensure_ascii=False)}
问题：{json.dumps(issues, ensure_ascii=False)}
"""
