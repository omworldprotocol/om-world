#!/usr/bin/env bash
# setup_shell_env.sh — 把 OMW env 持久化到 ~/.zshrc(idempotent)
#
# 目的:让所有 shell session 默认能用 OMW SDK + omw CLI + overlay 加载 public+private patterns。
#
# 安全特性:
#   - idempotent:有 BEGIN/END 块标记,重复跑只更新块内,不重复 append
#   - dry-run 模式预览不写
#   - 自动 backup .zshrc 到 .zshrc.omw-bak-<timestamp>
#   - 检测 om-world-private 是否存在,自动构造 overlay path
#
# 用法:
#   ./tools/setup_shell_env.sh --dry-run    # 预览
#   ./tools/setup_shell_env.sh              # 真写
#   source ~/.zshrc                          # 让当前 shell 立即生效

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

OMW_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OMW_PRIVATE="${OMW_ROOT}/../om-world-private"
OMW_PRIVATE="$(cd "$OMW_PRIVATE" 2>/dev/null && pwd || echo '')"

ZSHRC="$HOME/.zshrc"
BEGIN_MARKER="# >>> OMW env begin (managed by om-world/tools/setup_shell_env.sh) >>>"
END_MARKER="# <<< OMW env end <<<"

# 构造 OMW_PATTERN_PATH(检测私有目录,自动 overlay)
if [[ -n "$OMW_PRIVATE" && -d "$OMW_PRIVATE/patterns" ]]; then
  PATTERN_PATH="\$OMW_ROOT/patterns:$OMW_PRIVATE/patterns"
  echo "📂 detected om-world-private at $OMW_PRIVATE — will overlay"
else
  PATTERN_PATH="\$OMW_ROOT/patterns"
  echo "📂 no om-world-private detected — public-only"
fi

# 要 append 的 env block
read -r -d '' ENV_BLOCK <<EOF || true
$BEGIN_MARKER
export OMW_ROOT="$OMW_ROOT"
export OMW_PATTERN_PATH="$PATTERN_PATH"
export OMW_RUNTIME_PATH="\$OMW_ROOT/runtime"
export OMW_AGENT_ID="\${OMW_AGENT_ID:-shell}"
# omw CLI on PATH
case ":\$PATH:" in
  *":\$OMW_ROOT/tools:"*) ;;
  *) export PATH="\$OMW_ROOT/tools:\$PATH" ;;
esac
$END_MARKER
EOF

echo
echo "=== OMW shell env block to install ==="
echo "$ENV_BLOCK"
echo "=== end of block ==="
echo

if [[ "$DRY_RUN" == "true" ]]; then
  echo "✓ DRY RUN — no changes to $ZSHRC"
  echo "  Run without --dry-run to apply."
  exit 0
fi

# 创建 .zshrc 若不存在
if [[ ! -f "$ZSHRC" ]]; then
  touch "$ZSHRC"
  echo "📝 created empty $ZSHRC"
fi

# 备份
BAK="$ZSHRC.omw-bak-$(date +%Y%m%d%H%M%S)"
cp "$ZSHRC" "$BAK"
echo "💾 backup: $BAK"

# Idempotent:若已有 OMW 块 → 替换;否则 → append
if grep -qF "$BEGIN_MARKER" "$ZSHRC"; then
  echo "🔄 found existing OMW block — replacing"
  python3 -c "
from pathlib import Path
p = Path('$ZSHRC')
text = p.read_text()
begin, end = '''$BEGIN_MARKER''', '''$END_MARKER'''
i = text.find(begin)
j = text.find(end, i) + len(end) if i != -1 else -1
if i != -1 and j != -1:
    new = text[:i] + '''$ENV_BLOCK''' + text[j:]
    p.write_text(new)
"
else
  echo "➕ no existing OMW block — appending"
  {
    echo ""
    echo "$ENV_BLOCK"
    echo ""
  } >> "$ZSHRC"
fi

echo
echo "✅ done. To activate in current shell:"
echo "    source $ZSHRC"
echo
echo "Verify with:"
echo "    echo \$OMW_PATTERN_PATH"
echo "    omw status"
