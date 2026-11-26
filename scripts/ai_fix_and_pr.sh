#!/usr/bin/env bash
# scripts/ai_fix_and_pr.sh - AI model se violations fix karwata hai aur GitHub par PR create karta hai
set -uo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://192.168.10.44:11434}"
MODEL="${AI_REVIEW_MODEL:-nestjs-dev}"
GITHUB_REPO="${GITHUB_REPO:-HappyGujjars/user-service}"
TARGET_BRANCH="${TARGET_BRANCH:-${BRANCH_NAME:-stage}}"
BUILD_NUM="${BUILD_NUMBER:-$(date +%s)}"
GIT_TOKEN="${GIT_TOKEN:-}"
TIMEOUT="${AI_FIX_TIMEOUT:-300}"
REVIEW_FILE="${AI_REVIEW_OUT:-ai-review.md}"
CRITICAL_FILE="ai-review-critical.txt"

echo "=================================================="
echo "🤖 Starting AI Auto-Fix & PR Generator"
echo "=================================================="

# 1. Check critical issues
if [ ! -f "$CRITICAL_FILE" ]; then
  echo "ℹ️ No ${CRITICAL_FILE} found. Skipping auto-fix."
  exit 0
fi

CRITICAL_COUNT=$(cat "$CRITICAL_FILE" 2>/dev/null | tr -d ' ' || echo "0")
if [ "$CRITICAL_COUNT" -eq 0 ]; then
  echo "✅ No Critical violations found (count is 0). No PR needed."
  exit 0
fi

echo "⚠️ Found ${CRITICAL_COUNT} Critical violation(s). Proceeding with Auto-Fix..."

# 2. Check GitHub Token
if [ -z "$GIT_TOKEN" ]; then
  echo "⚠️ Warning: GIT_TOKEN is empty. Cannot push branch or create PR."
  exit 0
fi

# 3. Check Ollama connectivity
if ! curl -sf --max-time 10 "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
  echo "⚠️ Warning: Ollama server at ${OLLAMA_URL} is unreachable. Skipping auto-fix."
  exit 0
fi

