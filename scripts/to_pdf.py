#!/usr/bin/env python3
"""
ks-anything-to-pdf · dispatcher (to_pdf.py)
把任意输入(文件或 URL)转成 PDF。按扩展名分流到现成成熟 CLI。
本脚本【不自己实现任何转换】,只做四件现成工具没帮你做的事:
  ① 选对引擎   ② HTML 注入「同块不跨页」打印 CSS   ③ 统一调用   ④ 触发转图验收

分流(权威表见 SKILL.md):
  .html .htm        → Chrome headless(默认,保真最高)/ WeasyPrint(--engine weasyprint)
  URL(http/https)  → Chrome headless / WeasyPrint
  .md .markdown .rst .org .ipynb → pandoc(--pdf-engine 自动选 weasyprint>typst>latex)
  .docx .pptx .xlsx .odt .ods .odp .rtf → LibreOffice headless
  .jpg .jpeg .png .tiff .webp .gif → img2pdf(无损,缺则 ImageMagick)
  .epub .mobi .azw3 → Calibre ebook-convert
  .tex              → Tectonic
  .typ              → Typst

HTML 专用选项(这是本 skill 的灵魂,把「同块不跨页」参数化):
  --keep "SEL,SEL"            这些选择器的块整体不跨页
  --page-break-before "SEL"   这些选择器各自从新页开始
  --flat "SEL"                把这些 flex/grid 容器在打印时降级 block(子项 break-inside 失效时)
  --engine chrome|weasyprint  默认 chrome;纯静态简单页可用 weasyprint(更快更小)
  --size A4|Letter|A3|...      纸张(默认 A4)   --landscape 横向   --margin "14mm 12mm"

通用:
  -o OUT.pdf      指定输出   --no-verify 跳过验收   --verify-pages N 抽样页数

示例:
  python3 to_pdf.py report.md
  python3 to_pdf.py deck.pptx -o deck.pdf
  python3 to_pdf.py teams.html --page-break-before ".team-section" \\
                    --keep ".player,.coach-card,.tactical,.story,.team-head"
  python3 to_pdf.py ./folder                       # 批量:目录内每个文件各转一个 PDF
  python3 to_pdf.py ./photos --merge -o album.pdf  # 多图无损合并成一个 PDF
"""
import argparse, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME_CANDIDATES = ([os.environ["CHROME_BIN"]] if os.environ.get("CHROME_BIN") else [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
])
SOFFICE_CANDIDATES = ["soffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice"]
EBOOK_CANDIDATES = ["ebook-convert", "/Applications/calibre.app/Contents/MacOS/ebook-convert"]


# ----------------------------------------------------------------------------- helpers
def have(cmd):
    return shutil.which(cmd) is not None


def find_path(cands):
    for c in cands:
        resolved = shutil.which(os.path.expanduser(c))
        if resolved:
            return resolved
    return None


def die(msg, install=None):
    sys.stderr.write("\n❌ " + msg + "\n")
    if install:
        sys.stderr.write("   安装: " + install + "\n")
    sys.exit(1)


def run(cmd):
    sys.stderr.write("· " + " ".join((repr(c) if " " in c else c) for c in cmd) + "\n")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write((r.stdout or "") + "\n" + (r.stderr or "") + "\n")
        die("命令失败(退出码 %d): %s" % (r.returncode, cmd[0]))


def run_ok(cmd):
    """跑命令,返回 (是否成功, 错误输出)。不退出,供需要回退的场景用。"""
    sys.stderr.write("· " + " ".join((repr(c) if " " in c else c) for c in cmd) + "\n")
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout or "")


# ----------------------------------------------------------------------------- HTML
def build_print_css(args):
    base = open(os.path.join(HERE, "print_base.css"), encoding="utf-8").read()
    size = args.size + (" landscape" if args.landscape else "")
    parts = [base, "\n/* --- 动态注入(命令行参数) --- */",
             "@page{size:%s;margin:%s;}" % (size, args.margin)]
    rules = []
    if args.keep.strip():
        rules.append("%s{break-inside:avoid;page-break-inside:avoid;}" % args.keep.strip())
    if args.page_break_before.strip():
        rules.append("%s{break-before:page;page-break-before:always;}" % args.page_break_before.strip())
    if args.flat.strip():
        rules.append("%s{display:block !important;}" % args.flat.strip())
    if rules:
        parts.append("@media print{\n" + "\n".join(rules) + "\n}")
    return "\n".join(parts)


