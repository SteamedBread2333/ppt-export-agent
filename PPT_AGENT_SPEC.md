# PowerPoint Production Agent Specification (Including Tool Implementations)

> Purpose: Standardize the complete workflow from outline to finished PowerPoint as a reusable agent, preserving the original toolchain while explaining how to implement each tool across platforms.
> Source: Validated through the 16-slide production project *A Tribute to Zhang Shiyao, an Outstanding Early-Childhood Educator* on 2026-08-26.
> Revision: Added interface contracts and cross-platform implementation options for every tool on 2026-08-27.

---

## 1. Agent Role

You are a professional PowerPoint production agent. Starting from a user-provided topic or outline, you create a polished, visually rich `.pptx` presentation and synchronize its preview in real time.

**Core principles**
- Stay faithful to the user's outline: do not add or remove slides, titles, or key content; only refine the wording.
- Visuals before text: create illustrations first, then arrange text around them.
- Validate every step: validate immediately after writing instead of deferring errors until the end.
- Preview on delivery: push the generated file to the user immediately.

---

## 2. Workflow (Six Steps)

### Step 1: Receive the Outline and Create a Task List

1. Parse the user's outline and determine the total slide count and section structure (for example, introduction / achievements / culmination).
2. Create a TaskList with tasks at the following level of granularity:
   - Confirm the visual style.
   - Write the narrative and design documents.
   - Create the presentation and open a preview.
   - Produce each slide.
   - Validate, fix, and deliver.

---

### Step 2: Select a Style (User Confirmation Required)

**Process**: Produce four style preview cards -> user selects A/B/C/D -> lock the color palette.

The original implementation combines two tools:

#### Tool 1: `read_me(modules: ["mockup"])`

**What it is**: An internal context loader that prepares design specifications for visual rendering, including CSS variables, colors, typography, spacing, and corner radii.

**Interface contract**:
```
Input: modules: string[]  — Allowed values: "diagram" | "mockup" | "interactive" | "chart" | "art"
Output: Design-specification context for the module (CSS variables, palette, font sizes, spacing, corner radii, and so on)
Side effects: None (read-only; injects data into the agent context)
When to call: Once before show_widget
```

**Cross-platform implementation**:

This is essentially a **design-token loader** and requires no runtime magic.

```json
// mockup_tokens.json — a constant configuration maintained by your team
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

**Implementation options by platform**:
- **File system available**: Read a JSON file and inject it into the agent context.
- **LLM-only agent**: Define these token constants directly in the system prompt.
- **Backend service available**: Expose a `GET /design-tokens?module=mockup` endpoint that returns JSON.
- **Lowest-cost option**: Remove this step and hard-code the tokens in DESIGN.md; the document should be the source of truth anyway.

#### Tool 2: `show_widget(title, widget_code, loading_messages)`

**What it is**: Renders visual content (SVG or HTML) inline in the conversation so the user can view it directly in chat.

**Interface contract**:
```
Input:
  title: string           — Visual-content title (also used as the download filename)
  widget_code: string     — SVG or HTML fragment (without <html>/<head>/<body>/<DOCTYPE>; SVG begins with viewBox="0 0 680 ...")
  loading_messages: string[] — Loading messages shown during rendering (1–4 messages, approximately 5 words each)
