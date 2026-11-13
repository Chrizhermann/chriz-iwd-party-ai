import os
import shutil
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MOD_FOLDER_NAME = "chriz-iwd-party-ai"
MOD_DIR = REPO_ROOT / MOD_FOLDER_NAME
DEFAULT_WEIDU_CANDIDATES = (
    Path(r"C:\src\private\chriz-bg-rebalance\weidu.exe"),
    REPO_ROOT / "weidu.exe",
)
IWD_CLEAN_DIR = Path(r"C:\Games\Icewind Dale Enhanced Edition")


def find_weidu_exe() -> Path:
    env_val = os.environ.get("WEIDU_EXE") or os.environ.get("BGSE_WEIDU")
    if env_val:
        p = Path(env_val)
        if p.is_file():
            return p
    which_val = shutil.which("weidu")
    if which_val:
        return Path(which_val)
    for candidate in DEFAULT_WEIDU_CANDIDATES:
        if candidate.is_file():
            return candidate
    pytest.skip("weidu.exe not found (set WEIDU_EXE)")


@pytest.fixture(scope="session")
def weidu_exe() -> Path:
    return find_weidu_exe()
