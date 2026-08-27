# PPT 制作 Agent 大纲（含工具实现方式）

> 用途：将「从提纲到成品 PPT」的全流程固化为一个可复用的 Agent，保留原始工具链并阐明每个工具的跨平台实现方式。
> 来源：2026-08-26 实战项目《致敬最美幼教人张诗瑶老师》16 页全稿验证通过。
> 修订：2026-08-27 补充每个工具的接口契约 + 跨平台实现方案。

---

## 一、Agent 角色定位

你是一个专业 PPT 制作 Agent，负责从用户的主题/提纲出发，产出一份排版精良、图文并茂的 `.pptx` 演示文稿，并实时同步预览。

**核心原则**
- 忠于用户提纲：页数、标题、核心内容不擅自增删，只做润色
- 先图后文：插画先行，文字围绕图片排版
- 每一步可校验：写完即校验，不留错误到最后
- 交付即预览：文件生成后立即推送给用户

---

## 二、工作流程（六步）

### 第 1 步：接收提纲，创建任务清单

1. 解析用户提纲，统计总页数、分部结构（如：引言/事迹/升华）
2. 创建 TaskList，任务粒度：
   - 确认视觉风格
   - 撰写叙事与设计文档
   - 创建演示文稿并打开预览
   - 逐页制作
   - 校验修复并交付

---

### 第 2 步：风格选型（需用户确认）

**流程**：出 4 张风格预览卡 → 用户选 A/B/C/D → 锁定色板

原始实现用两个工具配合：

#### 工具 1：`read_me(modules: ["mockup"])`

**是什么**：内部上下文加载器，为可视化渲染准备设计规范（CSS 变量、配色、字体、间距、圆角等）。

**接口契约**：
```
输入: modules: string[]  — 可选值: "diagram" | "mockup" | "interactive" | "chart" | "art"
输出: 该模块的设计规范上下文（CSS 变量、色板、字号、间距、圆角等）
副作用: 无（纯读取，注入到 Agent 上下文）
调用时机: 在 show_widget 之前调用一次
```

**跨平台实现方式**：

这本质上就是一个**设计令牌加载器**，不需要任何运行时魔法。

```json
// mockup_tokens.json — 你自己写一份常量配置
{
  "mockup": {
    "colors": {
      "primary": "#E8603C",
      "secondary": "#F5C24B",
      "bg": "#FFF8F0",
      "text": "#3D2B1F",
      "muted": "#C4A484"
    },
    "typography": {
      "title": { "fontFamily": "Songti SC, serif", "fontSize": "28px", "fontWeight": "700" },
      "body": { "fontFamily": "PingFang SC, sans-serif", "fontSize": "16px", "fontWeight": "400" }
    },
    "spacing": { "padding": "24px", "gap": "16px", "margin": "12px" },
    "radius": { "card": "12px", "button": "8px" },
    "shadow": "0 4px 12px rgba(0,0,0,0.08)"
  }
}
```

**实现方式（按平台选）**：
- **有文件系统**：读 JSON 文件，注入到 Agent 上下文
- **纯 LLM Agent**：直接在 system prompt 里写死这些 token 常量
- **有后端服务**：提供 `GET /design-tokens?module=mockup` 接口，返回 JSON
- **最低成本方案**：砍掉这步，把 token 直接硬编码到 DESIGN.md 中——本来就该是文档说了算

#### 工具 2：`show_widget(title, widget_code, loading_messages)`

**是什么**：在对话中内联渲染一块可视内容（SVG 或 HTML），用户直接在聊天里看到图。

**接口契约**：
```
输入:
  title: string           — 可视内容标题（也用作下载文件名）
  widget_code: string     — SVG 或 HTML 片段（不含 <html>/<head>/<body>/<DOCTYPE>；SVG 用 viewBox="0 0 680 ..." 开头）
  loading_messages: string[] — 渲染时的 loading 提示（1-4 条，每条约 5 词）
输出: 用户在对话中看到渲染后的图
副作用: 在聊天界面中渲染视觉内容
调用时机: read_me 之后
```

**跨平台实现方式**：

核心需求：**把一段 SVG/HTML 可视内容送到用户眼前**。按你的平台能力选：

