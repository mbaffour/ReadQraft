from __future__ import annotations

import shutil
import subprocess

from app.config import mock_tools_enabled
from app.config import apply_tool_environment
from app.models.schemas import ToolStatus

TOOL_VERSION_ARGS = {
    "fastqc": ["--version"],
    "fastp": ["--version"],
    "multiqc": ["--version"],
    "cutadapt": ["--version"],
    "trimmomatic": ["-version"],
}

CORE_REQUIRED_TOOLS = {"fastqc", "multiqc"}
TRIMMING_TOOLS = {"fastp", "cutadapt"}


def check_tool(name: str) -> ToolStatus:
    apply_tool_environment()
    executable_name = "python" if name == "cutadapt" else name
    path = shutil.which(executable_name)
    required = False
    if not path:
        message = "Missing required tool." if required else "Optional tool not found."
        if mock_tools_enabled() and required:
            message += " Development mock mode is enabled."
        return ToolStatus(name=name, available=False, required=required, message=message)
    version = None
    try:
        cmd = [path, "-m", "cutadapt", *TOOL_VERSION_ARGS[name]] if name == "cutadapt" else [path, *TOOL_VERSION_ARGS[name]]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        output = (proc.stdout or proc.stderr).strip()
        if proc.returncode != 0:
            return ToolStatus(
                name=name,
                available=False,
                path=path,
                required=required,
                message=f"Found executable, but version check failed: {output.splitlines()[0] if output else 'no output'}",
            )
        version = output.splitlines()[0] if output else None
    except Exception as exc:  # pragma: no cover - defensive only
        return ToolStatus(name=name, available=True, path=path, required=required, message=f"Version check failed: {exc}")
    return ToolStatus(name=name, available=True, version=version, path=path, required=required)


def check_tools() -> list[ToolStatus]:
    items = [check_tool(name) for name in TOOL_VERSION_ARGS]
    by_name = {tool.name: tool for tool in items}
    for name in CORE_REQUIRED_TOOLS:
        by_name[name].required = True
    if by_name["fastp"].available:
        by_name["fastp"].required = True
    elif by_name["cutadapt"].available:
        by_name["cutadapt"].required = True
    else:
        by_name["fastp"].required = True
        by_name["cutadapt"].required = True
    return items


def tools_by_name() -> dict[str, ToolStatus]:
    return {tool.name: tool for tool in check_tools()}
