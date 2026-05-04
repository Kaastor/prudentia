# Sandboxing and test execution

Generated Python code is untrusted. Prudentia's test-runner boundary always executes against an ephemeral workspace copy and never directly against the source workspace.

## Docker default

Production validation prefers Docker. The Docker command mounts the ephemeral run copy read-only, disables network access with `--network none`, writes result files only under `.prudentia/runs/<run-id>/`, and records command metadata.

Before running the container, the runner checks that the expected local image exists and uses `--pull never` so validation does not implicitly fetch or substitute an image.

Build the default image with:

```bash
docker build -f docker/prudentia-pytest.Dockerfile -t prudentia-pytest:3.12 .
```

## Native escape hatch

Native mode is explicit:

```bash
prudentia validate --allow-native-execution
prudentia simulate --allow-native-execution
prudentia generate --all --allow-native-execution
```

Native mode stages the selected solution or simulated submission into an ephemeral workspace copy and runs pytest there. It captures stdout, stderr, exit code, pytest JSON, and run metadata. It still executes generated Python on the host process, so it is less safe than Docker.

## Run record shape

```text
.prudentia/runs/<run-id>/
  workspace-copy/
  stdout.txt
  stderr.txt
  exit_code.txt
  pytest_report.json
  run_metadata.json
```

## Source workspace protection

The source workspace is copied before test execution. The runner stages submissions only inside `workspace-copy/`. Generated `__pycache__`, `.pytest_cache`, and test-side writes remain inside the run directory.
