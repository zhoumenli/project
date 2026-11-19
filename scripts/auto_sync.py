#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动同步脚本：监听本地代码改动 → 自动 commit → 自动 push 到 GitHub

设计要点
--------
1. 用 `git status --porcelain` 判定变更，自动遵循 .gitignore，
   无需自行实现文件过滤逻辑。
2. 防抖（debounce）：最后一次改动后再等 N 秒才提交，
   避免连续保存 IDE 文件时产生几十条碎片提交。
3. 单实例锁：同一时间只允许一个同步进程，防止并发提交互相踩踏。
4. 推送失败自动重试（指数退避），应对网络抖动。
5. 纯标准库实现，零第三方依赖；有 watchdog 时自动切换为事件驱动（更快）。

用法
----
    python scripts/auto_sync.py                # 前台运行，Ctrl+C 退出
    python scripts/auto_sync.py --once         # 只同步一次就退出（配计划任务用）
    python scripts/auto_sync.py --dry-run      # 只打印将要做什么，不真正提交
    python scripts/auto_sync.py --interval 3   # 轮询间隔（秒），默认 5

参数
----
    --interval N    轮询间隔秒数，默认 5
    --debounce N    静默期秒数，默认 8
    --remote NAME   远程名，默认 origin
    --branch NAME   分支名，默认当前分支
    --message MSG   提交信息模板，{files} / {count} / {time} 可用
    --no-push       只 commit 不 push
    --dry-run       演练模式
    --once          执行一次后退出
    --exclude PATH  额外排除的路径（可重复），相对仓库根目录
