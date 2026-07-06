from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "ReadQraft"
APP_VERSION = "0.1.0"
HOST = "127.0.0.1"


def data_root() -> Path:
    configured = os.environ.get("READQRAFT_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".readqraft" / "projects").resolve()


def mock_tools_enabled() -> bool:
    # Default off so mock QC results are never produced silently. Set
    # READQRAFT_ALLOW_MOCK_TOOLS=1 explicitly to enable development mock mode.
    return os.environ.get("READQRAFT_ALLOW_MOCK_TOOLS", "0") == "1"


def apply_tool_environment() -> None:
    candidates = []
    configured = os.environ.get("READQRAFT_TOOL_ENV")
    if configured:
        candidates.append(Path(configured).expanduser())
    cwd = Path.cwd()
    candidates.extend([cwd / ".tools" / "readqraft-bio", cwd.parent / ".tools" / "readqraft-bio"])

    for env_dir in candidates:
        bin_dir = env_dir / "bin"
        if bin_dir.exists():
            current_path = os.environ.get("PATH", "")
            bin_text = str(bin_dir.resolve())
            if bin_text not in current_path.split(os.pathsep):
                os.environ["PATH"] = bin_text + os.pathsep + current_path
            java_home = env_dir / "lib" / "jvm"
            if java_home.exists() and not os.environ.get("JAVA_HOME"):
                os.environ["JAVA_HOME"] = str(java_home.resolve())
            return