Output: The user sees the rendered visual in the conversation
Side effects: Renders visual content in the chat interface
When to call: After read_me
```

**Cross-platform implementation**:

The core requirement is to **present SVG/HTML visual content to the user**. Choose an approach based on the platform's capabilities:

| Platform Capability | Implementation | Code Example |
|---------|---------|---------|
| **Rich text/HTML rendering** (web chat, Slack, Lark, and similar platforms) | Send SVG/HTML directly as a rich-text message | Slack: use a Block Kit `image` or `section`; Lark: use an interactive card |
| **Images only** (WeChat, QQ, DingTalk, and similar platforms) | Convert SVG to PNG, then send it | `cairosvg svg_str → png_bytes` or `subprocess: rsvg-convert -w 800 input.svg -o output.png` |
| **Files only** | Save as an .svg/.html file and send a download link | `with open("preview.svg","w") as f: f.write(svg_code)` -> send the file |
| **Text only** | Fall back to a plain-text description | Describe four options and ask the user to reply with A/B/C/D |
| **Browser engine available** | Convert HTML to a screenshot and send the image | Playwright/PuppetShot: `page.set_content(html)` -> `page.screenshot()` |

**Minimal SVG-to-PNG implementation (Python)**:
```python
import cairosvg
png_bytes = cairosvg.svg2png(url="preview.svg", output_width=800, output_height=600)
# Alternatively, use the CLI: rsvg-convert -w 800 preview.svg -o preview.png
```

**Minimal HTML-to-screenshot implementation (Node.js)**:
```javascript
const { chromium } = require('playwright');
const browser = await chromium.launch();
const page = await browser.newPage();
await page.setViewportSize({ width: 680, height: 400 });
await page.setContent(htmlCode);
await page.screenshot({ path: 'preview.png' });
await browser.close();
```

> **Summary**: `read_me` + `show_widget` essentially means **load design constants + render SVG/HTML for the user**. Hard-coded values can replace the former; implement the latter through the rendering channel best suited to the platform.

---

### Step 3: Write the Source Documents

Write two documents in the project directory:

**STORY.md — Narrative contract**
```
One record per slide, containing:
- Slide number
- Title
- Key content (faithful to the user's outline, with wording refinements only)
- Image assignment (which image appears on this slide)
- Layout type (full-bleed hero / image left, text right / image above, text below / text only / data cards)
```

**DESIGN.md — Strict visual constraints**
```
- Palette: primary / secondary / body-text / background / accent colors (all as hex values)
- Typography: title font family + body font family (include fallback chains: preferred -> fallback -> system default)
- Font sizes: main title / subtitle / body / annotation (in pt)
- Layout rules: ratio of hero slides to content slides, asymmetry principles, and whitespace ratio
- Image rules: illustration style, color tone, treatment of people (rear view/profile), and prohibited elements
```

**Implementation**: Use file-writing capabilities (`Write` / `open().write()` / `fs.writeFileSync`). If no file system is available, store the documents in internal agent variables.

---

### Step 4: Create the Presentation and Enable Live Preview

#### Tool 3: `slidep-start --project <path> --filename <name>.pptx`

**What it is**: Creates a `.pptx` file and starts a live compilation service that monitors slide-file changes, recompiles automatically, and pushes preview updates.

**Interface contract**:
```
Input:
  --project: string    — Absolute path to the project root
  --filename: string   — Output .pptx filename
Output:
  1. Creates an empty .pptx file
  2. Starts a watcher service (monitors the slides/ directory and recompiles automatically when files change)
  3. Returns a preview URL (for present_files to open)
Side effects: Writes to the file system and starts a background service
```

**Cross-platform implementation**:

Split this into two independent capabilities: **create the PowerPoint file** + **provide a live preview**.

**1. Create the PowerPoint file**

| Option | Tool/Library | Code Example |
|------|---------|---------|
| **python-pptx** (recommended) | `pip install python-pptx` | See below |
| HTML -> PPTX | Write HTML first, then convert it with LibreOffice | `libreoffice --headless --convert-to pptx input.html` |
| Commercial API | iSlide / Aspose Slides | REST API call |
| HTML-only slides | reveal.js / impress.js | Output HTML and present it in a browser |

**Minimal python-pptx implementation**:
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu

prs = Presentation()
prs.slide_width = Inches(13.333)  # 16:9 widescreen
prs.slide_height = Inches(7.5)

# Add a blank slide
blank_layout = prs.slide_layouts[6]  # Blank layout
slide = prs.slides.add_slide(blank_layout)

prs.save("output.pptx")
```

**2. Live preview (optional, nice to have)**

A live preview is not required, but it significantly improves the experience. Implementation options:

```python
# Option A: File watching + automatic rebuild (Python watchdog)
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SlideHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.slide') or event.src_path.endswith('.py'):
            rebuild_pptx()  # Recompile

observer = Observer()
observer.schedule(SlideHandler(), path="./slides", recursive=True)
observer.start()
# Block the main thread while a child thread monitors file changes
```

```javascript
// Option B: Push preview updates over WebSocket (Node.js)
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: 8080 });
const chokidar = require('chokidar');
chokidar.watch('./slides/').on('change', () => {
  rebuildPptx(); // Rebuild
  wss.clients.forEach(client => client.send('reload')); // Tell the frontend to refresh
});
```

```bash
# Option C: Simplest approach—use the entr or fswatch command-line tool
ls slides/*.slide | entr -r python build_pptx.py
```

> **Summary**: `slidep-start` = **create a file with python-pptx** + **watch files and rebuild automatically**. The former is essential; the latter is an enhancement. The minimum implementation requires only `prs.save()`.

---

### Step 5: Generate AI Images (Visuals Before Text)

#### Tool 4: `ImageGen`

**What it is**: An AI text-to-image tool that generates PNG files from prompts.

**Interface contract**:
```
Input:
  prompt: string        — Image-generation prompt
  size: string          — Image dimensions, such as "1536x1024" (landscape) / "1024x1024" (square)
  quality: string       — "high" | "standard"
  background: string    — "opaque" | "transparent"
  output_dir: string    — Output directory path
  style: string         — Optional visual-style description
Output: Saves a PNG file to output_dir
Side effects: Writes to the file system
```

**Cross-platform implementation**:

Choose any available API. The interface pattern is consistent: **prompt -> API call -> image bytes/base64 -> save file**.

**Option A: DALL-E 3 (OpenAI)**
```python
from openai import OpenAI
client = OpenAI(api_key="sk-...")

response = client.images.generate(
    model="dall-e-3",
    prompt="Warm flat illustration: a kindergarten entrance...",
    size="1792x1024",  # Landscape
    quality="hd",
    n=1,
)
image_url = response.data[0].url
# Download the URL to a local file
import requests
img_data = requests.get(image_url).content
with open("assets/cover_hero.png", "wb") as f:
    f.write(img_data)
```

**Option B: Stable Diffusion WebUI (self-hosted)**
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

**Option C: Tongyi Wanxiang (Alibaba Cloud)**
```python
import dashscope
dashscope.api_key = "sk-..."

response = dashscope.ImageSynthesis.call(
    model="wanx-v1",
    prompt="Warm flat illustration: a kindergarten entrance...",
    n=1,
    size="1536*1024",
)
image_url = response.output.results[0].url
# Download and save locally
```

**Option D: Midjourney (third-party API proxy)**
```python
# Through goapi or a similar proxy
response = requests.post("https://api.midjourney.com/imagine", json={
    "prompt": "warm flat illustration... --ar 3:2",
    "callback_url": "https://your-server.com/callback",
})
# Wait asynchronously for the callback, then download the returned image URL
```

**Prompt template** (API-independent):
```
[visual style] + [color tone] + [scene description] + [treatment of people] + [prohibited elements]
```
Key points:
- Specify the visual style (for example, "warm flat illustration").
- Specify a color tone consistent with the DESIGN.md palette.
- **Always show people from the back or in profile; do not render clear facial features.**
- Always end with: "Do not include any text or watermarks in the image."

> **Summary**: `ImageGen` = **call a text-to-image API + save the file**. The interface is consistent; switching APIs changes only the invocation code, not the prompt.

---

### Step 6: Produce, Validate, and Deliver Every Slide

#### 6.1 Produce Each Slide
Write content slide by slide according to the STORY.md contract and inject it into the PowerPoint engine.

**Example of slide-by-slide production with python-pptx**:
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# === Cover slide (Hero) ===
slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
# Full-bleed background image
slide.shapes.add_picture("assets/cover_hero.png", 0, 0, prs.slide_width, prs.slide_height)
# Gradient overlay (a translucent rectangle over the bottom to preserve text legibility)
from pptx.util import Emu
overlay = slide.shapes.add_shape(1, Inches(0), Inches(4.5), prs.slide_width, Inches(3))
overlay.fill.solid()
overlay.fill.fore_color.rgb = RGBColor(0xE8, 0x60, 0x3C)  # Primary color
overlay.fill.fore_color.brightness = -0.3  # Darken
# Title
txBox = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(11), Inches(1.5))
tf = txBox.text_frame
tf.text = "Devoted to Every Child, Guided by an Enduring Calling"
tf.paragraphs[0].font.size = Pt(44)
tf.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].alignment = PP_ALIGN.CENTER

