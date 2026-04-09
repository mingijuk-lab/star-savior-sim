# Skill: Secure Terminal Execution (Claude-Style)

## Context
Use this skill when running shell commands, especially complex ones involving find, xargs, or pipes. This skill is inspired by Claude's BashTool security protocols.

## Instructions
1. **Command Review**: Before running, check for shell injection risks (e.g., `;`, `&&`, or backticks in user-provided strings).
2. **Path Absolute-ness**: Prefer absolute paths or clear relative paths from the workspace root.
3. **Multi-step Execution**: Break down long pipe chains into separate commands to verify intermediate results if the task is complex.
4. **Safety Check**: Never run `rm -rf` on any directory without listing its contents first.

## Examples
### Safe finding and reading
Instead of: `find . -name "*.js" | xargs grep "api"`
Use: `find . -maxdepth 2 -name "*.js"` followed by targeted `grep` to ensure the scope is correct.

## Pre-execution Verification
- Ask yourself: "Does this command have any side effects I haven't accounted for?"
- If the command is destructive, provide a dry-run first or ask for explicit confirmation in the thought block.
