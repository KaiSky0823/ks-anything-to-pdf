# ks-anything-to-pdf

把 HTML、Markdown、Office 文档、图片、电子书、LaTeX、Typst 或网页转成 PDF。复用现有转换工具，补充 HTML 分页控制、中文文档样式与转图验收。

## 安装

Claude Code：

```bash
git clone https://github.com/KaiSky0823/ks-anything-to-pdf.git ~/.claude/skills/ks-anything-to-pdf
```

Codex：

```bash
git clone https://github.com/KaiSky0823/ks-anything-to-pdf.git ~/.agents/skills/ks-anything-to-pdf
```

安装后重启客户端或刷新技能列表。也可直接克隆到其他目录，通过脚本使用。

## 依赖

基础依赖 Python 3；中文排版脚本另需 Bash。只安装所用格式对应的引擎：

| 输入／功能 | 工具 |
|---|---|
| HTML、网页 | Chrome/Chromium，或 WeasyPrint |
| Markdown 等文本格式 | pandoc + WeasyPrint、Typst 或 LaTeX |
| 中文 Markdown 样式 | pandoc + Chrome/Chromium + 系统中文字体 |
| Word、PPT、Excel | LibreOffice |
| 图片 | img2pdf；ImageMagick 可作兼容回退 |
| ePub、MOBI、AZW3 | Calibre |
| LaTeX / Typst | Tectonic / Typst |
| PDF 合并 | qpdf |
| 转图验收 | PyMuPDF，可选；缺失时跳过 |

工具通过 `PATH` 查找；Chrome 也可通过 `CHROME_BIN` 指定可执行文件路径（不含参数）。macOS 会尝试常见应用路径。中文可安装 Noto Sans CJK SC；中文样式的数字衬线效果可选装 Noto Serif SC。缺字时先检查系统字体。

安装命令和其他转换工具示例见 [cookbook](references/cookbook.md)。脚本不会自动安装依赖或修改系统配置。

## 运行

在克隆的仓库／技能目录运行：

```bash
python3 scripts/to_pdf.py /path/to/report.md -o /path/to/report.pdf
python3 scripts/to_pdf.py /path/to/report.html -o /path/to/report.pdf \
  --keep ".card" --page-break-before ".chapter" --size A4
bash scripts/md_zh.sh /path/to/report.md /path/to/report.pdf --palette cream
python3 scripts/to_pdf.py /path/to/photos --merge -o /path/to/album.pdf
python3 scripts/verify_pdf.py /path/to/report.pdf --pages 6
```

中文配色支持 `nude` 和 `cream`。`--engine weasyprint` 适用于静态 HTML；`--no-verify` 跳过自动验收。完整选项见 `python3 scripts/to_pdf.py --help` 和 [SKILL.md](SKILL.md)。

生成的验收图位于输出目录下 `_verify/`。批量转换不会自动验收，应对需要检查的 PDF 单独运行验收脚本。转换可能覆盖同名输出；保留旧结果时使用新的 `-o` 路径。外部字体、图片、URL 和 Tectonic 首次下载宏包可能需要网络。

## 来源与范围

本仓库由个人使用的 `anything-to-pdf` 整理发布，保留较新版本中的 `md_zh.sh` 与 `zh-doc.css`。底层转换依赖上表中的第三方工具；没有把这些工具或未随包提供的本地研究资料作为仓库内容分发。
