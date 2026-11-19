"""SQLAlchemy ORM models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


def now():
    return datetime.now()


class User(Base):
    """Registered platform user (auth)."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    created_at = Column(DateTime, default=now)

    tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")


class AuthToken(Base):
    """Persistent login token for API authentication."""
    __tablename__ = "auth_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=now)
    expires_at = Column(DateTime, nullable=True)
    # 最后一次活跃时间：用于「长时间无操作自动登出」判定
    last_active_at = Column(DateTime, nullable=True, default=now)

    user = relationship("User", back_populates="tokens")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=now)

    folders = relationship("Folder", back_populates="project", cascade="all, delete-orphan")
    suites = relationship("Suite", back_populates="project", cascade="all, delete-orphan")


class Folder(Base):
    """Case directory tree node."""
    __tablename__ = "folders"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=now)

    project = relationship("Project", back_populates="folders")
    parent = relationship("Folder", remote_side=[id], back_populates="children")
    children = relationship("Folder", back_populates="parent", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="folder", cascade="all, delete-orphan")


class Case(Base):
    """Unified test case: manual / api / ui."""
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    case_type = Column(String(20), default="manual")  # manual | api | ui
    priority = Column(String(10), default="P2")  # P0/P1/P2/P3
    tags = Column(JSON, default=list)
    precondition = Column(Text, default="")
    steps = Column(Text, default="")       # manual: text; ui: step list json string
    expected = Column(Text, default="")
    # API case fields
    method = Column(String(10), default="GET")
    url = Column(Text, default="")
    headers = Column(JSON, default=dict)
    body = Column(Text, default="")
    assertions = Column(JSON, default=list)  # [{type, key, op, value}]
    extractors = Column(JSON, default=list)  # [{name, source, key}]
    # UI case runtime
    ui_config = Column(JSON, default=dict)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    folder = relationship("Folder", back_populates="cases")


class Environment(Base):
    __tablename__ = "environments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    base_url = Column(Text, default="")
    variables = Column(JSON, default=dict)  # {{var}} placeholders
    created_at = Column(DateTime, default=now)


class Suite(Base):
    """Named collection of cases for a run (smoke, regression, ...)."""
    __tablename__ = "suites"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    case_ids = Column(JSON, default=list)
    env_id = Column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=now)

    project = relationship("Project", back_populates="suites")


class GenerationRecord(Base):
    """History of requirement-document → test-case generations."""
    __tablename__ = "generation_records"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    doc_name = Column(String(255), nullable=False)
    doc_format = Column(String(30), default="")
    doc_size = Column(Integer, default=0)
    backend = Column(String(20), default="local")
    requirement_text = Column(Text, default="")
    cases_count = Column(Integer, default=0)
    dimensions = Column(JSON, default=list)
    cases = Column(JSON, default=list)
    imported = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)


class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(Integer, ForeignKey("suites.id", ondelete="SET NULL"), nullable=True)
    env_id = Column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="pending")  # pending/running/done
    trigger = Column(String(20), default="manual")
    total = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    start_time = Column(DateTime, default=now)
    end_time = Column(DateTime, nullable=True)
    results = Column(JSON, default=list)

    details = relationship("RunDetail", back_populates="run", cascade="all, delete-orphan")


class RunDetail(Base):
    __tablename__ = "run_details"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    case_title = Column(String(200), default="")
    case_type = Column(String(20), default="")
    status = Column(String(20), default="passed")  # passed/failed/error/skipped
    duration_ms = Column(Integer, default=0)
    error_msg = Column(Text, default="")
    request_info = Column(JSON, default=dict)
    response_info = Column(JSON, default=dict)
    assertions_result = Column(JSON, default=list)
    extracted = Column(JSON, default=dict)  # 该用例提取并传递给后续用例的变量
    logs = Column(Text, default="")
    created_at = Column(DateTime, default=now)

    run = relationship("Run", back_populates="details")
