#!/usr/bin/env python3
"""
ks-anything-to-pdf · 转图验收 (verify_pdf.py)
把生成的 PDF 渲染成 PNG 供 agent 肉眼复核,并自动标记可能的分页问题。
现成工具(Chrome/LibreOffice/pandoc)缺字时是「静默替换」不报错——
只有把页面渲成图让 agent 读,才抓得到白屏 / 缺字(豆腐块)/ 区块被拦腰截断 / 尾页近空白。

依赖:PyMuPDF (pip install pymupdf)。无则优雅退出,不影响转换本身。

用法:
  python3 verify_pdf.py OUT.pdf [--pages 6] [--zoom 2.0] [--outdir DIR]
"""
import argparse, os, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", type=int, default=6, help="抽样渲染的页数(首+尾+均匀抽样)")
    ap.add_argument("--zoom", type=float, default=2.0, help="渲染清晰度倍数")
    ap.add_argument("--outdir", default=None)
    args = ap.parse_args()

    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("⚠️  未装 PyMuPDF,跳过转图验收(pip install pymupdf 可启用)。")
        return 0

    pdf = os.path.abspath(args.pdf)
    if not os.path.exists(pdf):
        print(f"⚠️  验收找不到 PDF: {pdf}")
        return 0

    doc = fitz.open(pdf)
    n = doc.page_count
    outdir = args.outdir or os.path.join(os.path.dirname(pdf), "_verify")
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf))[0]

    # 选页:首页 + 末页 + 中间均匀抽样,去重保序
    if n <= args.pages:
        idx = list(range(n))
    else:
        picks = {0, n - 1}
        step = max(1, n // max(1, args.pages - 1))
        picks.update(range(0, n, step))
        idx = sorted(picks)[: args.pages]

    r0 = doc[0].rect
    print(f"📄 {base}.pdf  ·  共 {n} 页  ·  页面 {r0.width:.0f}×{r0.height:.0f} pt "
          f"({'A4纵' if abs(r0.width-595)<5 else 'Letter纵' if abs(r0.width-612)<5 else '自定义'})")

    saved, warns = [], []
    mtx = fitz.Matrix(args.zoom, args.zoom)
    for i in idx:
        page = doc[i]
        png = os.path.join(outdir, f"{base}_p{i+1:03d}.png")
        page.get_pixmap(matrix=mtx).save(png)
        saved.append(png)
        # 近空白页检测:正文文本字符数极少(非首页)→ 可能是分页留白 / 超高块被孤立
        txt = page.get_text("text").strip()
        if i not in (0,) and len(txt) < 40:
            warns.append(f"  · 第 {i+1} 页正文极少({len(txt)} 字符)——可能是分页留白或超高块被孤立")

    print(f"🖼️  已渲染 {len(saved)} 张验收图 → {outdir}/")
    for p in saved:
        print("     " + p)
    if warns:
        print("⚠️  分页提示:")
        print("\n".join(warns))
    else:
        print("✅ 未检测到明显的近空白页。")
    print("👉 用当前环境的图片查看工具打开上面的 PNG 逐张核对:背景色 / 字体(无豆腐块)/ 区块是否被拦腰截断。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
