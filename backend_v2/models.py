import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend_v2.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="EDITOR")


class SourceDocument(Base, TimestampMixin):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="UPLOADED")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    structure_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default="")
    extraction_method: Mapped[str] = mapped_column(String(30), default="text")


class DocumentUnit(Base, TimestampMixin):
    __tablename__ = "document_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("document_units.id", ondelete="CASCADE"), nullable=True)
    level: Mapped[str] = mapped_column(String(30))
    number: Mapped[str] = mapped_column(String(30), default="")
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, default="")
    start_page: Mapped[int] = mapped_column(Integer, default=1)
    end_page: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


class ReferenceRecord(Base, TimestampMixin):
    __tablename__ = "references"
    __table_args__ = (UniqueConstraint("project_id", "citation_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    citation_key: Mapped[str] = mapped_column(String(160))
    authors: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[str] = mapped_column(String(10), default="")
    container_title: Mapped[str] = mapped_column(Text, default="")
    doi: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    raw_reference: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(20), default="paste")
    parse_confidence: Mapped[float] = mapped_column(Float, default=0.5)


class CitationOccurrence(Base, TimestampMixin):
    __tablename__ = "citation_occurrences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("document_units.id", ondelete="CASCADE"), index=True)
    reference_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"), nullable=True)
    marker: Mapped[str] = mapped_column(String(300))
    context: Mapped[str] = mapped_column(Text, default="")
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="MISSING_REFERENCE")


class ReviewRun(Base, TimestampMixin):
    __tablename__ = "review_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("document_units.id", ondelete="CASCADE"), index=True)
    user_goal: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(30), default="rule-based")
    summary: Mapped[str] = mapped_column(Text, default="")
    suggestions_json: Mapped[str] = mapped_column(Text, default="[]")


class RevisionDraft(Base, TimestampMixin):
    __tablename__ = "revision_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("document_units.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    current_version: Mapped[int] = mapped_column(Integer, default=1)


class DraftVersion(Base):
    __tablename__ = "draft_versions"
    __table_args__ = (UniqueConstraint("draft_id", "version_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    draft_id: Mapped[str] = mapped_column(ForeignKey("revision_drafts.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(30), default="user")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    storage_prefix: Mapped[str] = mapped_column(Text)
    main_document: Mapped[str] = mapped_column(String(500), default="main.tex")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class WorkspaceVersion(Base):
    __tablename__ = "workspace_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    relative_path: Mapped[str] = mapped_column(String(1000))
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    job_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="QUEUED")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str] = mapped_column(String(500), default="Menunggu diproses")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(30))
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(Text)
