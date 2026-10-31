#!/usr/bin/env bash
# 深度研究报告拼接器（deep-research-report 配套）
# 用法1: assemble.sh <parts目录> <输出文件>                          # 目录内全部*.md按文件名排序
# 用法2: assemble.sh <parts目录> <输出文件> header.md module1.md ... # 显式顺序（推荐，可控）
# 依赖: bash 4+（Git Bash 自带）
set -euo pipefail

PARTS="${1:?用法: assemble.sh <parts目录> <输出文件> [文件...]}"
OUT="${2:?缺少输出文件路径}"
shift 2 || true

if [ $# -gt 0 ]; then
  FILES=("$@")
else
  mapfile -t FILES < <(ls "$PARTS"/*.md | sort)
fi

: > "$OUT"
for i in "${!FILES[@]}"; do
  f="${FILES[$i]}"
  case "$f" in /*) ;; *) f="$PARTS/$f" ;; esac
  [ -f "$f" ] || { echo "错误: 分片不存在: $f" >&2; exit 1; }
  [ "$i" -gt 0 ] && printf '\n\n---\n\n' >> "$OUT"
  cat "$f" >> "$OUT"
done

echo "已拼接 ${#FILES[@]} 个分片 -> $OUT"
wc -l -c "$OUT"
