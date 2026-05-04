from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from prudentia.core.time import utc_now_iso

SCHEMA_VERSION = "0.1"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    NOT_READY = "not_ready"
    READY = "ready"


class TaskKind(StrEnum):
    PLANNING = "planning"
    BRIEF = "brief"
    STARTER = "starter"
    SOLUTION = "solution"
    TESTS = "tests"
    REPAIR = "repair"
    RUBRIC = "rubric"
    SIMULATIONS = "simulations"
    REPORT = "report"
    QUALITY_REVIEW = "quality_review"


class FileRole(StrEnum):
    STUDENT_VISIBLE = "student-visible"
    TEACHER_ONLY = "teacher-only"
    METADATA = "metadata"
    TEST = "test"
    REPORT = "report"


class CourseProfile(BaseModel):
    name: str = Field(min_length=1)
    level: str = "introductory"
    audience: str = "first-year undergraduate"


class LanguageProfile(BaseModel):
    id: Literal["python"] = "python"
    version: str = "3.12"


class TestFrameworkProfile(BaseModel):
    id: Literal["pytest"] = "pytest"
    version_constraint: str = ">=8"


class AssignmentProfile(BaseModel):
    topic: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    estimated_minutes: int = Field(default=45, ge=5, le=600)
    learning_objectives: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)

    @field_validator("learning_objectives", "constraints")
    @classmethod
    def strip_blank_items(cls, items: list[str]) -> list[str]:
        return [item.strip() for item in items if item.strip()]


class Policy(BaseModel):
    ai_context_allowlist: list[str] = Field(
        default_factory=lambda: [
            "brief.md",
            "rubric.md",
            "starter/**",
            "solution/**",
            "tests/**",
            "prudentia.yaml",
        ]
    )
    never_send: list[str] = Field(
        default_factory=lambda: [
            "exports/**",
            ".prudentia/action_log.jsonl",
            "reports/**",
        ]
    )
    student_export_exclude: list[str] = Field(
        default_factory=lambda: [
            "solution/**",
            "tests/hidden/**",
            "reports/**",
            ".prudentia/**",
            ".codex/**",
        ]
    )


class Status(BaseModel):
    brief: ArtifactStatus = ArtifactStatus.DRAFT
    starter: ArtifactStatus = ArtifactStatus.DRAFT
    solution: ArtifactStatus = ArtifactStatus.DRAFT
    tests: ArtifactStatus = ArtifactStatus.DRAFT
    rubric: ArtifactStatus = ArtifactStatus.DRAFT
    validation: ArtifactStatus = ArtifactStatus.NOT_RUN
    export: ArtifactStatus = ArtifactStatus.NOT_READY


class WorkspaceMetadata(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    schema_version: Literal["0.1"] = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    course: CourseProfile
    language: LanguageProfile = Field(default_factory=LanguageProfile)
    test_framework: TestFrameworkProfile = Field(default_factory=TestFrameworkProfile)
    assignment: AssignmentProfile
    policy: Policy = Field(default_factory=Policy)
    status: Status = Field(default_factory=Status)

    @field_validator("id")
    @classmethod
    def id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("workspace id cannot be blank")
        return value

    @field_validator("slug")
    @classmethod
    def slug_is_safe(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
            raise ValueError("slug must contain only lowercase letters, numbers, and hyphens")
        if ".." in value or "/" in value or "\\" in value:
            raise ValueError("slug cannot contain path separators or traversal")
        return value

    @model_validator(mode="after")
    def objectives_default(self) -> WorkspaceMetadata:
        if not self.assignment.learning_objectives:
            self.assignment.learning_objectives = [
                "Write pure functions with clear input/output behavior",
                "Handle common string edge cases",
            ]
        return self

    def touch(self) -> None:
        self.updated_at = utc_now_iso()


class WorkflowState(BaseModel):
    schema_version: Literal["0.1"] = SCHEMA_VERSION
    workspace_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    active_run_id: str | None = None
    last_error: str | None = None
    progress_events: list[dict[str, Any]] = Field(default_factory=list)


class DoctorCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class DoctorReport(BaseModel):
    checks: list[DoctorCheck]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)