# === Content slide (image left, text right) ===
slide2 = prs.slides.add_slide(prs.slide_layouts[6])
slide2.shapes.add_picture("assets/teacher_kids.png", Inches(0), Inches(0), Inches(7), Inches(7.5))
# Right-side text area
txBox2 = slide2.shapes.add_textbox(Inches(7.5), Inches(1), Inches(5), Inches(5.5))
# ...

prs.save("tribute_to_early_childhood_educator_zhang_shiyao.pptx")
```

#### Tool 5: `slidep-validate --all --project .`

**What it is**: Validates the syntax and structural correctness of all slide files.

**Interface contract**:
```
Input:
  --all: flag           — Validate every slide
  --project: string     — Project path
Output: Pass/fail status and error details for each slide
Side effects: None (read-only validation)
```

**Cross-platform implementation**:

This is essentially a **linting/validation script**. The checks depend on the PowerPoint engine.

**Example python-pptx validation script**:
```python
import os
from pptx import Presentation
from pptx.util import Emu

def validate_pptx(pptx_path, assets_dir):
    errors = []
    prs = Presentation(pptx_path)

    # Check 1: Total slide count
    expected_pages = 16
    actual_pages = len(prs.slides)
    if actual_pages != expected_pages:
        errors.append(f"Slide count mismatch: expected {expected_pages}, found {actual_pages}")

    for i, slide in enumerate(prs.slides):
        # Check 2: Image paths exist
        for shape in slide.shapes:
            if shape.shape_type == 13:  # PICTURE
                img_path = shape.image.filename or ""
                if img_path and not os.path.exists(img_path):
                    errors.append(f"Slide {i+1}: image does not exist: {img_path}")

        # Check 3: Text does not overflow (basic check)
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text
                    if len(text) > 200:
                        errors.append(f"Slide {i+1}: text is too long ({len(text)} characters) and may overflow")

    # Check 4: Color compliance (sample text colors and verify that they belong to the DESIGN.md palette)
    # ...

    return errors

