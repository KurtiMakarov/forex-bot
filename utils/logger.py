import os
import logging
from datetime import datetime, timedelta


def _ensure_log_dirs():
    os.makedirs("logs", exist_ok=True)
    os.makedirs("logs/runs", exist_ok=True)


def _run_log_file():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join("logs", "runs", f"bot_run_{ts}.log")


def _cleanup_old_run_logs(keep_days: int = 30):
    """
    Auto-delete run logs older than keep_days.
    Safe-fail: никога не чупи старта на бота при грешка.
    """
    runs_dir = os.path.join("logs", "runs")
    if not os.path.isdir(runs_dir):
        return

    cutoff = datetime.now() - timedelta(days=keep_days)

    for fname in os.listdir(runs_dir):
        if not fname.endswith(".log"):
            continue
        fpath = os.path.join(runs_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
        except Exception:
            # ignore individual file errors
            pass


# Един run-файл за текущия процес (създава се при import)
_RUN_LOG_FILE = None


def setup_logger(name: str = "bot", level: int = logging.INFO) -> logging.Logger:
    global _RUN_LOG_FILE

    _ensure_log_dirs()

    # Колко дни да се пазят run логовете (env override, default=30)
    keep_days_env = os.getenv("LOG_RETENTION_DAYS", "30")
    try:
        keep_days = max(1, int(keep_days_env))
    except Exception:
        keep_days = 30

    _cleanup_old_run_logs(keep_days=keep_days)

    if _RUN_LOG_FILE is None:
        _RUN_LOG_FILE = _run_log_file()

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Ако вече има handler-и, не добавяй дублиращи
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # 1) Console
    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # 2) Global log
    fh_all = logging.FileHandler(os.path.join("logs", "app.log"), encoding="utf-8")
    fh_all.setLevel(level)
    fh_all.setFormatter(fmt)
    logger.addHandler(fh_all)

    # 3) Per-run log
    fh_run = logging.FileHandler(_RUN_LOG_FILE, encoding="utf-8")
    fh_run.setLevel(level)
    fh_run.setFormatter(fmt)
    logger.addHandler(fh_run)

    logger.info(f"🗂️ Run log file: {_RUN_LOG_FILE}")
    logger.info(f"🧹 Log retention: {keep_days} days")
    return logger