| 平台能力 | 实现方式 | 代码示例 |
|---------|---------|---------|
| **支持富文本/HTML 渲染**（Web 聊天、Slack、飞书等） | 直接把 SVG/HTML 作为富文本消息发送 | Slack: 用 Block Kit 的 `image` 或 `section`；飞书: 用 interactive card |
| **只支持图片**（微信、QQ、钉钉等） | SVG → PNG 转换后发送 | `cairosvg svg_str → png_bytes` 或 `subprocess: rsvg-convert -w 800 input.svg -o output.png` |
| **只支持文件** | 存为 .svg/.html 文件，发下载链接 | `with open("preview.svg","w") as f: f.write(svg_code)` → 发文件 |
| **只支持文字** | 降级为纯文本描述 | 文字描述 4 套方案，让用户回 A/B/C/D |
| **有浏览器内核** | HTML → 截图 → 发图片 | Playwright/PuppetShot: `page.set_content(html)` → `page.screenshot()` |

**SVG → PNG 最小实现（Python）**：
```python
import cairosvg
png_bytes = cairosvg.svg2png(url="preview.svg", output_width=800, output_height=600)
# 或用命令行: rsvg-convert -w 800 preview.svg -o preview.png
```

**HTML → 截图最小实现（Node.js）**：
```javascript
const { chromium } = require('playwright');
const browser = await chromium.launch();
const page = await browser.newPage();
await page.setViewportSize({ width: 680, height: 400 });
await page.setContent(htmlCode);
await page.screenshot({ path: 'preview.png' });
await browser.close();
```

> **总结**：`read_me` + `show_widget` 本质 = **加载设计常量 + 把 SVG/HTML 渲染给用户看**。前者可以用硬编码替代，后者按平台选最合适的渲染通道。

---

### 第 3 步：撰写底稿文档

在项目目录写两份文档：

**STORY.md — 叙事契约**
```
每页一条记录，包含：
- 页码
- 标题
- 核心内容（忠于用户提纲，仅做润色）
- 配图指向（哪张图放在这一页）
- 版式类型（Hero 满版图 / 左图右文 / 上图下文 / 纯文字 / 数据卡片）
```

**DESIGN.md — 视觉硬约束**
```
- 色板：主色 / 辅色 / 正文色 / 底色 / 强调色（全部 hex 值）
- 字体：标题字体族 + 正文字体族（标注备选链：首选 → 降级 → 系统默认）
- 字号：大标题 / 小标题 / 正文 / 注释（pt 值）
- 版式规范：Hero 页与内容页比例、非对称原则、留白比例
- 配图规范：画风、色调、人物处理（背影/侧影）、禁止元素
```

**实现**：用文件写入能力（`Write` / `open().write()` / `fs.writeFileSync`）。无文件系统则存 Agent 内部变量。

---

### 第 4 步：创建文稿与实时预览

#### 工具 3：`slidep-start --project <path> --filename <name>.pptx`

**是什么**：创建 `.pptx` 文件 + 启动实时编译服务（监听 slide 文件变化，自动重编译并推送预览）。

**接口契约**：
```
输入:
  --project: string    — 项目根目录绝对路径
  --filename: string   — 输出的 .pptx 文件名
输出:
  1. 创建空的 .pptx 文件
  2. 启动一个监听服务（watch slides/ 目录，文件变化时自动重编译）
  3. 返回预览地址（供 present_files 打开）
副作用: 文件系统写入 + 后台服务启动
```

**跨平台实现方式**：

拆成两个独立能力：**创建 PPT 文件** + **实时预览**。

**① 创建 PPT 文件**

| 方案 | 工具/库 | 代码示例 |
|------|---------|---------|
| **python-pptx**（推荐） | `pip install python-pptx` | 见下方 |
| HTML → PPTX | 先写 HTML，LibreOffice 转 | `libreoffice --headless --convert-to pptx input.html` |
| 商业 API | iSlide / Aspose Slides | REST API 调用 |
| 纯 HTML 幻灯片 | reveal.js / impress.js | 输出 HTML，浏览器放映 |

**python-pptx 最小实现**：
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu

prs = Presentation()
prs.slide_width = Inches(13.333)  # 16:9 宽屏
prs.slide_height = Inches(7.5)

# 添加空白页
blank_layout = prs.slide_layouts[6]  # 空白版式
slide = prs.slides.add_slide(blank_layout)

prs.save("输出.pptx")
```

**② 实时预览（可选，nice-to-have）**

实时预览不是必须的，但能大幅提升体验。实现方式：

```python
# 方案 A：文件监听 + 自动重建（Python watchdog）
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SlideHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.slide') or event.src_path.endswith('.py'):
            rebuild_pptx()  # 重新编译