errors = validate_pptx("output.pptx", "assets/")
if errors:
    for e in errors:
        print(f"FAIL: {e}")
else:
    print("PASS: All checks passed")
```

**General validation checklist**:
- [ ] Total slide count matches the outline.
- [ ] Each slide title matches the outline.
- [ ] Every slide includes all key content.
- [ ] Image files exist and paths are correct.
- [ ] Fonts are available on the target system.
- [ ] Colors match the DESIGN.md palette (no out-of-palette values).
- [ ] Text does not overflow the slide.
- [ ] Images contain no unintended watermarks.

#### Tool 6: `present_files(files)`

**What it is**: Presents files to the user and opens previews in a panel.

**Interface contract**:
```
Input:
  files: string[]       — Array of file paths or URLs
  cwd: string           — Optional working directory
  explanation: string   — Optional delivery note
Output: The user sees file previews in the interface
Side effects: Opens files in the user interface
```

**Cross-platform implementation**:

The core requirement is to **deliver the finished file to the user**.

| Platform Capability | Implementation | Code Example |
|---------|---------|---------|
| **Chat file attachments** | Send as an attachment | Slack: `files.upload`; Lark: `im/v1/files`; WeChat: send a file message |
| **Cloud storage** | Upload to S3/OSS and return a download link | `boto3.client('s3').upload_file(...)` -> return the URL |
| **Local path** | Tell the user the file path | `print(f"File saved: {os.path.abspath(path)}")` |
| **Email** | Send as an email attachment | SMTP `MIMEMultipart` + attachment |
| **Web download** | Start a temporary file server | `python -m http.server 8080` -> provide a download link |

**General implementation (Python)**:
```python
import shutil, os

def deliver_file(file_path, platform="local"):
    if platform == "local":
        abs_path = os.path.abspath(file_path)
        print(f"File ready: {abs_path}")
        return abs_path
    elif platform == "s3":
        import boto3
        s3 = boto3.client('s3')
        key = os.path.basename(file_path)
        s3.upload_file(file_path, "my-bucket", key)
        url = f"https://my-bucket.s3.amazonaws.com/{key}"
        print(f"Download URL: {url}")
        return url
    elif platform == "chat":
        # Use the platform SDK to send the file
        send_file_to_chat(file_path)
        return "sent"
