"""FastAPI application for the test efficiency platform."""
import os
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Form, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
import os as _os

from .database import get_db, init_db, SessionLocal
from . import models, schemas
from .engine import execute_api, execute_ui_steps, render
from .doc_parser import parse_document
from .case_generator import generate_cases, DIMENSIONS
from . import locator_extractor
from . import browser_session
from . import exporter
from . import coverage as coverage_engine
from . import ui_autogen as ui_autogen_engine
from . import api_autogen
from . import interactive_session
from . import auth
from . import db_connect as db_engine

app = FastAPI(title="测试提效平台", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Auth: protect all business APIs (except /api/auth/*)
# ============================================================
@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and not path.startswith("/api/auth/"):
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return JSONResponse(
                {"detail": "未登录或登录已过期", "code": "no_token"},
                status_code=401,
                headers={"X-Auth-Error": "no_token"},
            )
        token = header[7:].strip()
        db = SessionLocal()
        try:
            rec, user, detail, code = auth.resolve_token(db, token)
        finally:
            db.close()
        if not rec:
            return JSONResponse(
                {"detail": detail, "code": code},
                status_code=401,
                headers={"X-Auth-Error": code},
            )
    return await call_next(request)


# ============================================================
# Auth endpoints
# ============================================================
@app.post("/api/auth/register")
def register(payload: dict):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    err = auth.validate_username(username)
    if err:
        raise HTTPException(400, err)
    err = auth.validate_password(password)
    if err:
        raise HTTPException(400, err)
    db = SessionLocal()
    try:
        if db.query(models.User).filter(models.User.username == username).first():
            raise HTTPException(400, "用户名已被注册")
        user = models.User(username=username, password_hash=auth.hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)
        token = auth.create_token(db, user.id)
        return {
            "token": token,
            "user": {"id": user.id, "username": user.username, "role": user.role},
            "idle_timeout": auth.IDLE_TIMEOUT_SECONDS,
        }
    finally:
        db.close()


@app.post("/api/auth/login")
def login(payload: dict):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user or not auth.verify_password(password, user.password_hash):
            raise HTTPException(401, "用户名或密码错误")
        token = auth.create_token(db, user.id)
        return {
            "token": token,
            "user": {"id": user.id, "username": user.username, "role": user.role},
            "idle_timeout": auth.IDLE_TIMEOUT_SECONDS,
        }
    finally:
        db.close()


@app.get("/api/auth/me")
def me(current_user: dict = Depends(auth.get_current_user)):
    return current_user


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        db = SessionLocal()
        try:
            db.query(models.AuthToken).filter(models.AuthToken.token == token).delete()
            db.commit()
        finally:
            db.close()
    return {"ok": True}


@app.on_event("startup")
def startup():
    init_db()
    seed_demo_data()


# ============================================================
# Projects
# ============================================================
@app.get("/api/projects", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).order_by(models.Project.id).all()


@app.post("/api/projects", response_model=schemas.ProjectOut)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    obj = models.Project(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/projects/{pid}")
def delete_project(pid: int, db: Session = Depends(get_db)):
    obj = db.query(models.Project).filter(models.Project.id == pid).first()
    if not obj:
        raise HTTPException(404, "项目不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ============================================================
# Folders / Case tree
# ============================================================
@app.get("/api/folders", response_model=list[schemas.FolderOut])
def list_folders(project_id: int, db: Session = Depends(get_db)):
    folders = db.query(models.Folder).filter(models.Folder.project_id == project_id).all()
    result = []
    for f in folders:
        cnt = db.query(func.count(models.Case.id)).filter(models.Case.folder_id == f.id).scalar()
        result.append(schemas.FolderOut(
            id=f.id, project_id=f.project_id, parent_id=f.parent_id,
            name=f.name, created_at=f.created_at, case_count=cnt,
        ))
    return result


@app.post("/api/folders", response_model=schemas.FolderOut)
def create_folder(payload: schemas.FolderCreate, db: Session = Depends(get_db)):
    obj = models.Folder(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return schemas.FolderOut(
        id=obj.id, project_id=obj.project_id, parent_id=obj.parent_id,
        name=obj.name, created_at=obj.created_at, case_count=0,
    )


@app.delete("/api/folders/{fid}")
def delete_folder(fid: int, db: Session = Depends(get_db)):
    obj = db.query(models.Folder).filter(models.Folder.id == fid).first()
    if not obj:
        raise HTTPException(404, "目录不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ============================================================
# Cases
# ============================================================
@app.get("/api/cases", response_model=list[schemas.CaseOut])
def list_cases(
    project_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    case_type: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Case)
    if folder_id:
        q = q.filter(models.Case.folder_id == folder_id)
    elif project_id:
        folder_ids = [f.id for f in db.query(models.Folder).filter(models.Folder.project_id == project_id).all()]
        q = q.filter(models.Case.folder_id.in_(folder_ids))
    if case_type:
        q = q.filter(models.Case.case_type == case_type)
    if keyword:
        q = q.filter(models.Case.title.contains(keyword))
    return q.order_by(models.Case.id.desc()).all()


@app.get("/api/cases/export")
def export_cases_file(
    project_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    case_type: Optional[str] = None,
    keyword: Optional[str] = None,
    case_ids: Optional[str] = Query(None, description="逗号分隔的用例id，勾选批量导出时优先使用"),
    format: str = Query("xlsx"),
    db: Session = Depends(get_db),
):
    """Export case-center cases (same filters as the list view) to Excel / CSV."""
    q = db.query(models.Case)
    folder_names: dict = {}
    if case_ids:
        ids = [int(x) for x in case_ids.split(",") if x.strip().lstrip("-").isdigit()]
        q = q.filter(models.Case.id.in_(ids))
        flist = db.query(models.Folder).all()
        folder_names = {f.id: f.name for f in flist}
    elif folder_id:
        q = q.filter(models.Case.folder_id == folder_id)
        f = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
        if f:
            folder_names[f.id] = f.name
    elif project_id:
        flist = db.query(models.Folder).filter(models.Folder.project_id == project_id).all()
        folder_names = {f.id: f.name for f in flist}
        q = q.filter(models.Case.folder_id.in_([f.id for f in flist]))
    if case_type:
        q = q.filter(models.Case.case_type == case_type)
    if keyword:
        q = q.filter(models.Case.title.contains(keyword))
    cases = q.order_by(models.Case.id.desc()).all()
    if not cases:
        raise HTTPException(400, "当前筛选条件下没有可导出的用例")
    case_dicts = [{
        "id": c.id, "title": c.title, "case_type": c.case_type, "priority": c.priority,
        "folder_id": c.folder_id, "precondition": c.precondition, "steps": c.steps,
        "expected": c.expected, "tags": c.tags or [], "method": c.method, "url": c.url,
        "headers": c.headers or {}, "body": c.body, "assertions": c.assertions or [],
    } for c in cases]

    name = folder_names.get(folder_id) if folder_id else None
    if not name and project_id:
        p = db.query(models.Project).filter(models.Project.id == project_id).first()
        name = p.name if p else None
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    base = f"{name or '测试用例'}_{stamp}"

    try:
        data, filename, ctype = exporter.export_case_center(case_dicts, format, base, folder_names)
    except ValueError as e:
        raise HTTPException(400, str(e))
    from urllib.parse import quote
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return Response(content=data, media_type=ctype, headers=headers)


@app.post("/api/cases", response_model=schemas.CaseOut)
def create_case(payload: schemas.CaseCreate, db: Session = Depends(get_db)):
    obj = models.Case(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.put("/api/cases/{cid}", response_model=schemas.CaseOut)
def update_case(cid: int, payload: schemas.CaseUpdate, db: Session = Depends(get_db)):
    obj = db.query(models.Case).filter(models.Case.id == cid).first()
    if not obj:
        raise HTTPException(404, "用例不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/cases/{cid}")
def delete_case(cid: int, db: Session = Depends(get_db)):
    obj = db.query(models.Case).filter(models.Case.id == cid).first()
    if not obj:
        raise HTTPException(404, "用例不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


class CaseBatchDelete(schemas.BaseModel):
    ids: list[int]


@app.post("/api/cases/batch-delete")
def batch_delete_cases(payload: CaseBatchDelete, db: Session = Depends(get_db)):
    """批量删除用例"""
    if not payload.ids:
        raise HTTPException(400, "请提供要删除的用例 id")
    n = db.query(models.Case).filter(models.Case.id.in_(payload.ids)).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "deleted": n}


# ============================================================
# Requirement coverage analysis
# ============================================================
class CoverageAnalyze(schemas.BaseModel):
    project_id: int
    requirement_text: Optional[str] = None
    generation_id: Optional[int] = None


@app.post("/api/coverage/analyze")
def coverage_analyze(payload: CoverageAnalyze, db: Session = Depends(get_db)):
    """Analyze how well existing cases cover a requirement text (or a saved generation's text)."""
    text = (payload.requirement_text or "").strip()
    if payload.generation_id:
        r = db.query(models.GenerationRecord).filter(models.GenerationRecord.id == payload.generation_id).first()
        if not r:
            raise HTTPException(404, "生成记录不存在")
        if not text:
            text = (r.requirement_text or "").strip()
    if not text:
        raise HTTPException(400, "请提供需求文本或选择生成记录")

    flist = db.query(models.Folder).filter(models.Folder.project_id == payload.project_id).all()
    folder_names = {f.id: f.name for f in flist}
    cases = db.query(models.Case).filter(models.Case.folder_id.in_([f.id for f in flist])).all()
    case_dicts = [{
        "id": c.id, "title": c.title, "case_type": c.case_type, "priority": c.priority,
        "folder_id": c.folder_id, "precondition": c.precondition, "steps": c.steps,
        "expected": c.expected, "tags": c.tags or [], "method": c.method, "url": c.url,
    } for c in cases]

    result = coverage_engine.analyze(text, case_dicts)
    result["summary"]["project_id"] = payload.project_id
    # 补充目录名，便于前端展示用例归属
    for m in result["requirement_points"]:
        for match in m["matched"]:
            obj = next((c for c in case_dicts if c["id"] == match.get("id")), None)
            match["folder"] = folder_names.get(obj["folder_id"], "") if obj else ""
    return result


# ============================================================
# API automation project generation
# ============================================================
class AutoGenRequest(schemas.BaseModel):
    project_id: int
    folder_id: Optional[int] = None
    keyword: Optional[str] = None
    case_ids: Optional[list[int]] = None
    base_url: str = "http://127.0.0.1:9001"


@app.post("/api/cases/autogen")
def autogen_api_project(payload: AutoGenRequest, db: Session = Depends(get_db)):
    """按接口自动化框架模板，把选中的接口用例生成为可运行的 pytest 项目 (zip)。"""
    q = db.query(models.Case).filter(models.Case.case_type == "api")
    if payload.case_ids:
        q = q.filter(models.Case.id.in_(payload.case_ids))
    else:
        if payload.folder_id:
            q = q.filter(models.Case.folder_id == payload.folder_id)
        elif payload.project_id:
            flist = db.query(models.Folder).filter(models.Folder.project_id == payload.project_id).all()
            q = q.filter(models.Case.folder_id.in_([f.id for f in flist]))
        if payload.keyword:
            q = q.filter(models.Case.title.contains(payload.keyword))
    cases = q.order_by(models.Case.id.desc()).all()
    if not cases:
        raise HTTPException(400, "没有可生成的接口用例")

    flist = db.query(models.Folder).filter(models.Folder.project_id == payload.project_id).all()
    folder_names = {f.id: f.name for f in flist}
    p = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    project_name = p.name if p else "接口自动化"

    case_dicts = [{
        "id": c.id, "title": c.title, "kw": folder_names.get(c.folder_id, "未分组"),
        "method": (c.method or "GET").upper(), "path": c.url or "",
        "headers": c.headers or {},
        "json": c.body if c.body else None,  # 请求体按 JSON 处理（生成器会校验）
        "asserts": c.assertions or [],
        "extract": c.extractors or [],
    } for c in cases]
    # body 非 JSON 时降级为纯文本
    for d in case_dicts:
        if d["json"] is not None:
            try:
                d["json"] = json.loads(d["json"]) if isinstance(d["json"], str) else d["json"]
            except Exception:
                d["body"] = d.pop("json")

    try:
        data, top = api_autogen.generate_project(case_dicts, payload.base_url, project_name)
    except FileNotFoundError as e:
        raise HTTPException(500, f"模板文件缺失: {e}")
    from urllib.parse import quote
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(top + '.zip')}"}
    return Response(content=data, media_type="application/zip", headers=headers)


# ============================================================
# UI automation project generation (step-flow orchestration)
# ============================================================
class UiFlowStep(schemas.BaseModel):
    action: str
    target: Optional[str] = ""
    value: Optional[str] = ""


class UiFlow(schemas.BaseModel):
    title: str
    steps: list[UiFlowStep]


class UiAutoGenRequest(schemas.BaseModel):
    flows: list[UiFlow]
    framework: str = ui_autogen_engine.FRAMEWORK_PLAYWRIGHT


@app.post("/api/ui/autogen")
def ui_autogen_project(payload: UiAutoGenRequest):
    """按步骤编排 + 选定框架（Playwright/Selenium/RobotFramework），生成可运行项目 (zip)。"""
    flows = [{"title": f.title, "steps": [s.model_dump() for s in f.steps]} for f in payload.flows]
    try:
        data, filename = ui_autogen_engine.generate_ui_project(flows, payload.framework)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))
    from urllib.parse import quote
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return Response(content=data, media_type="application/zip", headers=headers)


# ============================================================
# Database connection & query (multi-DB)
# ============================================================
class DbConfig(schemas.BaseModel):
    db_type: str = "mysql"
    host: Optional[str] = ""
    port: Optional[int] = None
    database: Optional[str] = ""
    username: Optional[str] = ""
    password: Optional[str] = ""
    dsn: Optional[str] = ""       # Oracle 可选完整 DSN
    timeout: Optional[int] = 10


class DbQueryRequest(schemas.BaseModel):
    config: DbConfig
    sql: str
    allow_write: bool = False
    limit: int = 200


class DbTableRequest(schemas.BaseModel):
    config: DbConfig
    table: Optional[str] = None


@app.get("/api/db/types")
def db_types():
    """列出支持的数据库类型及本机驱动是否可用。"""
    return db_engine.supported_drivers()


@app.post("/api/db/install-driver/{db_type}")
def db_install_driver(db_type: str):
    """一键安装指定数据库驱动（在后端 Python 环境执行 pip install）。"""
    try:
        return db_engine.install_driver(db_type)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/db/test")
def db_test(payload: DbConfig):
    """测试数据库连接。"""
    return db_engine.test_connection(payload.model_dump())


@app.post("/api/db/query")
def db_query(payload: DbQueryRequest):
    """执行 SQL 查询。默认只读，写操作需 allow_write=True。"""
    try:
        return db_engine.execute_query(
            payload.config.model_dump(), payload.sql,
            allow_write=payload.allow_write, limit=payload.limit,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/db/tables")
def db_tables(payload: DbConfig):
    """列出数据库中的表。"""
    try:
        return db_engine.list_tables(payload.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/db/describe")
def db_describe(payload: DbTableRequest):
    """查看表结构。"""
    if not payload.table:
        raise HTTPException(400, "请提供表名")
    try:
        return db_engine.describe_table(payload.config.model_dump(), payload.table)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ============================================================
# Environments
# ============================================================
@app.get("/api/environments", response_model=list[schemas.EnvironmentOut])
def list_envs(db: Session = Depends(get_db)):
    return db.query(models.Environment).order_by(models.Environment.id).all()


@app.post("/api/environments", response_model=schemas.EnvironmentOut)
def create_env(payload: schemas.EnvironmentCreate, db: Session = Depends(get_db)):
    obj = models.Environment(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.put("/api/environments/{eid}", response_model=schemas.EnvironmentOut)
def update_env(eid: int, payload: schemas.EnvironmentCreate, db: Session = Depends(get_db)):
    obj = db.query(models.Environment).filter(models.Environment.id == eid).first()
    if not obj:
        raise HTTPException(404, "环境不存在")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/environments/{eid}")
def delete_env(eid: int, db: Session = Depends(get_db)):
    obj = db.query(models.Environment).filter(models.Environment.id == eid).first()
    if not obj:
        raise HTTPException(404, "环境不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ============================================================
# Suites
# ============================================================
@app.get("/api/suites", response_model=list[schemas.SuiteOut])
def list_suites(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Suite)
    if project_id:
        q = q.filter(models.Suite.project_id == project_id)
    return q.order_by(models.Suite.id.desc()).all()


@app.post("/api/suites", response_model=schemas.SuiteOut)
def create_suite(payload: schemas.SuiteCreate, db: Session = Depends(get_db)):
    obj = models.Suite(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/suites/{sid}")
def delete_suite(sid: int, db: Session = Depends(get_db)):
    obj = db.query(models.Suite).filter(models.Suite.id == sid).first()
    if not obj:
        raise HTTPException(404, "测试集不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ============================================================
# API debug (single request, no persistence)
# ============================================================
@app.post("/api/debug/run", response_model=schemas.ApiDebugResponse)
def debug_run(payload: schemas.ApiDebugRequest):
    case = {
        "method": payload.method, "url": payload.url, "headers": payload.headers,
        "body": payload.body, "body_mode": payload.body_mode, "form_data": payload.form_data,
        "assertions": payload.assertions, "extractors": payload.extractors,
    }
    env = {"base_url": "", "variables": payload.variables}
    res = execute_api(case, env)
    return schemas.ApiDebugResponse(
        status_code=res["response_info"].get("status_code"),
        headers=res["response_info"].get("headers", {}),
        body=res["response_info"].get("body"),
        duration_ms=res["duration_ms"],
        error=res["error_msg"],
        assertions_result=res["assertions_result"],
        extracted=res.get("_extracted", {}),
        size=res["response_info"].get("size", 0),
        cookies=res["response_info"].get("cookies", {}),
        request_info=res["request_info"],
    )


@app.post("/api/debug/run-chain")
def debug_run_chain(payload: dict):
    """Execute multiple API requests in order, forwarding extracted variables.

    payload: { steps: [ {method,url,headers,body,assertions,extractors}, ... ],
               variables: {...} }
    Each step's extracted values are merged into the shared variable pool and
    are available to all following steps via {{var}} placeholders.
    """
    steps = payload.get("steps") or []
    if not steps:
        raise HTTPException(400, "没有可执行的接口步骤")
    variables = dict(payload.get("variables") or {})
    out = []
    for i, st in enumerate(steps, 1):
        case = {
            "method": st.get("method", "GET"),
            "url": st.get("url", ""),
            "headers": st.get("headers") or {},
            "body": st.get("body", ""),
            "body_mode": st.get("body_mode", "raw"),
            "form_data": st.get("form_data") or [],
            "assertions": st.get("assertions") or [],
            "extractors": st.get("extractors") or [],
        }
        res = execute_api(case, {"base_url": "", "variables": variables})
        extracted = {k: v for k, v in (res.get("_extracted") or {}).items() if v is not None}
        if extracted:
            variables.update(extracted)
        out.append({
            "index": i,
            "name": st.get("name", ""),
            "url": case["url"],
            "method": case["method"],
            "status_code": res["response_info"].get("status_code"),
            "body": res["response_info"].get("body"),
            "size": res["response_info"].get("size", 0),
            "duration_ms": res["duration_ms"],
            "error": res["error_msg"],
            "assertions_result": res["assertions_result"],
            "extracted": extracted,
            "request_info": res["request_info"],
            "status": res["status"],
        })
    return {"results": out, "variables": variables}


# ============================================================
# Run execution
# ============================================================
def _persist_run(db: Session, case_ids: list[int], suite_id, env_id, trigger, case_type=None) -> models.Run:
    run = models.Run(suite_id=suite_id, env_id=env_id, status="running", trigger=trigger)
    db.add(run)
    db.commit()
    db.refresh(run)

    env = None
    variables = {}
    if env_id:
        e = db.query(models.Environment).filter(models.Environment.id == env_id).first()
        if e:
            env = {"base_url": e.base_url, "variables": e.variables or {}}
            variables = dict(e.variables or {})

    cases = db.query(models.Case).filter(models.Case.id.in_(case_ids)).all()
    case_map = {c.id: c for c in cases}
    ordered = [case_map[i] for i in case_ids if i in case_map and case_map[i].enabled]

    details = []
    for c in ordered:
        cdict = {
            "title": c.title, "case_type": c.case_type, "method": c.method, "url": c.url,
            "headers": c.headers, "body": c.body, "assertions": c.assertions,
            "extractors": c.extractors, "steps": c.steps, "ui_config": c.ui_config,
        }
        if c.case_type == "api":
            res = execute_api(cdict, env, variables)
        elif c.case_type == "ui":
            res = execute_ui_steps(cdict, variables)
        else:
            res = {"status": "skipped", "error_msg": "手工用例，不参与自动执行",
                   "duration_ms": 0, "request_info": {}, "response_info": {},
                   "assertions_result": [], "logs": ""}

        # 接口关联：把本用例提取的变量回写到共享变量池，后续用例可用 {{变量名}} 引用
        extracted = res.get("_extracted") or {}
        valid_extracted = {k: v for k, v in extracted.items() if v is not None}
        if valid_extracted:
            variables.update(valid_extracted)
            res["logs"] = (res.get("logs", "") +
                           f"\n[接口关联] 提取并传递变量: {', '.join(valid_extracted.keys())}").strip()

        d = models.RunDetail(
            run_id=run.id, case_id=c.id, case_title=c.title, case_type=c.case_type,
            status=res["status"], duration_ms=res["duration_ms"], error_msg=res["error_msg"],
            request_info=res["request_info"], response_info=res["response_info"],
            assertions_result=res["assertions_result"], extracted=valid_extracted,
            logs=res["logs"],
        )
        db.add(d)
        details.append(d)

    db.flush()
    statuses = [d.status for d in details]
    run.total = len(details)
    run.passed = statuses.count("passed")
    run.failed = len([s for s in statuses if s in ("failed", "error")])
    run.skipped = statuses.count("skipped")
    run.status = "done"
    run.end_time = datetime.now()
    run.results = [{"case_title": d.case_title, "status": d.status} for d in details]
    db.commit()
    db.refresh(run)
    return run


@app.post("/api/runs", response_model=schemas.RunOut)
def create_run(payload: schemas.RunCreate, db: Session = Depends(get_db)):
    case_ids = list(payload.case_ids)
    if payload.suite_id and not case_ids:
        s = db.query(models.Suite).filter(models.Suite.id == payload.suite_id).first()
        if s:
            case_ids = list(s.case_ids or [])
            payload.env_id = payload.env_id or s.env_id
    if payload.case_type and not case_ids:
        ids = [c.id for c in db.query(models.Case).filter(models.Case.case_type == payload.case_type).all()]
        case_ids = ids
    if not case_ids:
        raise HTTPException(400, "没有可执行的用例")
    run = _persist_run(db, case_ids, payload.suite_id, payload.env_id, payload.trigger)
    return run


@app.get("/api/runs", response_model=list[schemas.RunOut])
def list_runs(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(models.Run).order_by(models.Run.id.desc()).limit(limit).all()


@app.get("/api/runs/{rid}", response_model=schemas.RunOut)
def get_run(rid: int, db: Session = Depends(get_db)):
    run = db.query(models.Run).filter(models.Run.id == rid).first()
    if not run:
        raise HTTPException(404, "执行记录不存在")
    return run


@app.get("/api/runs/{rid}/details", response_model=list[schemas.RunDetailOut])
def get_run_details(rid: int, db: Session = Depends(get_db)):
    return db.query(models.RunDetail).filter(models.RunDetail.run_id == rid).order_by(models.RunDetail.id).all()


@app.delete("/api/runs/{rid}")
def delete_run(rid: int, db: Session = Depends(get_db)):
    obj = db.query(models.Run).filter(models.Run.id == rid).first()
    if not obj:
        raise HTTPException(404, "执行记录不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ============================================================
# Requirement → Case generation
# ============================================================
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt",
                ".md", ".markdown", ".csv", ".json", ".log", ".yaml", ".yml", ".xml",
                ".ini", ".sql", ".html", ".htm", ".png", ".jpg", ".jpeg", ".bmp",
                ".gif", ".webp", ".tiff"}


@app.post("/api/generate", response_model=schemas.GenerationOut)
async def generate_from_document(
    file: UploadFile = File(...),
    project_id: int | None = Form(None),
    backend: str = Form("local"),
    dimensions: str = Form(""),
    language: str = Form("zh"),
    template: str = Form(""),
    case_types: str = Form(""),
    db: Session = Depends(get_db),
):
    """Upload a requirement document, parse it, and auto-generate comprehensive test cases."""
    filename = file.filename or "requirement.txt"
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"不支持的文件格式: {ext}，支持 {', '.join(sorted(ALLOWED_EXTS))}")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "文件超过 20MB 限制")

    safe_name = f"{int(__import__('time').time()*1000)}_{filename.replace('/', '_').replace(chr(92), '_')}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(save_path, "wb") as f:
        f.write(content)

    try:
        text, fmt = parse_document(save_path, filename)
    except Exception as e:
        raise HTTPException(400, str(e))

    if not text.strip():
        raise HTTPException(400, "未能从文档中提取到文本内容")

    selected_dims = [d for d in dimensions.split(",") if d] if dimensions else None
    # 用例类型：functional=功能测试用例，api=接口测试用例；为空默认两类都生成
    case_type_list = [t.strip() for t in (case_types or "").split(",") if t.strip()]
    cases = generate_cases(text, os.path.splitext(filename)[0], {
        "backend": backend,
        "dimensions": selected_dims,
        "language": language,
        "template": template,
        "case_types": case_type_list,
    })
    if not cases:
        raise HTTPException(400, "未能生成用例，请检查文档内容是否充足")

    dims = sorted(set(c["dimension"] for c in cases))
    record = models.GenerationRecord(
        project_id=project_id,
        doc_name=filename,
        doc_format=fmt,
        doc_size=len(content),
        backend=backend,
        requirement_text=text[:20000],
        cases_count=len(cases),
        dimensions=dims,
        cases=cases,
        imported=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/generations", response_model=list[schemas.GenerationOut])
def list_generations(project_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.GenerationRecord)
    if project_id:
        q = q.filter(models.GenerationRecord.project_id == project_id)
    return q.order_by(models.GenerationRecord.id.desc()).all()


@app.get("/api/generations/{gid}", response_model=schemas.GenerationOut)
def get_generation(gid: int, db: Session = Depends(get_db)):
    r = db.query(models.GenerationRecord).filter(models.GenerationRecord.id == gid).first()
    if not r:
        raise HTTPException(404, "生成记录不存在")
    return r


@app.get("/api/generations/{gid}/export")
def export_generation(gid: int, format: str = Query("xlsx"), db: Session = Depends(get_db)):
    """Export a generation record's cases to the requested file format."""
    r = db.query(models.GenerationRecord).filter(models.GenerationRecord.id == gid).first()
    if not r:
        raise HTTPException(404, "生成记录不存在")
    cases = r.cases or []
    if not cases:
        raise HTTPException(400, "该记录没有可导出的用例")
    lang = cases[0].get("language", "zh")
    try:
        data, filename, ctype = exporter.export_cases(cases, format, r.doc_name, lang)
    except ValueError as e:
        raise HTTPException(400, str(e))
    from urllib.parse import quote
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return Response(content=data, media_type=ctype, headers=headers)


@app.delete("/api/generations/{gid}")
def delete_generation(gid: int, db: Session = Depends(get_db)):
    r = db.query(models.GenerationRecord).filter(models.GenerationRecord.id == gid).first()
    if not r:
        raise HTTPException(404, "生成记录不存在")
    db.delete(r)
    db.commit()
    return {"ok": True}


@app.post("/api/generations/{gid}/import")
def import_generation(gid: int, payload: schemas.GenerationImport, db: Session = Depends(get_db)):
    """Import generated cases into the case center (as a real test case folder)."""
    r = db.query(models.GenerationRecord).filter(models.GenerationRecord.id == gid).first()
    if not r:
        raise HTTPException(404, "生成记录不存在")
    folder = db.query(models.Folder).filter(models.Folder.id == payload.folder_id).first()
    if not folder:
        raise HTTPException(404, "目标目录不存在")

    cases = r.cases or []
    if payload.case_ids:
        cases = [c for c in cases if c.get("no") in payload.case_ids]

    imported = 0
    for c in cases:
        obj = models.Case(
            folder_id=payload.folder_id,
            title=c.get("title", "未命名用例"),
            case_type=c.get("case_type", "manual"),
            priority=c.get("priority", "P2"),
            tags=(c.get("tags") or []) + ["AI生成", f"生成#{gid}"],
            precondition=c.get("precondition", ""),
            steps=c.get("steps", ""),
            expected=c.get("expected", ""),
        )
        if obj.case_type == "api":
            # 接口用例透传可执行配置，导入后可直接在接口测试/批量执行中运行
            obj.method = str(c.get("method", "GET")).upper()
            obj.url = c.get("url", "")
            obj.headers = c.get("headers") or {"Content-Type": "application/json"}
            obj.body = c.get("body", "")
            obj.assertions = c.get("assertions") or []
            obj.extractors = c.get("extractors") or []
        db.add(obj)
        imported += 1
    r.imported = True
    db.commit()
    return {"ok": True, "imported": imported}


# ============================================================
# Element locator extraction
# ============================================================
@app.post("/api/locator/extract")
def locator_extract(payload: schemas.LocatorExtractRequest):
    """Open the URL in a real browser, match elements by keyword, and generate
    role → css → xpath locators with uniqueness verification."""
    url = (payload.url or "").strip()
    keyword = (payload.keyword or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "网址必须以 http:// 或 https:// 开头")
    if not keyword:
        raise HTTPException(400, "请输入要查找的元素关键词")
    if len(keyword) > 100:
        raise HTTPException(400, "关键词过长")

    if not locator_extractor._LOCK.acquire(blocking=False):
        raise HTTPException(409, "已有提取任务正在运行（每次会打开一个真实浏览器），请稍后再试")
    try:
        # 加载已保存的登录态（cookies / localStorage），无需再次输入账号密码
        state = None
        session_name = (payload.session_name or "").strip()
        if session_name:
            state = browser_session.state_path(session_name)
            if not os.path.exists(state):
                raise HTTPException(404, f"登录态「{session_name}」不存在，请重新创建")
        try:
            return locator_extractor.extract_locators(
                url=url,
                keyword=keyword,
                exact=payload.exact,
                wait_ms=payload.wait_ms,
                steps=[s.model_dump() for s in payload.steps],
                storage_state=state,
            )
        except HTTPException:
            raise
        except Exception as e:
            msg = str(e).split("\n")[0][:300]
            raise HTTPException(500, f"提取失败: {msg}")
    finally:
        locator_extractor._LOCK.release()


# ============================================================
# Interactive browser session (user operates visibly, then locates)
# ============================================================
@app.post("/api/locator/interactive/start")
def interactive_start(payload: dict):
    url = (payload.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "网址必须以 http:// 或 https:// 开头")
    try:
        return interactive_session.start_session(url)
    except Exception as e:
        raise HTTPException(500, f"打开浏览器失败: {str(e).split(chr(10))[0][:300]}")


@app.get("/api/locator/interactive/{sid}/status")
def interactive_status(sid: str):
    try:
        return interactive_session.session_status(sid)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/locator/interactive/{sid}/locate")
def interactive_locate(sid: str, payload: dict):
    keyword = (payload.get("keyword") or "").strip()
    if not keyword:
        raise HTTPException(400, "请输入元素关键词")
    if len(keyword) > 100:
        raise HTTPException(400, "关键词过长")
    try:
        reply = interactive_session.locate(sid, keyword, bool(payload.get("exact", False)))
    except (ValueError, TimeoutError) as e:
        raise HTTPException(400, str(e))
    if not reply.get("ok"):
        raise HTTPException(500, reply.get("error", "定位失败"))
    return reply["data"]


@app.post("/api/locator/interactive/{sid}/close")
def interactive_close(sid: str):
    return interactive_session.close_session(sid)


@app.get("/api/locator/sessions")
def list_login_sessions():
    """列出已保存的登录态。"""
    return {"sessions": browser_session.list_states()}


@app.post("/api/locator/sessions")
def start_login_session(payload: schemas.LoginSessionStart):
    """打开一个可见浏览器，让用户亲自登录（支持验证码/扫码/SSO）。"""
    url = (payload.url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "网址必须以 http:// 或 https:// 开头")
    try:
        return browser_session.start_login(payload.name, url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        msg = str(e).split("\n")[0][:300]
        raise HTTPException(500, f"打开浏览器失败: {msg}")


@app.post("/api/locator/sessions/{session_id}/complete")
def complete_login_session(session_id: str):
    """用户完成登录后调用：保存 cookies / localStorage 为登录态文件。"""
    try:
        return browser_session.complete_login(session_id)
    except (ValueError, TimeoutError) as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"保存登录态失败: {e}")


@app.get("/api/locator/sessions/{session_id}/status")
def login_session_status(session_id: str):
    try:
        return browser_session.session_status(session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.delete("/api/locator/sessions/{name}")
def delete_login_session(name: str):
    ok = browser_session.delete_state(name)
    if not ok:
        raise HTTPException(404, "登录态不存在")
    return {"ok": True}


# ============================================================
# Dashboard
# ============================================================
@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    project_count = db.query(func.count(models.Project.id)).scalar()
    case_count = db.query(func.count(models.Case.id)).scalar()
    api_count = db.query(func.count(models.Case.id)).filter(models.Case.case_type == "api").scalar()
    ui_count = db.query(func.count(models.Case.id)).filter(models.Case.case_type == "ui").scalar()
    run_count = db.query(func.count(models.Run.id)).scalar()
    recent = db.query(models.Run).order_by(models.Run.id.desc()).limit(8).all()
    trend = [{
        "id": r.id, "passed": r.passed, "failed": r.failed,
        "total": r.total, "start_time": r.start_time.isoformat() if r.start_time else None,
    } for r in reversed(recent)]
    return {
        "project_count": project_count, "case_count": case_count,
        "api_count": api_count, "ui_count": ui_count, "run_count": run_count,
        "trend": trend,
    }


# ============================================================
# Demo seed data
# ============================================================
def seed_demo_data():
    db = SessionLocal()
    try:
        if db.query(models.Project).count() > 0:
            return
        p = models.Project(name="电商系统", description="Web + 接口测试演示项目")
        db.add(p)
        db.flush()
        f1 = models.Folder(project_id=p.id, name="用户模块")
        f2 = models.Folder(project_id=p.id, name="商品模块")
        f3 = models.Folder(project_id=p.id, parent_id=f1.id, name="登录相关")
        db.add_all([f1, f2, f3])
        db.flush()

        cases = [
            models.Case(folder_id=f3.id, title="登录成功 - 正确账号密码", case_type="api", priority="P0",
                        tags=["登录", "冒烟"], method="POST", url="/api/login",
                        headers={"Content-Type": "application/json"},
                        body='{"username":"admin","password":"123456"}',
                        assertions=[{"type": "status", "op": "eq", "value": "200"},
                                    {"type": "json", "key": "code", "op": "eq", "value": "0"}],
                        extractors=[{"name": "token", "source": "json", "key": "data.token"}],
                        expected="返回 200，code=0，提取 token"),
            models.Case(folder_id=f3.id, title="登录失败 - 错误密码", case_type="api", priority="P1",
                        tags=["登录", "异常"], method="POST", url="/api/login",
                        headers={"Content-Type": "application/json"},
                        body='{"username":"admin","password":"wrong"}',
                        assertions=[{"type": "json", "key": "code", "op": "eq", "value": "401"}]),
            models.Case(folder_id=f1.id, title="获取用户信息", case_type="api", priority="P1",
                        tags=["用户"], method="GET", url="/api/user/info",
                        headers={"Authorization": "Bearer {{token}}"},
                        assertions=[{"type": "status", "op": "eq", "value": "200"}]),
            models.Case(folder_id=f2.id, title="商品列表 - 分页查询", case_type="api", priority="P1",
                        tags=["商品"], method="GET", url="/api/products?page=1&size=10",
                        assertions=[{"type": "status", "op": "eq", "value": "200"},
                                    {"type": "json", "key": "data.length", "op": "gte", "value": "5"}]),
            models.Case(folder_id=f2.id, title="搜索商品 - 关键字为空", case_type="api", priority="P2",
                        tags=["商品", "异常"], method="GET", url="/api/products?keyword=",
                        assertions=[{"type": "status", "op": "eq", "value": "200"}]),
            models.Case(folder_id=f1.id, title="用户登录 UI 流程", case_type="ui", priority="P0",
                        tags=["登录", "冒烟"],
                        steps='[{"action":"goto","target":"https://example.com/login"},{"action":"fill","target":"#username","value":"admin"},{"action":"fill","target":"#password","value":"123456"},{"action":"click","target":"button[type=submit]"},{"action":"assert_visible","target":".dashboard","screenshot":true}]',
                        expected="登录后跳转首页并截图"),
            models.Case(folder_id=f2.id, title="手工探索 - 商品详情页展示", case_type="manual", priority="P2",
                        tags=["探索"], precondition="已登录", steps="1. 打开商品详情\n2. 检查图片与价格",
                        expected="信息展示正确"),
        ]
        db.add_all(cases)
        db.flush()

        env = models.Environment(name="本地 Mock", base_url="http://127.0.0.1:9001",
                                 variables={"token": "demo-token", "page": "1"})
        db.add(env)
        db.flush()
        db.add(models.Suite(project_id=p.id, name="接口冒烟测试集",
                            case_ids=[c.id for c in cases[:5]], env_id=env.id))
        db.commit()
    finally:
        db.close()


# ============================================================
# Serve frontend build (if present)
# ============================================================
# locator extraction screenshots (must be registered before the SPA catch-all)
app.mount("/shots", StaticFiles(directory=locator_extractor.SHOTS_BASE), name="shots")

FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """SPA fallback: serve index.html for frontend routes."""
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
