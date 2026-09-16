#!/usr/bin/env bash
# Markdown → 中文工作文档 PDF。使用本目录的 zh-doc.css。
# 用法: md_zh.sh 输入.md [输出.pdf] [--palette nude|cream]
# nude: 裸粉×桃红×橄榄绿；cream: 蛋壳×朱红×钴蓝。
# pandoc 生成 HTML 结构，CSS 内联，Chrome/Chromium 负责打印。

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSS="$HERE/zh-doc.css"

PALETTE=nude
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --palette) PALETTE="${2:?--palette 后面要跟 nude 或 cream}"; shift 2 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- "${ARGS[@]}"

IN="${1:?用法: md_zh.sh 输入.md [输出.pdf] [--palette nude|cream]}"
OUT="${2:-${IN%.*}.pdf}"
[ -f "$IN" ] || { echo "✗ 找不到输入文件：$IN" >&2; exit 1; }
[ -f "$CSS" ] || { echo "✗ 找不到样式表：$CSS" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

TITLE="$(basename "${IN%.*}")"

# 1) pandoc 只出结构（不要 --standalone，样式我们自己给）
pandoc "$IN" -o "$TMP/body.html" --wrap=none

# 2) CSS 内联进 HTML —— 不用外链，Chrome 无网也能完整渲染
python3 - "$TMP/body.html" "$CSS" "$TMP/doc.html" "$TITLE" "$PALETTE" <<'PY'
import html, io, sys
body, css, out, title, palette = sys.argv[1:6]
b = io.open(body, encoding='utf-8').read()
c = io.open(css,  encoding='utf-8').read()

# 色板覆盖：只重定义 :root 变量，样式规则一行不动。
# cream 使用奶油底色、朱红和钴蓝。
PALETTES = {
    'nude': '',
    'cream': """:root{
  --paper:#FBF4E4; --ink:#1C1A17; --accent:#C8322A; --accent2:#1B4D8F;
  --muted:#7A736A; --muted2:#4A443C; --quote:#6E675E; --quote-em:#7A736A;
  --em:#A62A22; --code-bg:#F2E9D4; --pre-bg:#F6EFDD; --code-fg:#3A352E;
  --pre-fg:#2C2822; --rule:#DED3B8; --rule2:#C9BC9C; --rule3:#D6C9AC;
  --link:#1B4D8F; --link-line:#9FB6D4;
}""",
}
if palette not in PALETTES:
    sys.exit(f'✗ 未知色板：{palette}（可选 {"/".join(PALETTES)}）')
c += '\n' + PALETTES[palette]
io.open(out, 'w', encoding='utf-8').write(
    f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
    f'<title>{html.escape(title)}</title><style>{c}</style></head><body>{b}</body></html>')
PY

# 3) 交给 ks-anything-to-pdf 的 HTML 路径
#    --keep 只给这几类：整表 avoid 会把装不下的表推到下一页、留半页空白，
#    表格的分页在 CSS 里按「行不拆断 + 表头重复」处理了。
python3 "$HERE/to_pdf.py" "$TMP/doc.html" -o "$OUT" \
    --keep "pre,blockquote,h2,h3" \
    --size A4 --margin "15mm 14mm 16mm"
