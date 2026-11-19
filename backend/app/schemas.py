"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Project ----------
class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectOut(ORMBase):
    id: int
    name: str
    description: str
    created_at: datetime


# ---------- Folder ----------
class FolderCreate(BaseModel):
    project_id: int
    parent_id: Optional[int] = None
    name: str


class FolderOut(ORMBase):
    id: int
    project_id: int
    parent_id: Optional[int]
    name: str
    created_at: datetime
    case_count: int = 0


# ---------- Case ----------
class CaseCreate(BaseModel):
    folder_id: int
    title: str
    case_type: str = "manual"
    priority: str = "P2"
    tags: list[str] = []
    precondition: str = ""
    steps: str = ""
    expected: str = ""
    method: str = "GET"
    url: str = ""
    headers: dict[str, Any] = {}
    body: str = ""
    assertions: list[dict] = []
    extractors: list[dict] = []
    ui_config: dict = {}
    enabled: bool = True


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    case_type: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[list[str]] = None
    precondition: Optional[str] = None
    steps: Optional[str] = None
    expected: Optional[str] = None
    method: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[dict] = None
    body: Optional[str] = None
    assertions: Optional[list[dict]] = None
    extractors: Optional[list[dict]] = None
    ui_config: Optional[dict] = None
    enabled: Optional[bool] = None


class CaseOut(ORMBase):
    id: int
    folder_id: int
    title: str
    case_type: str
    priority: str
    tags: list
    precondition: str
    steps: str
    expected: str
    method: str
    url: str
    headers: dict
    body: str
    assertions: list
    extractors: list
    ui_config: dict
    enabled: bool
    updated_at: datetime


# ---------- Environment ----------
class EnvironmentCreate(BaseModel):
    name: str
    base_url: str = ""
    variables: dict[str, Any] = {}


class EnvironmentOut(ORMBase):
    id: int
    name: str
    base_url: str
    variables: dict


# ---------- Suite ----------
class SuiteCreate(BaseModel):
    project_id: int
    name: str
    case_ids: list[int] = []
    env_id: Optional[int] = None


class SuiteOut(ORMBase):
    id: int
    project_id: int
    name: str
    case_ids: list
    env_id: Optional[int]
    created_at: datetime


# ---------- Run ----------
class RunCreate(BaseModel):
    case_ids: list[int] = []
    suite_id: Optional[int] = None
    env_id: Optional[int] = None
    case_type: Optional[str] = None
    trigger: str = "manual"


class RunOut(ORMBase):
    id: int
    suite_id: Optional[int]
    env_id: Optional[int]
    status: str
    trigger: str
    total: int
    passed: int
    failed: int
    skipped: int
    start_time: datetime
    end_time: Optional[datetime]
    results: list


class RunDetailOut(ORMBase):
    id: int
    run_id: int
    case_id: Optional[int]
    case_title: str
    case_type: str
    status: str
    duration_ms: int
    error_msg: str
    request_info: dict
    response_info: dict
    assertions_result: list
    extracted: dict = {}
    logs: str


# ---------- Generation ----------
class GenerationOut(ORMBase):
    id: int
    project_id: Optional[int]
    doc_name: str
    doc_format: str
    doc_size: int
    backend: str
    requirement_text: str
    cases_count: int
    dimensions: list
    cases: list
    imported: bool
    created_at: datetime


class GenerationImport(BaseModel):
    record_id: int
    folder_id: int
    case_ids: list[int] = []  # optional subset; empty = all


# ---------- Locator extraction ----------
class LocatorStep(BaseModel):
    action: str = "wait"  # click / fill / check / wait / goto
    target: str = ""
    value: str = ""


class LocatorExtractRequest(BaseModel):
    url: str
    keyword: str
    exact: bool = False
    wait_ms: int = 1000
    steps: list[LocatorStep] = []
    session_name: str = ""  # 复用的登录态名称（可选）


class LoginSessionStart(BaseModel):
    name: str
    url: str


# ---------- API debug ----------
class ApiDebugRequest(BaseModel):
    method: str = "GET"
    url: str
    headers: dict[str, Any] = {}
    body: str = ""
    body_mode: str = "raw"          # raw | form-data | x-www-form-urlencoded | none
    form_data: list[dict] = []      # [{key, value, enabled, type}]
    variables: dict[str, Any] = {}
    assertions: list[dict] = []
    extractors: list[dict] = []


class ApiDebugResponse(BaseModel):
    status_code: Optional[int] = None
    headers: dict = {}
    body: Any = None
    duration_ms: int = 0
    error: str = ""
    assertions_result: list = []
    extracted: dict = {}
    size: int = 0
    cookies: dict = {}
    request_info: dict = {}
