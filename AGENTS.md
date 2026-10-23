## 2026-10-23 — PowerBox now has its own R3 repository

Canonical project: [GLL R3 PowerBox](https://github.com/druzvv-hash/r3-powerbox),
branch **main**, local **C:/Projects/r3-powerbox**. Its README distinguishes Rev.A,
Rev.B candidate and user-reported physical checks. Existing hardware files were
copied byte-for-byte; PowerBox history was filtered with an original/new commit
map. Previously local RevB/manufacturing evidence is now tracked privately.
No circuit change, new hardware test or manufacturing approval is implied.
The old r3-powerbox-routing worktree and R1 branch remain historical references;
do not start new PowerBox development there. This supersedes older location and
local-only status below. See the new repository's docs/MIGRATION_2026-10-23.md.

## External project memory audit - 2026-10-23

This is the durable technical memory for Astra/ChatGPT, not device storage.
At the start of every new task or after context loss, read this AGENTS.md,
NOTES.md, the newest relevant WORK_REPORT.md entry and docs/PROJECT_MEMORY.md;
check the actual branch, HEAD and dirty state before relying on older reports.
If accessible, also read C:/Projects/AGENTS.md and C:/Projects/PROJECT_MEMORY.md.
If those workspace files are unavailable, use the repository files and explicit
GitHub branch/ref links; do not assume another chat's context was loaded.

After EACH substantial milestone, update the current NOTES summary and add a
dated WORK_REPORT entry with changes, exact evidence/test scope, failures,
deployment status, unresolved issues and next steps. Update affected canonical
docs/README and the workspace index when its facts change. Preserve history;
mark superseded conclusions rather than silently erasing them. Record commit/push
and backup status in the final handoff. Commit only the intended files and respect
the user's authorization; no secrets, private captures or raw device dumps.
Memory updates occur during authorized work; no unattended two-way sync exists.

# External-memory bootstrap

Before substantial work: read NOTES.md, then the newest relevant WORK_REPORT.md
entries and git status/log; follow only relevant detailed links and inspect code.
After work checkpoint decisions, failures, evidence scope and deployment status.
Do not infer physical acceptance from a build or historical claims. Preserve
private evidence, owner changes and existing documentation. General policy:
C:/Projects/AGENTS.md. Owner instructions: existing Ukrainian docs/README links.

Project-specific constraints and sibling dependencies: NOTES.md.

## Owner manual

For changes to user-visible behavior, connections, roles, clocks, files or OTA,
update the relevant page in [the shared manual](../lily-logger-r3/docs/manual/README.uk.md) in the same work item.
Follow its maintenance guide; date evidence and distinguish deployed from planned.
