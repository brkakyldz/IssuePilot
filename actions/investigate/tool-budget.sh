#!/usr/bin/env bash
# PreToolUse hook: a hard bound on tool calls per investigation, owned by IssuePilot.
#
# --max-turns alone did not bound a run: in backtest run 39509305739 the model issued
# 5529 empty Bash calls and the session ran 562 s. This hook counts every tool call.
# Past ISSUEPILOT_TOOL_BUDGET calls it refuses tools and tells the agent to write its
# result; ten calls later it stops the session. The structured result itself is never
# refused, and a Bash call without a command is refused (and counted) at once.

set -u
input="$(cat)"
tool="$(printf '%s' "$input" | jq -r '.tool_name // ""')"
[ "$tool" = "StructuredOutput" ] && exit 0

file="${ISSUEPILOT_BUDGET_FILE:-/tmp/issuepilot-tool-calls}"
budget="${ISSUEPILOT_TOOL_BUDGET:-40}"
count=$(( $(cat "$file" 2>/dev/null || echo 0) + 1 ))
echo "$count" > "$file"

deny() {
  jq -nc --arg reason "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
  exit 0
}

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
