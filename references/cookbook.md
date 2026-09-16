# ks-anything-to-pdf · Cookbook(命令速查 / 坑 / 后处理)

按格式选择已安装的工具；安装示例面向 macOS/Homebrew，其他系统使用对应包管理器。转换命令也可独立运行。

---

## 0. 安装一条龙

```bash
# 按需选择，不必全部安装：
brew install --cask google-chrome
brew install weasyprint pandoc imagemagick
python3 -m pip install pymupdf          # 可选：转图验收
brew install --cask libreoffice          # Word/PPT/Excel → PDF
brew install img2pdf                      # 图片无损 → PDF(否则回退 ImageMagick)
brew install typst                        # Markdown 更优引擎 / .typ;免装 4GB MacTeX
brew install tectonic                     # .tex → PDF,单二进制按需下宏包
brew install --cask calibre              # ePub/MOBI → PDF
brew install qpdf ghostscript            # 后处理:合并/拆分 + 压缩
brew install font-noto-sans-cjk-sc       # LibreOffice 中文字体(防方框)
```

---

## 1. 全格式 X→PDF 命令速查

| 输入 | 一行命令 |
|---|---|
| HTML(静态) | `weasyprint in.html out.pdf` |
| HTML(含JS/web字体/现代CSS) | `python3 scripts/to_pdf.py in.html -o out.pdf`（在技能目录运行；自动查找 Chrome/Chromium，或设置 `CHROME_BIN`） |
| 网页 URL | 同上,把 `file://...` 换成 `https://...` |
| 网页(去广告净化) | `percollate pdf https://x.com/article -o a.pdf` |
| Markdown(推荐) | `pandoc in.md -o out.pdf --pdf-engine=typst`（或 `--pdf-engine=weasyprint`） |
| Markdown(零配置) | `md-to-pdf in.md`（npm,底层 Puppeteer) |
| Markdown→幻灯片 | `marp --pdf slides.md` |
| 数据科学报告 | `quarto render doc.qmd --to pdf` |
| Word / PPT / Excel | `soffice --headless --convert-to pdf in.docx --outdir ./out/` |
| 图片(无损) | `img2pdf *.jpg -o out.pdf` |
| 图片(调DPI/尺寸) | `magick *.jpg -density 300 -page A4 out.pdf` |
| ePub / MOBI | `ebook-convert in.epub out.pdf --paper-size a4 --pdf-add-toc` |
| LaTeX | `tectonic doc.tex` |
| Typst | `typst compile in.typ out.pdf` |

> 脚本通过 PATH 查找可执行文件，不读取 shell alias。macOS 另尝试 LibreOffice/Calibre 的标准应用路径；非标准安装请把可执行文件所在目录加入 PATH。

---

## 2. ⭐「同块不跨页」核心(HTML 路线)

可直接粘进样式表的关键规则(本 skill 的 `print_base.css` 已含通用部分):

```css
@page { size: A4; margin: 14mm 12mm; }
@media print {
  *,*::before,*::after { print-color-adjust: exact !important; -webkit-print-color-adjust: exact !important; }
  :root { color-scheme: only light; }                 /* 防 auto dark theme 反色 */
  h1,h2,h3,h4,h5,h6 { break-after: avoid; page-break-after: avoid; }
  p,li,blockquote { orphans: 3; widows: 3; }

  /* 要整块不跨页的卡片/条目(换成你的选择器): */
  .card,.player,.section { break-inside: avoid; page-break-inside: avoid; }
  /* 每节从新页开始: */
  .chapter { break-before: page; page-break-before: always; }

  /* 表格:表头每页重复 + 行不拆 */
  thead { display: table-header-group; } tr,td,th { break-inside: avoid; }
  /* 图片/figure 不拆 + 限高 */
  figure,img { break-inside: avoid; } img { max-width:100%; max-height:92vh; }
}
```

**各引擎差异 / 失效场景(关键):**
- 普通 **block** 元素 `break-inside: avoid` —— Chrome / WeasyPrint / Prince 都可靠。
- **flex / grid 子项** —— Chromium 有未修 bug(#719908),WeasyPrint flex 多列也有(#2440)。
  **workaround:把父容器在 `@media print` 里 `display: block`**(本 skill 用 `--flat "选择器"`),再给子项加 break-inside。
- **table** —— 避免 `border-collapse: collapse` 跨页(边框错乱),用 `separate`;`tr` 加 break-inside。
- **硬限制**:块本身高于一整页时,所有引擎都被迫拆开它(CSS 规范软约束)。只能缩小或拆分内容。
- `break-inside` 与 `page-break-inside` **双写**(新旧别名),兼容性最好。

---

## 3. 常见坑速查

| 现象 | 原因 / 对策 |
|---|---|
| 背景色 / 底色丢失变白 | 加 `print-color-adjust: exact`(本 skill 默认已加) |
| 颜色被反转 / 变暗 | `:root { color-scheme: only light; }` |
| 中文变方框(豆腐) | LibreOffice 缺字:`brew install font-noto-sans-cjk-sc`;Typst 模板里 `#set text(font:"PingFang SC")` |
| web 字体没加载好 | Chrome 加 `--virtual-time-budget=25000`(给加载时间);确保联网 |
| 透明 PNG → PDF 变大/失真 | 先 `magick in.png -background white -alpha remove flat.png`(本 skill 自动做) |
| ImageMagick 报 PDF 权限错 | 先用 `magick -list policy` 查看策略位置；优先使用 img2pdf。需要修改系统策略时先确认影响与授权 |
| 文字不可选 / 放大糊 | 别用 jsPDF+html2canvas(位图);用 Chrome/WeasyPrint(矢量) |
| 导航栏 / 侧边栏混进 PDF | 给它们 `class="no-print"` 或本 skill 默认隐藏 `nav` |

---

## 4. PDF 后处理(合并 / 拆分 / 压缩 / 加密)

```bash
qpdf --empty --pages a.pdf b.pdf -- merged.pdf        # 页面合并（不保证保留原书签/内链）
qpdf --split-pages in.pdf page_%d.pdf                  # 每页拆分
qpdf --empty --pages in.pdf 1,3-5,7 -- out.pdf         # 抽取指定页
gs -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile=small.pdf in.pdf                       # 压缩(/screen<最小 /ebook /printer /prepress)
qpdf --encrypt USERPW OWNERPW 256 -- in.pdf enc.pdf    # AES-256 加密
```

---

## 5. 引擎选择决策树

```
含 JS / SPA / 图表 / web字体 / 现代CSS(backdrop-filter,clamp)?  → Chrome headless / Playwright
纯静态 HTML、要最小体积 / Python 栈?                          → WeasyPrint
整本书排版(running header / 自动TOC / 出血裁切)?             → Paged.js
Markdown / 学术 / 含代码执行?                                 → pandoc(+typst) / Quarto
Office 文档?                                                  → LibreOffice headless
❌ 永远别用:wkhtmltopdf(EOL+CVE)、jsPDF+html2canvas(位图,正式文档勿用)
```

---

## 6. 中文 Markdown 排版

在技能目录运行：

```bash
bash scripts/md_zh.sh report.md report.pdf --palette cream
```

所需 `scripts/md_zh.sh`、`scripts/zh-doc.css` 均随包提供；依赖 pandoc、Chrome/Chromium 和中文字体。配色可选 `nude` 或 `cream`。Markdown 的本地图片建议使用绝对路径，中间 HTML 位于临时目录。
