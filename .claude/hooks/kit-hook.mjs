#!/usr/bin/env node
// Runs one of the maintainer's agent-kit hooks (commit-gate, test-gate, holdout-lock,
// run-fence) when that kit is installed on this machine, and does nothing otherwise.
// A clone without the kit gets no hook errors and no gates; the gates' configs in
// .claude/*.json still document what the maintainer runs before a commit.
//
// Usage from .claude/settings.json:  node "${CLAUDE_PROJECT_DIR}/.claude/hooks/kit-hook.mjs" commit-gate
import { existsSync, realpathSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const name = process.argv[2] || "";
if (!/^[a-z-]+$/.test(name)) process.exit(0);

// The kit is found through its installed `ship` skill: ~/.claude/skills/ship links into it.
let kit = process.env.AGENT_KIT || "";
if (!kit) {
  try {
    kit = path.resolve(realpathSync(path.join(os.homedir(), ".claude", "skills", "ship")), "..", "..");
  } catch {
    process.exit(0);
  }
}
const hook = path.join(kit, "hooks", `${name}.mjs`);
if (!existsSync(hook)) process.exit(0);
await import(pathToFileURL(hook).href);
