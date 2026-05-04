# Contributing

Prudentia MVP favors boring, typed, local-first code. Keep ownership boundaries narrow:

- CLI should call domain services and avoid duplicating business logic.
- Server routes should orchestrate owned services and return validated contracts.
- Workspace, Codex, validation, runner, simulation, reporting, and export modules should remain separate.
- Do not add databases, queues, cloud sync, auth, LMS integrations, or language adapters for the MVP.

Before submitting changes, run:

```bash
make gate
```

Do not commit run outputs, generated ZIP exports, local credentials, cache directories, virtual environments, or machine-specific paths.