# 4. Parse files with violations from ai-review.md
FILES_TO_FIX=()
if [ -f "$REVIEW_FILE" ]; then
  while IFS= read -r line; do
    # Extract filename from "## `src/...`"
    if [[ "$line" =~ ^##\ \`([^\`]+)\` ]]; then
      CURRENT_FILE="${BASH_REMATCH[1]}"
    fi
    # Check if section has [Critical]
    if [[ "$line" =~ \[Critical\] ]] && [ -n "${CURRENT_FILE:-}" ]; then
      if [[ ! " ${FILES_TO_FIX[*]:-} " =~ " ${CURRENT_FILE} " ]]; then
        FILES_TO_FIX+=("$CURRENT_FILE")
      fi
    fi
  done < "$REVIEW_FILE"
fi

if [ ${#FILES_TO_FIX[@]} -eq 0 ]; then
  echo "ℹ️ No specific files with [Critical] identified. Skipping."
  exit 0
fi

echo "Files to remediate: ${FILES_TO_FIX[*]}"

# 5. Fix each file using AI model
SYSTEM_FIX_PROMPT=$(cat <<'EOF'
You are an expert NestJS & TypeScript software security engineer.
Fix ALL reported security vulnerabilities and violations in the provided file.
Strict Guidelines:
1. Output ONLY the complete, raw, ready-to-save TypeScript file content.
2. Do NOT output markdown code fences (no ```typescript or ```).
3. Do NOT provide conversational explanations, greetings, or notes.
4. Strictly preserve original business logic, imports, class structure, and function signatures.
EOF
)

MODIFIED_FILES=()

for FILE in "${FILES_TO_FIX[@]}"; do
  [ -f "$FILE" ] || continue
  echo "🔧 AI is generating fix for: ${FILE}..."

  ORIGINAL_CONTENT=$(cat "$FILE")
  
  # File specific review extract
  FILE_REVIEW=$(awk "/## \`$(echo "$FILE" | sed 's/\//\\\//g')\`/{flag=1;next}/## \`/{flag=0}flag" "$REVIEW_FILE" 2>/dev/null || echo "")

  REQUEST=$(jq -n \
    --arg model "$MODEL" \
    --arg sys "$SYSTEM_FIX_PROMPT" \
    --arg user "File: ${FILE}
Findings to fix:
${FILE_REVIEW}

Current Code:
${ORIGINAL_CONTENT}" '{
      model: $model,
      stream: false,
      options: { temperature: 0.1, num_ctx: 8192 },
      messages: [
        { role: "system", content: $sys },
        { role: "user", content: $user }
      ]
    }')

  RESPONSE=$(curl -s --max-time "$TIMEOUT" "${OLLAMA_URL}/api/chat" -d "$REQUEST" 2>/dev/null \
    | jq -r '.message.content // empty' 2>/dev/null || true)

  if [ -n "$RESPONSE" ]; then
    # Strip any accidental ``` markdown fences if model generated them
    CLEANED_CODE=$(echo "$RESPONSE" | sed -E 's/^```(typescript|ts|javascript|js)?//g' | sed -E 's/^```$//g')
    
    # Basic sanity check: ensure file is not empty and has minimum content
    if [ ${#CLEANED_CODE} -gt 50 ]; then
      echo "$CLEANED_CODE" > "$FILE"
      MODIFIED_FILES+=("$FILE")
      echo "✅ Fix applied to ${FILE}"
    else
      echo "⚠️ Fix for ${FILE} was too small or empty. Skipped."
    fi
  else
    echo "⚠️ No response from model for ${FILE}."
  fi
done

# 6. Check if any file was actually modified in Git
DIFF_STATUS=$(git status --porcelain 2>/dev/null || true)
if [ -z "$DIFF_STATUS" ]; then
  echo "ℹ️ No file changes detected after AI remediation. Skipping PR creation."
  exit 0
fi

# 7. Create Git branch and push changes
BRANCH_NAME="ai-fix/build-${BUILD_NUM}-$(date +%s)"
echo "🌿 Creating Git branch: ${BRANCH_NAME}..."

git config user.name "AI Remediation Bot"
git config user.email "ai-bot@jenkins.local"

git checkout -b "$BRANCH_NAME"
git add "${FILES_TO_FIX[@]}" 2>/dev/null || git add -u
git commit -m "fix(security): automated AI remediation for build #${BUILD_NUM}"

PUSH_URL="https://x-access-token:${GIT_TOKEN}@github.com/${GITHUB_REPO}.git"

echo "🚀 Pushing branch ${BRANCH_NAME} to remote..."
if ! git push "$PUSH_URL" "$BRANCH_NAME" > /dev/null 2>&1; then
  echo "❌ Error: Failed to push branch ${BRANCH_NAME} to GitHub."
  exit 0
fi
echo "✅ Branch pushed successfully."

# 8. Create GitHub Pull Request via REST API
echo "📬 Opening Pull Request towards ${TARGET_BRANCH}..."

PR_TITLE="🤖 [AI Auto-Fix] Security Remediation for Build #${BUILD_NUM}"
PR_BODY=$(cat <<EOF
## 🤖 Automated Security Remediation
This Pull Request was automatically created by **Jenkins AI Review & Remediation Bot** using the local **${MODEL}** model.

### 📋 Addressed Critical Violations:
Build #${BUILD_NUM} on branch \`${TARGET_BRANCH}\` detected **${CRITICAL_COUNT}** critical violations.

### 📁 Modified Files:
$(for f in "${MODIFIED_FILES[@]}"; do echo "- \`$f\`"; done)

---
*Please review the diff and run tests before merging into \`${TARGET_BRANCH}\`.*
EOF
)

PR_PAYLOAD=$(jq -n \
  --arg title "$PR_TITLE" \
  --arg head "$BRANCH_NAME" \
  --arg base "$TARGET_BRANCH" \
  --arg body "$PR_BODY" \
  '{title: $title, head: $head, base: $base, body: $body}')

API_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer ${GIT_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${GITHUB_REPO}/pulls" \
  -d "$PR_PAYLOAD")

PR_URL=$(echo "$API_RESPONSE" | jq -r '.html_url // empty')

if [ -n "$PR_URL" ] && [ "$PR_URL" != "null" ]; then
  echo "=================================================="
  echo "🎉 SUCCESS: Pull Request created successfully!"
  echo "🔗 PR URL: ${PR_URL}"
  echo "=================================================="
  echo "$PR_URL" > ai-pr-url.txt
else
  ERROR_MSG=$(echo "$API_RESPONSE" | jq -r '.message // "Unknown error"')
  echo "⚠️ Notice: PR creation returned: ${ERROR_MSG}"
  echo "$API_RESPONSE"
fi

exit 0
