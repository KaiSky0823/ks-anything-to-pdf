---
name: ks-anything-to-pdf
description: >-
  把任意输入(HTML / Markdown / Word·PPT·Excel / 图片 / 网页URL / ePub / LaTeX·Typst)转成高质量 PDF。
  一层薄 dispatcher,底层全调用现成成熟 CLI(Chrome headless · WeasyPrint · pandoc · LibreOffice ·
  img2pdf · Calibre · Tectonic · Typst),另外提供:HTML 的「同块不跨页」打印 CSS 自动注入,
  以及转图视觉验收。当用户想把某个文件 / 网页 / 整个文件夹做成 PDF、批量转 PDF、或要求转出的 PDF
  「同一区块不被分页拆断 / 同区域在一页 / 卡片不跨页」时使用。
  触发词:转PDF、转成PDF、做成PDF、生成PDF、导出PDF、html转pdf、markdown转pdf、md转pdf、
  word转pdf、ppt转pdf、excel转pdf、图片转pdf、网页转pdf、批量转pdf、合并PDF、压缩PDF、
  to PDF、convert to PDF、export PDF、同块不跨页、不要跨页、卡片不跨页、区块完整。
---

# ks-anything-to-pdf

把任意输入转成 PDF。**不重复造轮子**——底层全是现成成熟 CLI;本 skill 的价值在于「选对引擎 + HTML 同块不跨页 + 转图验收」这层粘合。

脚本:`scripts/to_pdf.py`(主入口)、`scripts/print_base.css`(通用打印基线)、`scripts/verify_pdf.py`(转图验收)。
完整命令速查 / 各格式坑 / 安装一条龙:见 `references/cookbook.md`。

---

## 分流与依赖

| 输入 | 引擎(按需安装) | 依赖 |
|---|---|---|
| `.html` `.htm` / URL | **Chrome headless**(默认,保真最高)或 WeasyPrint(`--engine weasyprint`,纯静态更快更小) | Chrome/Chromium 或 WeasyPrint |
| `.md` `.markdown` `.rst` `.org` `.ipynb` | **pandoc**(weasyprint 引擎优先:中文最稳、最不挑环境;typst 作 fallback) | pandoc + WeasyPrint/Typst/LaTeX |
| `.docx` `.pptx` `.xlsx` `.odt` `.ods` `.odp` `.rtf` | **LibreOffice headless** | 需对应引擎 |
| `.jpg` `.png` `.tiff` `.webp` `.gif` | **img2pdf**(无损)→ 缺则 ImageMagick | img2pdf 或 ImageMagick |
| `.epub` `.mobi` `.azw3` | **Calibre ebook-convert** | 需对应引擎 |
| `.tex` | **Tectonic** | 需对应引擎 |
| `.typ` | **Typst** | 需对应引擎 |

> 不假定本机已安装这些工具；先检查所选路线的命令与字体。命令从 PATH 查找；Chrome 另支持 `CHROME_BIN` 指定可执行文件。LibreOffice、Calibre 和 Chrome 也尝试常见 macOS 应用路径。

工具缺失时脚本打印依赖提示并退出，不自动安装；其中 Homebrew 命令仅适用于 macOS。其他系统使用相应包管理器。按用户已授权的范围处理安装。

---

## 工作流(按此顺序)

以下命令在本技能安装目录运行（Claude Code 通常为 `~/.claude/skills/ks-anything-to-pdf`，Codex 通常为 `~/.agents/skills/ks-anything-to-pdf`）。

### 通用(Markdown / Office / 图片 / 电子书 / URL)— 直接一条命令
```bash
python3 scripts/to_pdf.py 输入文件 [-o 输出.pdf]
```
安装 PyMuPDF 后，单文件和合并转换会自动渲染验收图到 `输出同目录/_verify/`（`--no-verify` 可跳过）；批量转换需另行运行 `scripts/verify_pdf.py`。用当前环境的图片查看工具打开 PNG，核对背景色、中文缺字和分页。