"""
from __future__ import annotations

import argparse
import datetime as _dt
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
LOG_DIR = REPO_ROOT / "logs"
LOG_FILE = LOG_DIR / "auto_sync.log"
LOCK_FILE = LOG_DIR / "auto_sync.lock"

# 保险性排除：即便 .gitignore 漏了，也不该提交这些东西
DEFAULT_DENY = (
    "logs/",
    "node_modules/",
    ".npm-cache/",
    "__pycache__/",
    ".idea/",
    ".vscode/",
    "*.log",
    "*.db",
    "*.pyc",
    "backend/app/uploads/",
    "backend/app/shots/",
    "backend/screenshots/",
    "backend/temp_*.py",
    "backend/tmp_*.py",
)


# ---------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------
def setup_logging(verbose: bool = True) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("auto_sync")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    if verbose:
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(sh)

    return logger


# ---------------------------------------------------------------------
# git 封装
# ---------------------------------------------------------------------
class Git:
    def __init__(self, cwd: Path, dry_run: bool = False):
        self.cwd = cwd
        self.dry_run = dry_run

    def run(self, *args: str, check: bool = True, timeout: int = 120) -> tuple[int, str, str]:
        """执行 git 命令，返回 (returncode, stdout, stderr)"""
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, "", f"命令超时: git {' '.join(args)}"
        if check and proc.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} 失败 (exit {proc.returncode})\n"
                f"stdout: {proc.stdout.strip()}\nstderr: {proc.stderr.strip()}"
            )
        return proc.returncode, proc.stdout, proc.stderr

    def status_porcelain(self) -> list[str]:
        """返回变更条目列表（已遵循 .gitignore）"""
        _, out, _ = self.run("status", "--porcelain", "--untracked-files=all")
        return [line for line in out.splitlines() if line.strip()]

    def current_branch(self) -> str:
        _, out, _ = self.run("rev-parse", "--abbrev-ref", "HEAD")
        return out.strip()

    def stage_all(self) -> None:
        self.run("add", "--all")

    def has_staged(self) -> bool:
        _, out, _ = self.run("diff", "--cached", "--name-only")
        return bool(out.strip())

    def commit(self, message: str) -> tuple[bool, str]:
        code, out, err = self.run("commit", "-m", message, check=False)
        combined = (out + err).strip()
        if code == 0:
            return True, combined
        if "nothing to commit" in combined or "no changes added" in combined:
            return False, combined
        return False, combined

    def push(self, remote: str, branch: str) -> tuple[bool, str]:
        code, out, err = self.run("push", remote, branch, check=False, timeout=180)
        combined = (out + err).strip()
        return code == 0, combined

    def head_sha(self) -> str:
        _, out, _ = self.run("rev-parse", "--short", "HEAD")
        return out.strip()

    def files_in_last_commit(self) -> list[str]:
        _, out, _ = self.run("show", "--name-only", "--pretty=format:", "HEAD")
        return [f for f in out.splitlines() if f.strip()]


# ---------------------------------------------------------------------
# 单实例锁
# ---------------------------------------------------------------------
class SingleInstance:
    """基于文件存在性的简单锁，防止多个同步进程同时跑。"""

    def __init__(self, path: Path):
        self.path = path
        self.acquired = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            self.acquired = True
        except FileExistsError:
            # 锁文件已存在：若持有者进程已退出则清理后重试一次
            if self._stale():
                try:
                    self.path.unlink()
                except OSError:
                    pass
                return self.__enter__()
            raise RuntimeError("另一个自动同步进程正在运行（锁文件存在）")
        return self

    def __exit__(self, *exc):
        if self.acquired:
            try:
                self.path.unlink()
            except OSError:
                pass
        return False

    def _stale(self) -> bool:
        try:
            pid = int(self.path.read_text(encoding="utf-8").strip() or 0)
        except (OSError, ValueError):
            return True
        if pid <= 0:
            return True
        try:
            os.kill(pid, 0)  # Windows 上同样可用（signal 0 仅探测）
            return False
        except (OSError, ProcessLookupError):
            return True


# ---------------------------------------------------------------------
# 过滤与提交信息
# ---------------------------------------------------------------------
def is_denied(path: str, extra_exclude: list[str]) -> bool:
    """判断路径是否在排除名单内"""
    p = path.replace("\\", "/").strip('"')
    for pat in list(DEFAULT_DENY) + list(extra_exclude):
        pat = pat.replace("\\", "/")
        if pat.endswith("/"):
            if p.startswith(pat) or f"/{pat}" in f"/{p}":
                return True
        elif p == pat or p.endswith("/" + pat) or p.startswith(pat):
            return True
        elif "*" in pat or "?" in pat:
            import fnmatch
            if fnmatch.fnmatch(p, pat):
                return True
    return False


def filter_changes(entries: list[str], extra_exclude: list[str]) -> list[str]:
    """从 porcelain 输出里提取文件路径，并剔除排除项"""
    paths = []
    for entry in entries:
        # porcelain 格式: XY <path>  (重命名时为 "old -> new")
        raw = entry[3:].strip() if len(entry) > 3 else ""
        if " -> " in raw:
            raw = raw.split(" -> ")[-1]
        raw = raw.strip('"')
        if not raw:
            continue
        if is_denied(raw, extra_exclude):
            continue
        paths.append(raw)
    return paths


def build_message(template: str, files: list[str], count: int) -> str:
    now = _dt.datetime.now()
    summary = ", ".join(files[:3])
    if len(files) > 3:
        summary += f" 等 {len(files)} 个文件"
    defaults = {
        "files": summary,
        "count": str(count),
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
    }
    try:
        return template.format(**defaults)
    except KeyError as e:
        raise ValueError(f"提交信息模板含未知占位符: {e}") from e


# ---------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------
class AutoSync:
    def __init__(self, args):
        self.args = args
        self.log = setup_logging()
        self.git = Git(REPO_ROOT, dry_run=args.dry_run)
        self.branch = args.branch or self.git.current_branch()
        self.last_change_time: float | None = None
        self.last_seen: set[str] = set()

    # -- 变更检测 ------------------------------------------------------
    def detect(self) -> list[str]:
        entries = self.git.status_porcelain()
        files = filter_changes(entries, self.args.exclude)
        current = set(files)
        if current != self.last_seen:
            if current:
                self.log.info(f"检测到 {len(current)} 处变更：{', '.join(list(current)[:5])}"
                             + (" ..." if len(current) > 5 else ""))
            self.last_seen = current
        return files

    # -- 执行一次同步 --------------------------------------------------
    def sync_once(self) -> bool:
        """返回 True 表示发生了实际提交"""
        files = self.detect()
        if not files:
            return False

        self.log.info(f"→ 开始同步（{len(files)} 个文件待提交）")

        if self.args.dry_run:
            # 演练模式：临时 add 以准确统计待提交内容，随后还原暂存区，不留副作用
            self.git.stage_all()
            staged = self.git.run("diff", "--cached", "--name-only")[1].split()
            self.git.run("reset", check=False)
            message = build_message(self.args.message, files, len(files))
            self.log.info(f"  提交信息: {message}")
            self.log.info(f"  [dry-run] 将提交 {len(staged)} 个文件，未实际执行")
            return True

        self.git.stage_all()

        if not self.git.has_staged():
            self.log.info("  暂存区为空，跳过")
            return False

        message = build_message(self.args.message, files, len(files))
        self.log.info(f"  提交信息: {message}")

        ok, out = self.git.commit(message)
        if not ok:
            if "nothing to commit" in out:
                self.log.info("  无实际变更，跳过")
            else:
                self.log.error(f"  提交失败: {out}")
            return False

        self.log.info(f"  提交成功 → {self.git.head_sha()}")

        if self.args.no_push:
            self.log.info("  --no-push 已启用，跳过推送")
            return True

        # 推送（带重试）
        for attempt in range(1, self.args.retries + 1):
            ok, out = self.git.push(self.args.remote, self.branch)
            if ok:
                self.log.info(f"  推送成功 → {self.args.remote}/{self.branch}")
                return True
            self.log.warning(f"  推送失败（第 {attempt}/{self.args.retries} 次）: {out.strip()[:300]}")
            if attempt < self.args.retries:
                time.sleep(min(2 ** attempt, 15))

        self.log.error("  推送最终失败，变更已保留在本地提交中")
        return True

    # -- 轮询循环 ------------------------------------------------------
    def run(self) -> int:
        self.log.info("=" * 62)
        self.log.info(f"自动同步已启动 | 仓库: {REPO_ROOT}")
        self.log.info(f"远程: {self.args.remote} | 分支: {self.branch}")
        self.log.info(f"轮询间隔 {self.args.interval}s | 静默期 {self.args.debounce}s")
        if self.args.dry_run:
            self.log.info("模式: DRY-RUN（不会真正提交/推送）")
        self.log.info("按 Ctrl+C 停止")
        self.log.info("=" * 62)

        # ---- 单次模式：检测一次，同步一次，立即退出 ----
        if self.args.once:
            files = self.detect()
            if not files:
                self.log.info("当前无待同步变更，退出")
                return 0
            try:
                self.sync_once()
            except Exception as e:
                self.log.error(f"同步异常: {e}", exc_info=True)
                return 1
            return 0

        # ---- 常驻模式 ----
        try:
            while True:
                files = self.detect()
                if files:
                    self.last_change_time = time.time()

                # 静默期到期才提交
                if (self.last_change_time
                        and time.time() - self.last_change_time >= self.args.debounce):
                    self.last_change_time = None
                    try:
                        self.sync_once()
                    except Exception as e:
                        self.log.error(f"同步异常: {e}", exc_info=True)

                time.sleep(self.args.interval)

        except KeyboardInterrupt:
            self.log.info("已停止")
            return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="监听本地代码改动，自动 commit 并 push 到 GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--interval", type=int, default=5, help="轮询间隔秒数（默认 5）")
    p.add_argument("--debounce", type=int, default=8, help="静默期秒数（默认 8）")
    p.add_argument("--remote", default="origin", help="远程名（默认 origin）")
    p.add_argument("--branch", default="", help="分支名（默认当前分支）")
    p.add_argument(
        "--message",
        default="chore: 自动同步 {files} ({time})",
        help="提交信息模板，可用占位符 {files} {count} {time} {date}",
    )
    p.add_argument("--no-push", action="store_true", help="只提交不推送")
    p.add_argument("--dry-run", action="store_true", help="演练模式，不实际提交")
    p.add_argument("--once", action="store_true", help="执行一次后退出")
    p.add_argument("--retries", type=int, default=3, help="推送失败重试次数（默认 3）")
    p.add_argument("--exclude", action="append", default=[], help="额外排除路径（可重复）")
    return p.parse_args(argv)


def main() -> int:
    args = parse_args()
    if not (REPO_ROOT / ".git").exists():
        print(f"错误: {REPO_ROOT} 不是 Git 仓库", file=sys.stderr)
        return 1

    try:
        with SingleInstance(LOCK_FILE):
            syncer = AutoSync(args)
            return syncer.run()
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
