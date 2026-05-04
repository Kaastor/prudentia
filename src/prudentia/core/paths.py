from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterable


class PathSafetyError(ValueError):
    """Raised when a path would escape the workspace boundary."""


def normalize_workspace_root(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def safe_join(root: Path | str, relative_path: Path | str) -> Path:
    root_path = normalize_workspace_root(root)
    rel = Path(relative_path)
    if rel.is_absolute():
        raise PathSafetyError(f"Absolute paths are not allowed: {relative_path}")
    if any(part == ".." for part in rel.parts):
        raise PathSafetyError(f"Path traversal is not allowed: {relative_path}")
    candidate = (root_path / rel).resolve()
    if not is_within(candidate, root_path):
        raise PathSafetyError(f"Path escapes workspace: {relative_path}")
    return candidate


def is_within(candidate: Path, root: Path) -> bool:
    candidate = candidate.resolve()
    root = root.resolve()
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def relative_to_root(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        pattern = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, pattern):
            return True
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return True
    return False


def iter_files(root: Path, exclude_globs: Iterable[str] = ()) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = relative_to_root(root, path)
        if matches_any(rel, exclude_globs):
            continue
        files.append(path)
    return sorted(files, key=lambda item: relative_to_root(root, item))