### 批量 / 合并(传目录而非单文件)
- **批量转换**:`to_pdf.py ./folder` —— 目录内每个支持的文件各转一个同名 PDF
- **多图合并**:`to_pdf.py ./photos --merge -o album.pdf` —— 目录内所有图片合并成一个 PDF(img2pdf 无损;遇 12/16-bit、CMYK 等异常图**自动回退 ImageMagick**)
- **PDF 合并**:`to_pdf.py ./pdfs --merge -o all.pdf` —— 目录内所有 PDF 合并(qpdf，合并页面，不保证保留原书签)

### ⭐ HTML —— 这是本 skill 的灵魂,转之前先「读结构」

通用打印基线(保色 / 隐藏导航 / 表头重复 / 图表不拆)对所有 HTML 自动生效。但「**让某种卡片/区块整体不跨页**」需要知道它的 CSS 选择器,所以:

1. **先看 HTML 结构**,找出两类东西:
   - 重复的内容块(卡片、条目、section)→ 用 `--keep` 让它们整块不跨页
   - 大的分节容器(每章 / 每个主题)→ 用 `--page-break-before` 让每节从新页开始
   ```bash
   grep -oE 'class="[^"]*"' 输入.html | sort | uniq -c | sort -rn | head -30   # 看主要块的类名
   ```
2. **带参数转换**(实例,来自世界杯球队档案 HTML):
   ```bash
   python3 scripts/to_pdf.py teams.html \
     --page-break-before ".team-section" \
     --keep ".team-head,.coach-card,.tactical,.story,.warning-card,.player,.subhead" \
     --size A4 --margin "14mm 11mm"
   ```
3. **读验收图核对**。若发现某卡片仍被拆断,且它是 flex/grid 布局,加 `--flat ".那个容器"`(打印时降级 block,Chromium grid 的 break-inside bug #719908 的标准 workaround)。

HTML 选项速查:
- `--engine chrome|weasyprint`(默认 chrome;含 JS/web字体/backdrop-filter/现代CSS 必须 chrome)
- `--keep "SEL,SEL"`(整块不跨页)  · `--page-break-before "SEL"`(每节新页)  · `--flat "SEL"`(降级 block)
- `--size A4|Letter|A3` · `--landscape` · `--margin "14mm 12mm"`

---

## 中文 Markdown 排版

```bash
bash scripts/md_zh.sh 输入.md 输出.pdf --palette nude
bash scripts/md_zh.sh 输入.md 输出.pdf --palette cream
```

依赖 pandoc、Chrome/Chromium 和系统中文字体；使用 `scripts/zh-doc.css`，提供裸粉与奶油两种配色、表格按行分页、重复表头、代码块和引用样式。CSS 内联，不依赖外部样式文件。Markdown 中的图片建议使用绝对路径，或资源完整的 URL；中间 HTML 在临时目录生成。

## 重要提醒

- **联网**：引用远程字体、图片或 URL 时需要相应网络权限；遵守当前客户端的权限机制，不假设 Claude 专有参数在 Codex 可用。离线转换应使用本地资源；Tectonic 首次使用可能需要下载宏包。
- **不改用户原文件**:HTML 路径会复制一份注入打印 CSS(临时文件 `._atp_*.html`,用完自动删),原 HTML 不动。
- **超高块的硬限制**:任何单个块本身就比一整页还高时,所有引擎都会被迫拆开它(CSS 规范,不是 bug)。对策是缩小该块字号/留白,或拆分内容。
- **中文**:Chrome / WeasyPrint 走系统字体即可;LibreOffice 若中文变方框,`brew install font-noto-sans-cjk-sc`;pandoc 走 latex 引擎才需额外 CJK 配置(优先用 typst/weasyprint 引擎免配置)。
- **批量**:对文件夹逐个文件调脚本即可;需要合并/压缩见 cookbook.md 的 qpdf / Ghostscript 后处理。
- **其他 PDF 操作**：提取、表单、OCR 可使用当前客户端实际安装的 PDF 技能；本技能主要负责生成 PDF，不假定存在其他插件。
- **URL 与本地 HTML**：`--keep`、`--page-break-before`、`--flat`、纸张与边距 CSS 只对本地 HTML 注入；URL 路径直接交给引擎打印。
- **输出文件**：转换可能覆盖同名 PDF；需要保留已有结果时使用新的 `-o` 路径。