observer = Observer()
observer.schedule(SlideHandler(), path="./slides", recursive=True)
observer.start()
# 主线程阻塞，子线程监听文件变化
```

```javascript
// 方案 B：WebSocket 推送预览（Node.js）
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: 8080 });
const chokidar = require('chokidar');
chokidar.watch('./slides/').on('change', () => {
  rebuildPptx(); // 重建
  wss.clients.forEach(client => client.send('reload')); // 通知前端刷新
});
```

```bash
# 方案 C：最简方案——用 entr 或 fswatch 命令行工具
ls slides/*.slide | entr -r python build_pptx.py
```

> **总结**：`slidep-start` = **python-pptx 创建文件** + **文件监听自动重建**。前者是核心，后者是锦上添花。最低实现只需 `prs.save()`。

---

### 第 5 步：AI 生图（先图后文）

#### 工具 4：`ImageGen`

**是什么**：文本生成图片的 AI 工具，根据提示词产出 PNG 文件。

**接口契约**：
```
输入:
  prompt: string        — 生图提示词
  size: string          — 图片尺寸，如 "1536x1024"（横版）/ "1024x1024"（方版）
  quality: string       — "high" | "standard"
  background: string    — "opaque" | "transparent"
  output_dir: string    — 输出目录路径
  style: string         — 画风描述（可选）
输出: PNG 文件保存到 output_dir
副作用: 文件系统写入
```

**跨平台实现方式**：

按可用的 API 选一个，接口模式统一：**prompt → API 调用 → 图片字节/base64 → 存文件**。

**方案 A：DALL-E 3（OpenAI）**
```python
from openai import OpenAI
client = OpenAI(api_key="sk-...")

response = client.images.generate(
    model="dall-e-3",
    prompt="温暖扁平插画：幼儿园门口...",
    size="1792x1024",  # 横版
    quality="hd",
    n=1,
)
image_url = response.data[0].url
# 下载 URL 存为本地文件
import requests
img_data = requests.get(image_url).content
with open("assets/cover_hero.png", "wb") as f:
    f.write(img_data)
```

**方案 B：Stable Diffusion WebUI（自部署）**
```python
import requests, base64

response = requests.post("http://localhost:7860/sdapi/v1/txt2img", json={
    "prompt": "warm flat illustration, kindergarten entrance...",
    "negative_prompt": "text, watermark, signature, face details",
    "width": 1536,
    "height": 1024,
    "steps": 30,
    "sampler_name": "DPM++ 2M Karras",
})
image_b64 = response.json()["images"][0]
with open("assets/cover_hero.png", "wb") as f:
    f.write(base64.b64decode(image_b64))
```

**方案 C：通义万相（阿里云）**
```python
import dashscope
dashscope.api_key = "sk-..."

response = dashscope.ImageSynthesis.call(
    model="wanx-v1",
    prompt="温暖扁平插画：幼儿园门口...",
    n=1,
    size="1536*1024",
)
image_url = response.output.results[0].url
# 下载存本地
```

**方案 D：Midjourney（第三方 API 代理）**
```python
# 通过 goapi 或 similar 代理
response = requests.post("https://api.midjourney.com/imagine", json={
    "prompt": "warm flat illustration... --ar 3:2",
    "callback_url": "https://your-server.com/callback",
})
# 异步等待回调，拿到图片 URL 后下载
```

**提示词模板**（与 API 无关，通用）：
```
[画风] + [色调] + [场景描述] + [人物处理] + [禁止元素]
```
要点：
- 明确画风（如"温暖扁平插画"）
- 明确色调（与 DESIGN.md 色板一致）
- **人物一律背影/侧影，不出现清晰五官**
- 结尾必加："画面中不出现任何文字与水印"

> **总结**：`ImageGen` = **调一个文生图 API + 存文件**。接口统一，换 API 只改调用代码，提示词不变。

---

### 第 6 步：逐页制作与校验交付

#### 6.1 逐页制作
按 STORY.md 契约逐页写内容，注入到 PPT 引擎中。

**python-pptx 逐页制作示例**：
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# === 封面页 (Hero) ===
slide = prs.slides.add_slide(prs.slide_layouts[6])  # 空白版式
# 满版背景图
slide.shapes.add_picture("assets/cover_hero.png", 0, 0, prs.slide_width, prs.slide_height)
# 渐变蒙版（半透明矩形覆盖底部，保证文字可读）
from pptx.util import Emu
overlay = slide.shapes.add_shape(1, Inches(0), Inches(4.5), prs.slide_width, Inches(3))
overlay.fill.solid()
overlay.fill.fore_color.rgb = RGBColor(0xE8, 0x60, 0x3C)  # 主色
overlay.fill.fore_color.brightness = -0.3  # 调暗
# 标题
txBox = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(11), Inches(1.5))
tf = txBox.text_frame
tf.text = "以热血赴温柔，以初心育童心"
tf.paragraphs[0].font.size = Pt(44)
tf.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].alignment = PP_ALIGN.CENTER

# === 内容页 (左图右文) ===
slide2 = prs.slides.add_slide(prs.slide_layouts[6])
slide2.shapes.add_picture("assets/teacher_kids.png", Inches(0), Inches(0), Inches(7), Inches(7.5))
# 右侧文字区
txBox2 = slide2.shapes.add_textbox(Inches(7.5), Inches(1), Inches(5), Inches(5.5))
# ...

prs.save("致敬最美幼教人张诗瑶老师.pptx")
```

#### 工具 5：`slidep-validate --all --project .`

**是什么**：校验所有 slide 文件的语法与结构正确性。

**接口契约**：
```
输入:
  --all: flag           — 校验全部页
  --project: string     — 项目路径
输出: 每页 pass/fail + 错误信息
副作用: 无（只读校验）
```

**跨平台实现方式**：

这本质上就是一个 **lint/校验脚本**，需要检查什么取决于你的 PPT 引擎。

**python-pptx 校验脚本示例**：
```python
import os
from pptx import Presentation
from pptx.util import Emu

def validate_pptx(pptx_path, assets_dir):
    errors = []
    prs = Presentation(pptx_path)

    # 检查 1: 总页数
    expected_pages = 16
    actual_pages = len(prs.slides)
    if actual_pages != expected_pages:
        errors.append(f"页数不符: 预期 {expected_pages}, 实际 {actual_pages}")

    for i, slide in enumerate(prs.slides):
        # 检查 2: 图片路径存在
        for shape in slide.shapes:
            if shape.shape_type == 13:  # PICTURE
                img_path = shape.image.filename or ""
                if img_path and not os.path.exists(img_path):
                    errors.append(f"第{i+1}页: 图片不存在 {img_path}")

        # 检查 3: 文字未溢出（简单版）
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text
                    if len(text) > 200:
                        errors.append(f"第{i+1}页: 文本过长({len(text)}字符)，可能溢出")

    # 检查 4: 色值合规（抽检文本颜色是否在 DESIGN.md 色板内）
    # ...

    return errors

errors = validate_pptx("输出.pptx", "assets/")
if errors:
    for e in errors:
        print(f"❌ {e}")
else:
    print("✅ 全部通过")
```

**通用校验检查清单**：
- [ ] 总页数与提纲一致
- [ ] 每页标题与提纲一致
- [ ] 每页核心内容完整
- [ ] 图片文件存在且路径正确
- [ ] 字体在目标系统可用
- [ ] 色板与 DESIGN.md 一致（无越界色值）
- [ ] 文字未溢出版面
- [ ] 图片无意外水印

#### 工具 6：`present_files(files)`

**是什么**：将文件展示给用户，在面板中打开预览。

**接口契约**：
```
输入:
  files: string[]       — 文件路径或 URL 数组
  cwd: string           — 工作目录（可选）
  explanation: string    — 交付说明（可选）
输出: 用户在界面中看到文件预览
副作用: 在用户界面打开文件
```

**跨平台实现方式**：

核心需求：**把成品文件送到用户手里**。

| 平台能力 | 实现方式 | 代码示例 |
|---------|---------|---------|
| **聊天文件附件** | 作为附件发送 | Slack: `files.upload`；飞书: `im/v1/files`；微信: 发送文件消息 |
| **云存储** | 上传到 S3/OSS，返回下载链接 | `boto3.client('s3').upload_file(...)` → 返回 URL |
| **本地路径** | 告知用户文件路径 | `print(f"文件已保存: {os.path.abspath(path)}")` |
| **邮件** | 作为附件发邮件 | SMTP `MIMEMultipart` + 附件 |
| **Web 下载** | 启动临时文件服务 | `python -m http.server 8080` → 提供下载链接 |

**通用实现（Python）**：
```python
import shutil, os

def deliver_file(file_path, platform="local"):
    if platform == "local":
        abs_path = os.path.abspath(file_path)
        print(f"📁 文件已就绪: {abs_path}")
        return abs_path
    elif platform == "s3":
        import boto3
        s3 = boto3.client('s3')
        key = os.path.basename(file_path)
        s3.upload_file(file_path, "my-bucket", key)
        url = f"https://my-bucket.s3.amazonaws.com/{key}"
        print(f"🔗 下载链接: {url}")
        return url
    elif platform == "chat":
        # 调用平台 SDK 发送文件
        send_file_to_chat(file_path)
        return "sent"
```

> **总结**：`present_files` = **把文件推送给用户**。按你的渠道选：发附件 / 上传云存储给链接 / 告知本地路径。

---

## 三、版式设计要点

- **Hero 视觉高潮页**：约占 1/4（16 页配 4 个），分布在开头、中段高潮、结尾，均匀不挤堆
- **非对称版式为主**：图占 55–60%，文占 40–45%，错位排布；仅致谢等仪式页用纯对称
- **节奏**：Hero 页（满版图+大标题）与内容页（分栏信息）交替
- **色彩一致性**：所有页只使用 DESIGN.md 中锁定的色板，插图色调与页面底色同族

---

## 四、工具实现总览表

| 工具 | 本质 | 最低实现 | 推荐实现 |
|------|------|---------|---------|
| `read_me` | 设计令牌加载 | 硬编码 JSON 常量 | 独立 JSON 配置文件 + 加载函数 |
| `show_widget` | SVG/HTML 内联渲染 | 转成文字描述 | SVG→PNG 转换 + 发图片 |
| `slidep-start` | 创建 PPT + 文件监听 | `python-pptx` 的 `prs.save()` | python-pptx + watchdog 自动重建 |
| `ImageGen` | 文生图 API | 任意一个文生图 API | DALL-E 3 或 Stable Diffusion |
| `slidep-validate` | lint 校验脚本 | 逐页检查清单 | Python 校验脚本（自动） |
| `present_files` | 文件推送 | 告知本地路径 | 上传云存储 + 返回下载链接 |

---

## 五、踩坑经验（实战沉淀）

| # | 经验 | 通用/专属 |
|---|------|----------|
| 1 | 图片路径用绝对路径，不用相对路径 | 通用（所有引擎） |
| 2 | JSX/模板属性里不能用数组下标 `[...][idx]`，改用对象字段名 | 专属（JSX 引擎） |
| 3 | 图标名要在图标库元数据内（如 `sunset` 不存在 → 换 `cloud-sun`） | 专属（图标库） |
| 4 | 中文字体先查系统是否安装（`fc-list`），选 Songti SC / PingFang SC 等通用字体 | 通用 |
| 5 | AI 生图水印：靠页面渐变蒙版淡化，或提示词追加禁止词 | 通用 |
| 6 | 校验工具输出噪音多，过滤堆栈行只看结果 | 通用 |
| 7 | 副标题用主色的浅色变体（降低饱和度），不要引入新色 | 通用（设计） |
| 8 | 大段正文分行用显式 `\n`，不靠自动换行（跨引擎兼容） | 通用 |

---

## 六、Agent 系统提示词草稿

以下可直接作为 Agent 的 System Prompt：

```
你是一个专业 PPT 制作助手。接收用户的主题和提纲后，按以下流程执行：

1. 解析提纲，统计页数与结构，建立任务清单
2. 准备 4 套视觉风格方案（色板+气质描述），渲染预览卡让用户选择
   - 渲染方式：生成 SVG 预览卡 → 转为 PNG → 发送给用户
   - 若无法发图：降级为文字描述，让用户回 A/B/C/D
3. 用户选定后，撰写 STORY.md（逐页叙事契约）和 DESIGN.md（视觉硬约束）
4. 用 python-pptx 创建空 PPT 文件
5. 按设计文档生成配图（6-8 张统一风格插画，调文生图 API）
   - 提示词必含：画风+色调+场景+背影人物+"不出现文字水印"
6. 逐页制作 PPT 内容，用 python-pptx 写入每页
   - 版式非对称为主，Hero 高潮页均匀分布
7. 运行校验脚本，确认全部通过
8. 将 .pptx 文件发送给用户

规则：
- 提纲页数、标题、核心内容不擅自增删，只润色
- 先图后文，图片先行
- 色板一旦锁定不越界
- 字体选系统通用字体并设降级链
- 图片路径用绝对路径
```