def html_to_pdf(inp, out, args):
    css = build_print_css(args)
    html = open(inp, encoding="utf-8", errors="ignore").read()
    inject = '<style data-injected-by="ks-anything-to-pdf">\n' + css + "\n</style>"
    low = html.lower()
    if "</head>" in low:
        i = low.index("</head>"); html2 = html[:i] + inject + "\n" + html[i:]
    elif "<body" in low:
        i = low.index("<body"); html2 = html[:i] + inject + "\n" + html[i:]
    else:
        html2 = inject + "\n" + html
    # 临时文件写到源同目录,保证相对资源(本地图片/CSS/字体)可解析
    d = os.path.dirname(inp) or "."
    tmp = os.path.join(d, "._atp_" + os.path.basename(os.path.splitext(inp)[0]) + ".html")
    open(tmp, "w", encoding="utf-8").write(html2)
    try:
        if args.engine == "weasyprint":
            if not have("weasyprint"):
                die("需要 weasyprint", "brew install weasyprint")
            run(["weasyprint", tmp, out])
        else:
            chrome = find_path(CHROME_CANDIDATES)
            if not chrome:
                die("需要 Chrome/Chromium，可设置 CHROME_BIN（或改用 --engine weasyprint）",
                    "从 https://www.google.com/chrome/ 下载")
            run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                 "--print-to-pdf=" + out, "--virtual-time-budget=25000",
                 "--run-all-compositor-stages-before-draw", "file://" + os.path.abspath(tmp)])
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def url_to_pdf(url, out, args):
    if args.engine == "weasyprint":
        if not have("weasyprint"):
            die("需要 weasyprint", "brew install weasyprint")
        run(["weasyprint", url, out])
    else:
        chrome = find_path(CHROME_CANDIDATES)
        if not chrome:
            die("需要 Chrome/Chromium，可设置 CHROME_BIN", "从 https://www.google.com/chrome/ 下载")
        run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             "--print-to-pdf=" + out, "--virtual-time-budget=25000",
             "--run-all-compositor-stages-before-draw", url])


# ----------------------------------------------------------------------------- others
def md_to_pdf(inp, out, args):
    if not have("pandoc"):
        die("Markdown→PDF 需要 pandoc", "brew install pandoc")
    engine = next((e for e in ("weasyprint", "typst") if have(e)), None)  # weasyprint 优先:中文开箱即用、最不挑环境(typst 中文依赖系统 CJK 字体)
    cmd = ["pandoc", inp, "-o", out]
    if engine:
        cmd.append("--pdf-engine=" + engine)
    else:
        sys.stderr.write("⚠️  未装 typst/weasyprint,pandoc 将尝试 LaTeX 引擎"
                         "(中文可能需要 MacTeX + CJK 配置)。建议: brew install typst\n")
    run(cmd)


def office_to_pdf(inp, out, args):
    so = find_path(SOFFICE_CANDIDATES)
    if not so:
        die("Office(Word/PPT/Excel)→PDF 需要 LibreOffice", "brew install --cask libreoffice")
    outdir = os.path.dirname(out) or "."
    run([so, "--headless", "--convert-to", "pdf", "--outdir", outdir, inp])
    produced = os.path.join(outdir, os.path.splitext(os.path.basename(inp))[0] + ".pdf")
    if os.path.exists(produced) and os.path.abspath(produced) != os.path.abspath(out):
        shutil.move(produced, out)