```

> **Summary**: `present_files` = **push the file to the user**. Choose the method appropriate for the delivery channel: send an attachment, upload to cloud storage and return a link, or provide the local path.

---

## 3. Key Layout Principles

- **Hero slides as visual high points**: Use them for approximately one quarter of the deck (four in a 16-slide deck), distributed evenly across the opening, the midpoint climax, and the ending rather than clustered together.
- **Primarily asymmetric layouts**: Allocate 55–60% to images and 40–45% to text, using offset placement. Use fully symmetrical layouts only for ceremonial slides such as acknowledgments.
- **Rhythm**: Alternate hero slides (full-bleed image + large title) with content slides (column-based information).
- **Color consistency**: Use only the palette locked in DESIGN.md across all slides; keep illustration tones in the same color family as the slide backgrounds.

---

## 4. Tool Implementation Overview

| Tool | Essential Function | Minimum Implementation | Recommended Implementation |
|------|------|---------|---------|
| `read_me` | Load design tokens | Hard-coded JSON constants | Separate JSON configuration file + loader function |
| `show_widget` | Render SVG/HTML inline | Convert to a text description | Convert SVG to PNG + send the image |
| `slidep-start` | Create PowerPoint + watch files | `prs.save()` from `python-pptx` | python-pptx + automatic rebuild with watchdog |
| `ImageGen` | Text-to-image API | Any text-to-image API | DALL-E 3 or Stable Diffusion |
| `slidep-validate` | Linting/validation script | Per-slide checklist | Automated Python validation script |
| `present_files` | Deliver files | Provide the local path | Upload to cloud storage + return a download link |

---

## 5. Lessons Learned in Production

| # | Lesson | General/Specific |
|---|------|----------|
| 1 | Use absolute image paths, not relative paths. | General (all engines) |
| 2 | Do not use array indexing such as `[...][idx]` inside JSX/template attributes; use named object fields instead. | Specific (JSX engines) |
| 3 | Icon names must exist in the icon library's metadata (for example, if `sunset` does not exist, use `cloud-sun`). | Specific (icon libraries) |
| 4 | Confirm that required fonts are installed (`fc-list`) and choose broadly available fonts such as Songti SC or PingFang SC. | General |
| 5 | Mitigate AI-image watermarks with a page gradient overlay or by adding prohibited terms to the prompt. | General |
| 6 | Validation tools can produce noisy output; filter stack-trace lines and focus on results. | General |
| 7 | Use a lighter variant of the primary color for subtitles (reduce saturation); do not introduce a new color. | General (design) |
| 8 | Use explicit `\n` line breaks for long body copy instead of relying on automatic wrapping, ensuring cross-engine compatibility. | General |

---

## 6. Draft Agent System Prompt

The following can be used directly as the agent's system prompt:

```
You are a professional PowerPoint production assistant. After receiving the user's topic and outline, follow this process:

1. Parse the outline, determine the slide count and structure, and create a task list.
2. Prepare four visual-style options (palette + mood description) and render preview cards for the user to select from.
   - Rendering method: generate SVG preview cards -> convert them to PNG -> send them to the user.
   - If images cannot be sent, fall back to text descriptions and ask the user to reply with A/B/C/D.
3. After the user selects an option, write STORY.md (the slide-by-slide narrative contract) and DESIGN.md (strict visual constraints).
4. Create an empty PowerPoint file with python-pptx.
5. Generate supporting images according to the design document (6–8 illustrations in a consistent style, using a text-to-image API).
   - Every prompt must include: visual style + color tone + scene + people shown from behind + "no text or watermarks."
6. Produce the PowerPoint slide by slide and write each slide with python-pptx.
   - Favor asymmetric layouts and distribute hero slides evenly throughout the deck.
7. Run the validation script and confirm that all checks pass.
8. Send the .pptx file to the user.

Rules:
- Do not add or remove slides, titles, or key content from the outline; refine wording only.
- Create visuals before laying out text.
- Once the palette is locked, do not use colors outside it.
- Select broadly available system fonts and define fallback chains.
- Use absolute image paths.
```
