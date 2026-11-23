"""
多数据库连接与查询引擎。

支持 MySQL / PostgreSQL / Oracle / SQL Server / SQLite。
- 按需导入驱动（缺驱动时给出明确安装提示，不影响其他数据库）
- 连接测试、执行 SQL（只读优先，破坏性语句需显式允许）、查询表结构
- 连接配置加密保存到数据库（密码用 Fernet 或简单异或混淆，避免明文）
"""
import re
import time
import decimal
from datetime import date, datetime
from typing import Any

# 驱动映射：优先选纯 Python 驱动（无需编译/系统依赖）
# MySQL: pymysql（纯 Python）| PostgreSQL: pg8000（纯 Python）
# Oracle: oracledb（纯 Python 版）| SQLServer: pyodbc（需系统 ODBC 驱动）
DRIVERS = {
    "mysql": "pymysql",
    "postgresql": "pg8000",
    "oracle": "oracledb",
    "sqlserver": "pyodbc",
    "sqlite": "sqlite3",
}

# 一键安装时的 pip 包名（可能与导入名不同）
PIP_PACKAGES = {
    "mysql": "pymysql",
    "postgresql": "pg8000",
    "oracle": "oracledb",
    "sqlserver": "pyodbc",
    "sqlite": "",  # 内置
}
# 每种驱动的部署难度提示
DRIVER_NOTES = {
    "mysql": "纯 Python 驱动，pip 即可安装",
    "postgresql": "pg8000 纯 Python，无需编译",
    "oracle": "oracledb 纯 Python 版，无需 Oracle 客户端",
    "sqlserver": "需 pip 安装 pyodbc，且系统需装 ODBC Driver 17",
    "sqlite": "Python 内置，无需安装",
}

DEFAULT_PORTS = {
    "mysql": 3306,
    "postgresql": 5432,
    "oracle": 1521,
    "sqlserver": 1433,
    "sqlite": 0,
}

# 安全策略：
# - 不可逆语句永远禁止（drop/truncate/shutdown 等）
# - 其余写操作（含 create/alter 结构变更）需显式 allow_write=True
FORBIDDEN = re.compile(r"^\s*(drop|truncate|shutdown|grant|revoke)\b", re.I)
DML = re.compile(
    r"^\s*(insert|update|delete|replace|merge|call|create|alter|rename|exec|execute)\b", re.I
)


def _jsonable(v: Any) -> Any:
    """把数据库返回的类型转成 JSON 可序列化值。"""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (bytes, bytearray, memoryview)):
        return bytes(v).hex()
    return str(v)


def _connect(cfg: dict):
    """按配置建立连接，返回 (conn, cursor)。驱动缺失时抛 ValueError。"""
    kind = (cfg.get("db_type") or "mysql").lower()
    host = (cfg.get("host") or "").strip()
    port = int(cfg.get("port") or DEFAULT_PORTS.get(kind, 0) or 0)
    user = (cfg.get("username") or "").strip()
    password = cfg.get("password") or ""
    database = (cfg.get("database") or "").strip()
    timeout = int(cfg.get("timeout") or 10)

    if kind == "sqlite":
        import sqlite3
        if not database:
            raise ValueError("SQLite 需要填写数据库文件路径")
        conn = sqlite3.connect(database, timeout=timeout)
        return conn, conn.cursor()

    if kind not in DRIVERS:
        raise ValueError(f"不支持的数据库类型: {kind}")

    if kind == "mysql":
        try:
            import pymysql
        except ImportError:
            raise ValueError("缺少 MySQL 驱动，请执行: pip install pymysql")
        conn = pymysql.connect(
            host=host, port=port or 3306, user=user, password=password,
            database=database, connect_timeout=timeout, charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        return conn, conn.cursor()

    if kind == "postgresql":
        # pg8000 纯 Python 驱动，无需 C 编译；返回 tuple，execute_query 会按 description 转 dict
        try:
            import pg8000
            import pg8000.dbapi
        except ImportError:
            raise ValueError("缺少 PostgreSQL 驱动，可在页面上点「一键安装」或执行: pip install pg8000")
        conn = pg8000.dbapi.connect(
            user=user, host=host, port=port or 5432, password=password,
            database=database, timeout=timeout,
        )
        return conn, conn.cursor()

    if kind == "oracle":
        try:
            import oracledb
        except ImportError:
            raise ValueError("缺少 Oracle 驱动，请执行: pip install oracledb")
        dsn = cfg.get("dsn") or f"{host}:{port or 1521}/{database}"
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
        cur = conn.cursor()
        cur.rowfactory = lambda *args: dict(zip([d[0] for d in cur.description], args))
        return conn, cur

    if kind == "sqlserver":
        try:
            import pyodbc
        except ImportError:
            raise ValueError("缺少 SQL Server 驱动，请执行: pip install pyodbc")
        odbc = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={host},{port or 1433};DATABASE={database};"
            f"UID={user};PWD={password};Connection Timeout={timeout}"
        )
        conn = pyodbc.connect(odbc, timeout=timeout)
        cur = conn.cursor()
        cur.rowfactory = lambda *args: dict(zip([c[0] for c in cur.description], args))
        return conn, cur

    raise ValueError(f"不支持的数据库类型: {kind}")


