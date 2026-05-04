# Repo A Human Verification Left

Implementation target: `/home/przemek/Nauka/prudentia`

Plan source: `plans/repo-a-production-shaped-mvp.md`

## Current Automated Evidence

- Gate passed: `make gate`
- Native CLI smoke passed through create, generate all, validate, simulate, report, approve, student export, teacher export, and status
- Docker validation/simulation passed with run metadata showing Docker mode, network disabled, and read-only workspace copy
- Independent agent verification found no remaining blocking findings after fixes

## Human Must Verify Before Handoff

1. Live Codex workspace-write environment
   - Live Codex auth/model access works in read-only mode.
   - Prudentia reaches the real Codex CLI.
   - Workspace-write generation is still blocked locally by Codex sandbox failure: `bwrap: Unknown option --perms`.
   - Human should fix or update the local Codex/bubblewrap environment, then rerun:

   ```bash
   prudentia create --title "Live Codex smoke" --course CS101 --topic "strings and functions" --difficulty beginner
   prudentia generate --brief --use-codex --workspace ./live-codex-smoke --json
   ```

   Expected after environment fix: task status is `succeeded`, expected artifacts exist, and changed files stay inside allowed write globs.

2. Teacher semantic review of exports
   - Scanner allowlists and marker checks are automated.
   - Human should still open both ZIPs and confirm student export has no semantic solution leaks.
   - Confirm teacher export contains useful teaching artifacts and no credentials or local-only run data.

3. Docker image provenance
   - Current evidence uses local tag `prudentia-pytest:3.12`.
   - Human should decide whether MVP handoff accepts a local tag or needs a pinned digest/build attestation.

4. Real browser UI smoke
   - CLI/API paths are tested.
   - Human should launch `prudentia ui`, create or open a workspace, run Generate All, approve artifacts, and try both export buttons.
   - Confirm blocked export errors are understandable before approval and validation.

5. Packaging/install on a clean machine
   - Current checks use an existing Python environment.
   - Human should verify install from a clean checkout:

   ```bash
   python -m pip install -e .
   prudentia doctor
   ```

## Residual Risks To Accept Or Fix

- Live Codex end-to-end workspace-write generation remains unverified until the local sandbox issue is resolved.
- Export scanner cannot prove absence of semantic solution hints; teacher review remains required.
- Docker sandbox depends on the local Docker daemon and local image tag.
- The MVP is local-first and has no auth, cloud sync, database, LMS integration, or multi-language support by design.
