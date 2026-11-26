#!/usr/bin/env bash
# scripts/ai_review.sh - PR diff ko local nestjs-dev model (Ollama) se review karwata hai
set -uo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://192.168.10.44:11434}"
MODEL="${AI_REVIEW_MODEL:-nestjs-dev}"
TARGET_BRANCH="${CHANGE_TARGET:-stage}"
OUT_FILE="${AI_REVIEW_OUT:-ai-review.md}"
MAX_CHARS="${AI_REVIEW_MAX_CHARS:-12000}"   # ~3-4k tokens per file
BLOCKING="${AI_REVIEW_BLOCKING:-false}"
TIMEOUT="${AI_REVIEW_TIMEOUT:-300}"         # seconds per file

SYSTEM_PROMPT=$(cat <<'EOF'
You are a Senior NestJS reviewer enforcing the pro-architect rules:
zero any, Zod-only DTOs with custom error messages, GenericDbFactory for all DB access,
mappers before returning data, Symbol-token DI, typed env (no process.env),
{table}_id primary keys, Logger with traffic-light scheme, full Swagger decorators.
Review ONLY the code in the given diff. Output exactly these sections:
❌ VIOLATIONS - one line each: [Critical|Major|Minor] file:line - problem
✅ WHAT IS GOOD
🔧 FIXES - short corrected snippets
If there are no violations write: ❌ VIOLATIONS: none
Never invent code that is not in the diff.
EOF
)

echo "# AI Review (${MODEL})" > "$OUT_FILE"
echo "" >> "$OUT_FILE"

# 1. Server down ho to build mat todo
if ! curl -sf --max-time 10 "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
  echo "> AI review skipped: ${OLLAMA_URL} reachable nahi hai." >> "$OUT_FILE"
  echo "WARN: Ollama unreachable at ${OLLAMA_URL}, skipping AI review"
  echo 0 > ai-review-critical.txt
  exit 0
fi

# 2. Target branch fetch karo, badli hui .ts files nikalo
git fetch --no-tags origin "+refs/heads/${TARGET_BRANCH}:refs/remotes/origin/${TARGET_BRANCH}" > /dev/null 2>&1 || true

# Portable diff file list
FILES=()
while IFS= read -r file; do
  [ -n "$file" ] && FILES+=("$file")
done < <(git diff --name-only --diff-filter=AM "origin/${TARGET_BRANCH}...HEAD" -- '*.ts' 2>/dev/null \
  | grep -vE '(^|/)(dist|node_modules|migrations)/|\.d\.ts$' || true)

# Agar PR diff empty hai to last commit ka diff check karo (fallback for testing)
if [ ${#FILES[@]} -eq 0 ]; then
  while IFS= read -r file; do
    [ -n "$file" ] && FILES+=("$file")
  done < <(git diff --name-only --diff-filter=AM HEAD~1 HEAD -- '*.ts' 2>/dev/null \
    | grep -vE '(^|/)(dist|node_modules|migrations)/|\.d\.ts$' || true)
fi

if [ ${#FILES[@]} -eq 0 ]; then
  echo "Koi .ts file nahi badli, review skip." >> "$OUT_FILE"
  echo 0 > ai-review-critical.txt
  exit 0
fi

# 3. Har file ka diff alag review karo
CRITICAL_TOTAL=0
for FILE in "${FILES[@]}"; do
  DIFF=$(git diff -U5 "origin/${TARGET_BRANCH}...HEAD" -- "$FILE" 2>/dev/null || git diff -U5 HEAD~1 HEAD -- "$FILE" 2>/dev/null || true)
  if [ -z "$DIFF" ]; then
    continue
  fi

  if [ ${#DIFF} -gt "$MAX_CHARS" ]; then
    DIFF="${DIFF:0:$MAX_CHARS}
... [diff truncated: sirf pehla hissa review hua]"
  fi

  REQUEST=$(jq -n --arg model "$MODEL" --arg sys "$SYSTEM_PROMPT" \
    --arg user "File: ${FILE}

${DIFF}" '{
      model: $model, stream: false,
      options: { temperature: 0.1, num_ctx: 8192 },
      messages: [ {role: "system", content: $sys}, {role: "user", content: $user} ]
    }')

  RESPONSE=$(curl -s --max-time "$TIMEOUT" "${OLLAMA_URL}/api/chat" -d "$REQUEST" 2>/dev/null \
    | jq -r '.message.content // empty' 2>/dev/null || true)

  {
    echo "## \`${FILE}\`"
    echo ""
    if [ -n "$RESPONSE" ]; then echo "$RESPONSE"; else echo "> Model ne jawab nahi diya (timeout?)."; fi
    echo ""
  } >> "$OUT_FILE"

  COUNT=$(printf '%s' "$RESPONSE" | grep -c '\[Critical\]' || true)
  CRITICAL_TOTAL=$((CRITICAL_TOTAL + COUNT))
done

echo "$CRITICAL_TOTAL" > ai-review-critical.txt
echo "AI review done: ${#FILES[@]} files, ${CRITICAL_TOTAL} Critical"

# 4. Blocking mode mein hi fail karo
if [ "$BLOCKING" = "true" ] && [ "$CRITICAL_TOTAL" -gt 0 ]; then
  exit 2
fi
exit 0