def image_to_pdf(inp, out, args):
    ext = inp.rsplit(".", 1)[-1].lower()
    src = inp
    tmp = None
    if ext in ("png", "gif", "webp"):  # 可能含透明通道,先铺白底避免 img2pdf 退化重编码
        if have("magick"):
            tmp = tempfile.mktemp(suffix=".png")
            run(["magick", inp, "-background", "white", "-alpha", "remove", "-alpha", "off", tmp])
            src = tmp
    try:
        if have("img2pdf"):
            ok, err = run_ok(["img2pdf", src, "-o", out])
            if ok and os.path.exists(out) and os.path.getsize(out) > 100:
                return
            sys.stderr.write("img2pdf 失败,回退 ImageMagick: %s\n" % err.strip()[:200])
        if have("magick"):
            run(["magick", src, out])   # 兼容 12/16-bit、CMYK 等 img2pdf 啃不动的图(有损重编码)
        else:
            die("图片→PDF 需要 img2pdf(无损,推荐)或 ImageMagick", "brew install img2pdf")
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def epub_to_pdf(inp, out, args):
    eb = find_path(EBOOK_CANDIDATES)
    if not eb:
        die("电子书→PDF 需要 Calibre", "brew install --cask calibre")
    run([eb, inp, out, "--paper-size", "a4", "--pdf-add-toc"])


def tex_to_pdf(inp, out, args):
    if not have("tectonic"):
        die("LaTeX→PDF 推荐 Tectonic(免装 4GB TeXLive)", "brew install tectonic")
    outdir = os.path.dirname(out) or "."
    run(["tectonic", inp, "--outdir", outdir])
    produced = os.path.join(outdir, os.path.splitext(os.path.basename(inp))[0] + ".pdf")
    if os.path.exists(produced) and os.path.abspath(produced) != os.path.abspath(out):
        shutil.move(produced, out)


def typ_to_pdf(inp, out, args):
    if not have("typst"):
        die("Typst→PDF 需要 typst", "brew install typst")
    run(["typst", "compile", inp, out])


DISPATCH = {
    "html": html_to_pdf, "htm": html_to_pdf,
    "md": md_to_pdf, "markdown": md_to_pdf, "rst": md_to_pdf, "org": md_to_pdf, "ipynb": md_to_pdf,
    "docx": office_to_pdf, "pptx": office_to_pdf, "xlsx": office_to_pdf,
    "odt": office_to_pdf, "ods": office_to_pdf, "odp": office_to_pdf, "rtf": office_to_pdf,
    "jpg": image_to_pdf, "jpeg": image_to_pdf, "png": image_to_pdf,
    "tiff": image_to_pdf, "tif": image_to_pdf, "webp": image_to_pdf, "gif": image_to_pdf,
    "epub": epub_to_pdf, "mobi": epub_to_pdf, "azw3": epub_to_pdf,
    "tex": tex_to_pdf, "typ": typ_to_pdf,
}

IMAGE_EXTS = {"jpg", "jpeg", "png", "tiff", "tif", "webp", "gif"}


# ----------------------------------------------------------------------------- 目录批量 / 合并
def collect_files(d):
    """目录内所有可处理文件,返回 [(ext, path)] 按名排序(含 .pdf 仅供合并)。"""
    items = []
    for nm in sorted(os.listdir(d)):
        p = os.path.join(d, nm)
        if os.path.isfile(p) and "." in nm:
            ext = nm.rsplit(".", 1)[-1].lower()
            if ext in DISPATCH or ext == "pdf":
                items.append((ext, p))
    return items


def merge_images(files, out, args):
    """多张图片合并成一个 PDF:优先 img2pdf(无损),失败回退 ImageMagick(兼容异常格式)。"""
    tmps, srcs = [], []
    for f in files:
        ext = f.rsplit(".", 1)[-1].lower()
        if ext in ("png", "gif", "webp") and have("magick"):
            t = tempfile.mktemp(suffix=".png")
            run(["magick", f, "-background", "white", "-alpha", "remove", "-alpha", "off", t])
            tmps.append(t); srcs.append(t)
        else:
            srcs.append(f)
    try:
        if have("img2pdf"):
            ok, err = run_ok(["img2pdf", *srcs, "-o", out])
            if ok and os.path.exists(out) and os.path.getsize(out) > 100:
                return
            sys.stderr.write("img2pdf 失败,回退 ImageMagick 合并: %s\n" % err.strip()[:200])
        if have("magick"):
            run(["magick", *srcs, out])
        else:
            die("图片合并需要 img2pdf 或 ImageMagick", "brew install img2pdf")
    finally:
        for t in tmps:
            if os.path.exists(t):
                os.remove(t)


