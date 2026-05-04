# Security policy

## Local execution risks

Prudentia runs locally on the teacher's machine. Generated code is untrusted until reviewed. The default test runner uses Docker with `--network none`, an ephemeral workspace copy mounted read-only, and result writes isolated under `.prudentia/runs/<run-id>/`. Native pytest execution is available only through `--allow-native-execution` or the UI advanced setting.

Native execution can still run arbitrary generated Python code on the host. Use it only when Docker is unavailable and the workspace is trusted enough for local execution.

## Credential boundaries

Prudentia does not request or collect:

- OpenAI API keys
- ChatGPT passwords
- session cookies
- OAuth tokens
- `~/.codex/auth.json`

The Codex readiness check only verifies whether a local SDK import or `codex` executable is available. Prudentia writes only project-scoped `.codex/config.toml` defaults inside the assignment workspace and never modifies global Codex configuration.

## Export gates and scanner guarantees

Student and teacher exports are blocked until all reviewable artifacts are approved and validation has passed. Blocked attempts write local export manifests so teachers can audit why packaging was denied.

Student export uses an allowlist and blocks:

- `solution/**`
- `tests/hidden/**`
- `simulations/**`
- `reports/**`
- `exports/**`
- `.prudentia/**`
- `.codex/**`
- obvious leak markers such as `REFERENCE SOLUTION`, references to instructor-only checks, and solution paths

Teacher export excludes `.codex/**`, export folders, action logs, context manifests, OS temp files, Python caches, and credential-like content such as `OPENAI_API_KEY`, `sk-...`, session-token markers, `auth.json`, and bearer-token strings.

The scanner is intentionally conservative. It reduces common leakage risks but does not prove that prose or code has no semantic solution hints. Teachers should review every export before distribution.

## Logs and manifests

Action logs are local JSONL files under `.prudentia/action_log.jsonl`. Secret-like strings are redacted before logging. Context manifests and export manifests remain local to the workspace.

## Reporting issues

For the MVP repository, report security issues privately to the repository maintainer or project owner before public disclosure. Include reproduction steps, affected files, and whether the issue can leak credentials, execute code outside the workspace, or put teacher-only artifacts in a student export.
