#!/usr/bin/env bash
# PreToolUse hook: a hard bound on tool calls per investigation, owned by IssuePilot.
#
# --max-turns alone did not bound a run: in backtest run 39509305739 the model issued
# 5529 empty Bash calls and the session ran 562 s. This hook counts every tool call.
# Past ISSUEPILOT_TOOL_BUDGET calls it refuses tools and tells the agent to write its
# result; ten calls later it stops the session. A Bash call without a command is
# refused (and counted) at once.
#
# The first structured result is sent back once with a checklist, while budget
# remains: in field trial 1 the investigator stopped after a median of 8.5 turns and
# left checkable claims as assumptions, and a prompt rule alone did not change that.
# The second result is always accepted, and past the budget the first one is too.

set -u
input="$(cat)"
tool="$(printf '%s' "$input" | jq -r '.tool_name // ""')"
file="${ISSUEPILOT_BUDGET_FILE:-/tmp/issuepilot-tool-calls}"
budget="${ISSUEPILOT_TOOL_BUDGET:-40}"

deny() {
  jq -nc --arg reason "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
  exit 0
}

if [ "$tool" = "StructuredOutput" ]; then
  used=$(cat "$file" 2>/dev/null || echo 0)
  if [ ! -e "$file.checked" ] && [ "$used" -lt $(( budget - 5 )) ]; then
    : > "$file.checked"
    deny "Before you submit, check once, with tool calls where something is missing:
1. The exact error text or names from the issue: did you search the whole repository for them, with no pathspec? Before you say code is outside this repository, list the top level with git show HEAD: and the directory that would hold it.
2. The function you blame: did you read all of it, every branch to its end?
3. A traceback or version in the issue from another commit: did you read that version with git show <commit>:<path>?
4. The code your fix changes: did you check every caller, and the comment and commit behind any line you propose to remove or revert?
5. Anything in uncertainty or assumptions that one Read or git grep would settle: check it now.
6. The first evidence item: is it the code that has to change?
Do what is missing, then submit again. If everything was done, submit the same result again."
  fi
  exit 0
fi

count=$(( $(cat "$file" 2>/dev/null || echo 0) + 1 ))
echo "$count" > "$file"

if [ "$count" -gt $(( budget + 10 )) ]; then
  jq -nc '{continue: false, stopReason: "IssuePilot tool-call budget exhausted"}'
  exit 0
fi
if [ "$count" -gt "$budget" ]; then
  deny "Tool-call budget exhausted. Do not call any more tools: return the structured result now with the evidence you have, and say in uncertainty what you could not check."
fi
if [ "$tool" = "Bash" ] && [ -z "$(printf '%s' "$input" | jq -r '.tool_input.command // "" | gsub("\\s"; "")')" ]; then
  deny "Bash was called without a command. Give the command to run, or return your result."
fi
exit 0
