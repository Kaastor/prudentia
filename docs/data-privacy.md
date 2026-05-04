# Data privacy

Prudentia MVP is local-first. It does not require a Prudentia cloud account and does not centralize assignment content.

## Local data

Assignment content, reports, run outputs, logs, manifests, and exports are stored in the workspace folder. Teachers can inspect, copy, archive, or delete the folder directly.

## Codex context transparency

Before a Codex task, Prudentia creates a context manifest containing:

- schema version
- manifest ID
- workspace ID
- task kind
- included files
- file role
- reason for inclusion
- excluded globs
- allowed write globs
- privacy warnings

The MVP never includes export folders, action logs, or report folders in Codex context by default.

## No real student data

The `simulations/` folder contains generated fake submissions only. The UI and reports call them simulated submissions, not real student submissions. Real submission grading is explicitly out of scope.

## Credential handling

Prudentia never asks for OpenAI credentials or ChatGPT login details. It does not read global Codex auth files. Codex setup remains an external local workflow controlled by the teacher.