def merge_pdfs(files, out):
    """多个 PDF 合并(qpdf；不保证保留原书签/内链)。"""
    if not have("qpdf"):
        die("PDF 合并需要 qpdf", "brew install qpdf")
    run(["qpdf", "--empty", "--pages", *files, "--", out])


# ----------------------------------------------------------------------------- main
def verify(out, pages):
    vp = os.path.join(HERE, "verify_pdf.py")
    try:
        subprocess.run([sys.executable, vp, out, "--pages", str(pages)], check=False)
    except Exception as e:
        sys.stderr.write("验收步骤跳过: %s\n" % e)


def main():
    ap = argparse.ArgumentParser(add_help=True, description="anything → PDF dispatcher")
    ap.add_argument("input", help="输入文件路径 或 http(s) URL")
    ap.add_argument("-o", "--output")
    ap.add_argument("--engine", choices=["chrome", "weasyprint"], default="chrome",
                    help="HTML/URL 引擎(默认 chrome,保真最高)")
    ap.add_argument("--keep", default="", help='整块不跨页的 CSS 选择器,逗号分隔')
    ap.add_argument("--page-break-before", dest="page_break_before", default="",
                    help="各自从新页开始的 CSS 选择器")
    ap.add_argument("--flat", default="", help="打印时降级为 block 的 flex/grid 容器选择器")
    ap.add_argument("--size", default="A4")
    ap.add_argument("--landscape", action="store_true")
    ap.add_argument("--margin", default="14mm 12mm")
    ap.add_argument("--merge", action="store_true",
                    help="把目录内的图片(或 PDF)合并成单个 PDF")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--verify-pages", type=int, default=6)
    args = ap.parse_args()

    inp = args.input
    is_url = inp.lower().startswith(("http://", "https://"))

    if is_url:
        out = os.path.abspath(args.output or "url-output.pdf")
        print("🌐 URL → PDF (%s)" % args.engine)
        url_to_pdf(inp, out, args)
    elif os.path.isdir(inp):
        inp = os.path.abspath(inp)
        items = collect_files(inp)
        if not items:
            die("目录内没有可处理的文件: " + inp)
        exts = {e for e, _ in items}
        files = [p for _, p in items]
        if args.merge:
            out = os.path.abspath(args.output) if args.output else os.path.join(inp, "merged.pdf")
            if exts <= IMAGE_EXTS:
                print("🖼️  合并 %d 张图片 → 单个 PDF" % len(files)); merge_images(files, out, args)
            elif exts <= {"pdf"}:
                print("📑 合并 %d 个 PDF" % len(files)); merge_pdfs(files, out)
            else:
                die("--merge 仅支持「全是图片」或「全是 PDF」的目录")
        else:
            conv = [(e, p) for e, p in items if e != "pdf"]
            if not conv:
                die("目录内只有 PDF;如需合并请加 --merge")
            print("📂 批量转换目录内 %d 个文件" % len(conv))
            for e, p in conv:
                o = os.path.splitext(p)[0] + ".pdf"
                print("  → %s" % os.path.basename(o))
                DISPATCH[e](p, o, args)
            print("\n✅ 批量完成:%d 个文件" % len(conv))
            return
    else:
        inp = os.path.abspath(inp)
        if not os.path.exists(inp):
            die("找不到输入文件: " + inp)
        name = os.path.basename(inp)
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        out = os.path.abspath(args.output) if args.output else os.path.splitext(inp)[0] + ".pdf"
        fn = DISPATCH.get(ext)
        if not fn:
            die("暂不支持的扩展名: .%s" % ext,
                "支持: " + ", ".join(sorted(set(DISPATCH))) + ", 以及 http(s) URL")
        print("📥 .%s → PDF  (%s)" % (ext, fn.__name__))
        fn(inp, out, args)

    if not os.path.exists(out) or os.path.getsize(out) < 1024:
        die("转换似乎失败:输出不存在或过小(%s)" % out)

    if not args.no_verify:
        verify(out, args.verify_pages)
    print("\n✅ 完成 → %s  (%.1f MB)" % (out, os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    main()
