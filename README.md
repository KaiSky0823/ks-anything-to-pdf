# ks-anything-to-pdf · 什么都能转 PDF 📄

> *One thin dispatcher over the mature converters (Chrome, WeasyPrint, pandoc, LibreOffice, img2pdf, Calibre, Tectonic, Typst), plus "keep this block on one page" CSS and self-verification.*

每次要出一份 PDF，都要重新想一遍：这个用 pandoc 还是 Chrome？中文字体为什么又是方块？卡片为什么被分页切成两半？转完了还得自己翻一遍看有没有排崩。

这个 skill 把这些问题一次性收掉。

## 🧩 它怎么做

一层薄 dispatcher，按输入类型把活派给最合适的成熟工具，**自己不造轮子**：

| 输入 | 引擎 |
|---|---|
| HTML、网页 | Chrome/Chromium 或 WeasyPrint |
| Markdown 等文本 | pandoc + WeasyPrint、Typst 或 LaTeX |
| 中文 Markdown（带样式） | pandoc + Chrome + 系统中文字体 |
| Word、PPT、Excel | LibreOffice |
| 图片、整个相册目录 | img2pdf（ImageMagick 回退） |
| ePub、MOBI、AZW3 | Calibre |
| LaTeX / Typst | Tectonic / Typst |
| 合并 | qpdf |

在此之上加了三样别人没有的：

- 📐 **同块不跨页** —— `--keep ".card"` 自动注入打印 CSS，卡片、表格、代码块不再被分页拦腰切断
- 🀄 **中文文档样式** —— `md_zh.sh` + `zh-doc.css`，两套配色（`nude` / `cream`），数字衬线、标题层级、页边距一次调好
- 👀 **转图验收** —— 转完自动把前几页渲染成图放在 `_verify/`，你或 AI 看一眼就知道有没有排崩

## 💬 你说什么，它给什么

你说：「把这份 report.md 转成 PDF，卡片别跨页」

它跑：
```bash
python3 scripts/to_pdf.py report.md -o report.pdf --keep ".card"
```
然后给你 PDF + 验收图。中文报告直接：
```bash
bash scripts/md_zh.sh report.md report.pdf --palette cream
```

## ⚙️ 安装

```bash
# Claude Code
git clone https://github.com/KaiSky0823/ks-anything-to-pdf.git ~/.claude/skills/ks-anything-to-pdf
# Codex
git clone https://github.com/KaiSky0823/ks-anything-to-pdf.git ~/.agents/skills/ks-anything-to-pdf
```

基础依赖 Python 3；只装你用得到的引擎（安装命令见 [cookbook](references/cookbook.md)）。工具通过 `PATH` 查找，Chrome 可用 `CHROME_BIN` 指定。中文装 Noto Sans CJK SC，数字衬线可选 Noto Serif SC。脚本**不会**自动安装依赖或改系统配置。

## 🛠️ 更多用法

```bash
python3 scripts/to_pdf.py report.html -o report.pdf --keep ".card" --page-break-before ".chapter" --size A4
python3 scripts/to_pdf.py ./photos --merge -o album.pdf
python3 scripts/verify_pdf.py report.pdf --pages 6
```
`--engine weasyprint` 适合静态 HTML；`--no-verify` 跳过验收；批量转换不自动验收。转换可能覆盖同名输出，要留旧结果就换 `-o` 路径。完整选项见 `--help` 和 SKILL.md。

## 📖 来源

由个人日常使用的 `anything-to-pdf` 整理发布。底层引擎全是第三方工具，本仓库不分发它们，也不含任何私人研究资料。

## License

MIT © 2026 KaiSky0823