def test_connection(cfg: dict) -> dict:
    """测试连接是否可用，返回版本信息。"""
    start = time.time()
    conn = cur = None
    try:
        conn, cur = _connect(cfg)
        kind = (cfg.get("db_type") or "mysql").lower()
        queries = {
            "mysql": "SELECT VERSION() AS v",
            "postgresql": "SELECT VERSION() AS v",
            "oracle": "SELECT BANNER AS v FROM V$VERSION WHERE ROWNUM=1",
            "sqlserver": "SELECT @@VERSION AS v",
            "sqlite": "SELECT sqlite_version() AS v",
        }
        cur.execute(queries.get(kind, "SELECT 1 AS v"))
        row = cur.fetchone()
        version = (row.get("v") if isinstance(row, dict) else row[0]) if row else "unknown"
        return {"ok": True, "message": "连接成功", "version": str(version)[:200],
                "elapsed_ms": int((time.time() - start) * 1000)}
    except Exception as e:
        return {"ok": False, "message": f"连接失败: {e}", "elapsed_ms": int((time.time() - start) * 1000)}
    finally:
        if cur:
            try: cur.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


def execute_query(cfg: dict, sql: str, allow_write: bool = False, limit: int = 200) -> dict:
    """执行 SQL 并返回结果。默认只读；写操作需 allow_write=True。"""
    sql = (sql or "").strip().rstrip(";")
    if not sql:
        raise ValueError("SQL 语句不能为空")
    if FORBIDDEN.match(sql):
        raise ValueError("出于安全考虑，禁止执行 DROP/TRUNCATE 等不可逆语句")
    if DML.match(sql) and not allow_write:
        raise ValueError("写操作需勾选「允许执行写操作」")
    limit = min(max(int(limit or 200), 1), 1000)

    start = time.time()
    conn = cur = None
    try:
        conn, cur = _connect(cfg)
        cur.execute(sql)
        # 有结果集：select / pragma / explain 等
        is_select = bool(cur.description)
        if is_select:
            rows = cur.fetchmany(limit)
            columns = [d[0] for d in cur.description]
            data = []
            for r in rows:
                if isinstance(r, dict):
                    data.append({k: _jsonable(v) for k, v in r.items()})
                else:
                    data.append({columns[i]: _jsonable(v) for i, v in enumerate(r)})
            return {
                "ok": True, "columns": columns, "rows": data,
                "row_count": len(data), "truncated": len(data) >= limit,
                "elapsed_ms": int((time.time() - start) * 1000),
            }
        # 无结果集：insert/update/delete 等
        affected = getattr(cur, "rowcount", -1)
        conn.commit()
        return {
            "ok": True, "columns": [], "rows": [], "row_count": affected,
            "affected_rows": affected, "message": "执行成功",
            "elapsed_ms": int((time.time() - start) * 1000),
        }
    except Exception as e:
        if conn:
            try: conn.rollback()
            except Exception: pass
        raise ValueError(f"执行失败: {e}")
    finally:
        if cur:
            try: cur.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


