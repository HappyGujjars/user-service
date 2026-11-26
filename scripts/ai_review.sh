#!/usr/bin/env bash
# scripts/ai_review.sh - PR diff ya full codebase ko local nestjs-dev model (Ollama) se review karwata hai
set -uo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://192.168.10.44:11434}"
MODEL="${AI_REVIEW_MODEL:-nestjs-dev}"
TARGET_BRANCH="${CHANGE_TARGET:-stage}"
OUT_FILE="${AI_REVIEW_OUT:-ai-review.md}"
MAX_CHARS="${AI_REVIEW_MAX_CHARS:-12000}"   # ~3-4k tokens per file
BLOCKING="${AI_REVIEW_BLOCKING:-false}"
TIMEOUT="${AI_REVIEW_TIMEOUT:-300}"         # seconds per file
REVIEW_ALL="${AI_REVIEW_ALL:-true}"         # First time ya empty diff par poora src/ review karein

SYSTEM_PROMPT=$(cat <<'EOF'
You are a Senior NestJS reviewer enforcing the pro-architect rules:
zero any, Zod-only DTOs with custom error messages, GenericDbFactory for all DB access,
mappers before returning data, Symbol-token DI, typed env (no process.env),
{table}_id primary keys, Logger with traffic-light scheme, full Swagger decorators.
Review ONLY the code in the given snippet/file. Output exactly these sections:
❌ VIOLATIONS - one line each: [Critical|Major|Minor] file:line - problem
✅ WHAT IS GOOD
🔧 FIXES - short corrected snippets
If there are no violations write: ❌ VIOLATIONS: none
Never invent code that is not in the provided snippet.
EOF
)

echo "# AI Code Review (${MODEL})" > "$OUT_FILE"
echo "" >> "$OUT_FILE"

# 1. Server down ho to build mat todo
if ! curl -sf --max-time 10 "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
  echo "> AI review skipped: ${OLLAMA_URL} reachable nahi hai." >> "$OUT_FILE"
  echo "WARN: Ollama unreachable at ${OLLAMA_URL}, skipping AI review"
  echo 0 > ai-review-critical.txt
  exit 0
fi

# 2. Files list gather karna
FILES=()

if [ "$REVIEW_ALL" != "true" ]; then
  # Target branch fetch karo, badli hui .ts files nikalo
  git fetch --no-tags origin "+refs/heads/${TARGET_BRANCH}:refs/remotes/origin/${TARGET_BRANCH}" > /dev/null 2>&1 || true

  while IFS= read -r file; do
    [ -n "$file" ] && FILES+=("$file")
  done < <(git diff --name-only --diff-filter=AM "origin/${TARGET_BRANCH}...HEAD" -- '*.ts' 2>/dev/null \
    | grep -vE '(^|/)(dist|node_modules|migrations)/|\.d\.ts$' || true)
fi

# Agar REVIEW_ALL=true ho YA diff me koi file na mili ho, to full src/ directory scan karein
if [ ${#FILES[@]} -eq 0 ]; then
  echo "ℹ️ Notice: No diff found or full review requested. Scanning all .ts files under src/..."
  while IFS= read -r file; do
    [ -n "$file" ] && FILES+=("$file")
  done < <(find src -type f -name '*.ts' ! -name '*.spec.ts' ! -name '*.d.ts' 2>/dev/null | sort)
fi

if [ ${#FILES[@]} -eq 0 ]; then
  echo "Koi .ts file nahi mili, review skip." >> "$OUT_FILE"
  echo 0 > ai-review-critical.txt
  exit 0
fi

echo "Found ${#FILES[@]} files to review."

# 3. Har file ka content ya diff alag review karo
CRITICAL_TOTAL=0
for FILE in "${FILES[@]}"; do
  [ -f "$FILE" ] || continue

  DIFF=""
  if [ "$REVIEW_ALL" != "true" ]; then
    DIFF=$(git diff -U5 "origin/${TARGET_BRANCH}...HEAD" -- "$FILE" 2>/dev/null || true)
  fi

  LABEL="File diff"
  if [ -z "$DIFF" ]; then
    DIFF=$(cat "$FILE")
    LABEL="Full file content"
  fi

  if [ ${#DIFF} -gt "$MAX_CHARS" ]; then
    DIFF="${DIFF:0:$MAX_CHARS}
... [code truncated to fit context window: first 12,000 characters reviewed]"
  fi

  echo "Analyzing ${FILE} (${LABEL})..."

  REQUEST=$(jq -n --arg model "$MODEL" --arg sys "$SYSTEM_PROMPT" \
    --arg user "File: ${FILE} (${LABEL})

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
echo "AI review done: ${#FILES[@]} files, ${CRITICAL_TOTAL} Critical violations"

# 4. Blocking mode mein hi fail karo
if [ "$BLOCKING" = "true" ] && [ "$CRITICAL_TOTAL" -gt 0 ]; then
  exit 2
fi
exit 0