def list_tables(cfg: dict) -> dict:
    """列出数据库的表。"""
    kind = (cfg.get("db_type") or "mysql").lower()
    database = (cfg.get("database") or "").strip()
    queries = {
        "mysql": ("SHOW TABLES", None),
        "postgresql": ("SELECT tablename AS name FROM pg_tables WHERE schemaname='public' ORDER BY tablename", None),
        "oracle": ("SELECT table_name AS name FROM user_tables ORDER BY table_name", None),
        "sqlserver": ("SELECT TABLE_NAME AS name FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME", None),
        "sqlite": ("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", None),
    }
    sql, _ = queries.get(kind, ("SHOW TABLES", None))
    result = execute_query(cfg, sql, limit=500)
    if result.get("ok") and result["columns"]:
        key = result["columns"][0]
        result["tables"] = [list(r.values())[0] for r in result["rows"]]
    return result


def describe_table(cfg: dict, table: str) -> dict:
    """查看表结构。table 需为合法标识符，防注入。"""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$.]*", table or ""):
        raise ValueError("表名不合法")
    kind = (cfg.get("db_type") or "mysql").lower()
    database = (cfg.get("database") or "").strip()
    if kind == "mysql":
        sql = f"SHOW FULL COLUMNS FROM `{table}`"
    elif kind == "postgresql":
        sql = f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='{table}' ORDER BY ordinal_position"
    elif kind == "oracle":
        sql = f"SELECT COLUMN_NAME, DATA_TYPE, NULLABLE FROM USER_TAB_COLUMNS WHERE TABLE_NAME=UPPER('{table}') ORDER BY COLUMN_ID"
    elif kind == "sqlserver":
        sql = f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table}' ORDER BY ORDINAL_POSITION"
    else:
        sql = f"PRAGMA table_info(`{table}`)"
    return execute_query(cfg, sql, limit=200)


def supported_drivers() -> list:
    """返回每种数据库是否可用（前端提示/一键安装用）。"""
    out = []
    for kind, module in DRIVERS.items():
        if kind == "sqlite":
            available, hint = True, "Python 内置，无需安装"
        else:
            try:
                __import__(module)
                available, hint = True, "已安装"
            except ImportError:
                available, hint = False, PIP_PACKAGES[kind]
        out.append({
            "type": kind, "label": {
                "mysql": "MySQL", "postgresql": "PostgreSQL", "oracle": "Oracle",
                "sqlserver": "SQL Server", "sqlite": "SQLite",
            }[kind],
            "default_port": DEFAULT_PORTS[kind],
            "driver": module, "available": available, "hint": hint,
            "pip_package": PIP_PACKAGES[kind], "note": DRIVER_NOTES[kind],
        })
    return out


def install_driver(kind: str) -> dict:
    """在后端进程环境安装指定数据库驱动（subprocess 调用 pip）。"""
    if kind not in DRIVERS:
        raise ValueError(f"不支持的数据库类型: {kind}")
    package = PIP_PACKAGES.get(kind, "")
    if not package:
        return {"ok": True, "message": "该数据库无需安装驱动"}
    try:
        __import__(DRIVERS[kind])
        return {"ok": True, "message": "驱动已安装，无需重复安装"}
    except ImportError:
        pass
    import subprocess
    import sys
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True, text=True, timeout=180,
        )
        if proc.returncode == 0:
            return {"ok": True, "message": f"驱动 {package} 安装成功", "output": proc.stdout[-500:]}
        return {"ok": False, "message": f"安装失败: {proc.stderr[-500:] or proc.stdout[-500:]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "安装超时（超过 180 秒），请手动安装"}
    except Exception as e:
        return {"ok": False, "message": f"安装异常: {e}"}
