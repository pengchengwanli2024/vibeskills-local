"""Read enabled Codex plugin versions, then inspect only their declared Skills.

The cache is storage, not an installation registry. Never infer activation from
directory names, install markers, or the greatest cached version.
"""
from __future__ import annotations

import json
import os
from pathlib import Path, PureWindowsPath
import queue
import shutil
import subprocess
import threading
import time


IGNORED_DIRS = frozenset({".git", "node_modules", ".venv", "venv", "__pycache__"})
INVENTORY_TIMEOUT = 20.0


def _installed_plugins(cache_root: Path, workspace_root: Path | None) -> dict:
    """Query the host's read-only registry without reading credentials ourselves."""
    executable = cache_root.parent / ".plugin-appserver" / ("codex.exe" if os.name == "nt" else "codex")
    command = str(executable) if executable.is_file() else shutil.which("codex.exe") or shutil.which("codex")
    if not command or Path(command).suffix.casefold() in {".cmd", ".bat"}:
        raise RuntimeError("Codex app-server executable is unavailable")
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(cache_root.parents[1].resolve())
    messages: queue.Queue = queue.Queue()
    process = subprocess.Popen(
        [command, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="strict",
        env=environment,
    )

    def receive() -> None:
        try:
            for line in process.stdout:
                messages.put(json.loads(line))
        except (OSError, ValueError) as exc:
            messages.put(exc)
        finally:
            messages.put(None)

    reader = threading.Thread(target=receive, daemon=True)
    reader.start()
    deadline = time.monotonic() + INVENTORY_TIMEOUT

    def send(payload: dict) -> None:
        process.stdin.write(json.dumps(payload) + "\n")
        process.stdin.flush()

    def request(identity: int, method: str, params: dict) -> dict:
        send({"id": identity, "method": method, "params": params})
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Codex plugin inventory timed out")
            try:
                item = messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError("Codex plugin inventory timed out") from exc
            if not isinstance(item, dict):
                raise RuntimeError("Codex plugin inventory stream ended or was invalid")
            if item.get("id") != identity:
                continue
            if "error" in item or not isinstance(item.get("result"), dict):
                raise RuntimeError("Codex plugin inventory request failed")
            return item["result"]

    try:
        request(1, "initialize", {
            "clientInfo": {"name": "vibe-plugin-discovery", "version": "1"},
            "capabilities": {"experimentalApi": True, "explicitGatewayOauth": True},
        })
        send({"method": "initialized"})
        cwd = workspace_root.resolve() if workspace_root is not None else Path.cwd().resolve()
        inventory = request(2, "plugin/installed", {"cwds": [str(cwd)]})
        skills = request(3, "skills/list", {"cwds": [str(cwd)], "forceReload": False})
        if not isinstance(skills.get("data"), list) or not skills["data"]:
            raise ValueError("Codex Skill inventory is missing")
        disabled = []
        for row in skills["data"]:
            if (not isinstance(row, dict) or not isinstance(row.get("skills"), list)
                    or not isinstance(row.get("errors"), list) or row["errors"]):
                raise ValueError("Codex Skill inventory is incomplete or invalid")
            for skill in row["skills"]:
                if (not isinstance(skill, dict) or not isinstance(skill.get("enabled"), bool)
                        or not isinstance(skill.get("path"), str)):
                    raise ValueError("Codex Skill inventory entry is invalid")
                if skill["enabled"] is False:
                    disabled.append(skill["path"])
        inventory["disabled_skill_paths"] = disabled
        return inventory
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        reader.join(timeout=1)
        process.stdin.close()
        process.stdout.close()


def codex_host_inventory(cache_root: Path, workspace_root: Path | None = None) -> dict:
    """Fetch plugin versions and disabled ordinary Skill paths in one host session.

    Errors propagate to the caller; an unavailable registry is not an empty one.
    """
    return _installed_plugins(cache_root.resolve(), workspace_root)


def _component(value: object) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or value in {".", ".."} or any(c in value for c in "/\\\0")
            or PureWindowsPath(value).drive):
        raise ValueError("Invalid plugin registry path component")
    return value


def _contained(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Plugin path escapes its declared root")
    return resolved


def _manifest_roots(plugin: Path) -> list[Path]:
    manifests = [plugin / "plugin.json", plugin / ".codex-plugin/plugin.json"]
    declarations: object = "./skills"
    found = False
    for path in manifests:
        if not path.is_file():
            continue
        _contained(path, plugin)
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict) or not isinstance(payload.get("name"), str) or not payload["name"].strip():
            raise ValueError("Plugin manifest must be an object with a name")
        found = True
        if "skills" in payload:
            declarations = payload["skills"]
    if not found:
        raise ValueError("Installed plugin manifest is missing")
    values = [declarations] if isinstance(declarations, str) else declarations
    if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Plugin skills declaration must be a path or list of paths")
    roots = []
    for value in values:
        portable = value.replace("\\", "/")
        if Path(portable).is_absolute() or PureWindowsPath(value).is_absolute() or PureWindowsPath(value).drive:
            raise ValueError("Plugin skills declaration must be relative")
        candidate = plugin / portable
        root = _contained(candidate, plugin)
        if any(part.casefold() in IGNORED_DIRS for part in Path(portable).parts):
            raise ValueError("Plugin skills declaration points into a dependency directory")
        roots.append(root)
    return roots


def discover_codex_plugin_skills(
    cache_root: Path, workspace_root: Path | None = None, *, inventory: dict | None = None,
) -> tuple[list[Path], list[dict[str, object]]]:
    """Return direct Skill directories of exact installed, enabled plugin versions."""
    cache_root = cache_root.resolve()
    diagnostics: list[dict[str, object]] = []

    def diagnostic(reason: str, path: Path, message: str) -> None:
        diagnostics.append({"reason": reason, "path": str(path), "message": message})

    try:
        inventory = codex_host_inventory(cache_root, workspace_root) if inventory is None else inventory
        if not isinstance(inventory, dict) or not isinstance(inventory.get("marketplaces"), list) or inventory.get("marketplaceLoadErrors"):
            raise ValueError("Codex plugin inventory is incomplete or invalid")
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        diagnostic("plugin_inventory_unavailable", cache_root, str(exc))
        return [], diagnostics

    discovered: set[Path] = set()
    for marketplace in inventory["marketplaces"]:
        try:
            market_name = _component(marketplace.get("name"))
            plugins = marketplace.get("plugins")
            if not isinstance(plugins, list):
                raise ValueError("Marketplace plugins must be a list")
        except (AttributeError, ValueError) as exc:
            diagnostic("invalid_plugin_inventory", cache_root, str(exc))
            continue
        for row in plugins:
            plugin_path = cache_root / market_name
            try:
                if not isinstance(row, dict):
                    raise ValueError("Plugin registry entry must be an object")
                if row.get("installed") is not True or row.get("enabled") is not True:
                    continue
                name = _component(row.get("name"))
                source = row.get("source")
                if not isinstance(source, dict) or source.get("type") not in {"remote", "local"}:
                    raise ValueError("Plugin registry source type is missing or unsupported")
                # Remote versions identify the installed release; localVersion
                # identifies the materialized version of local/bundled plugins.
                version = row.get("version") if source.get("type") == "remote" else row.get("localVersion") or row.get("version")
                version = _component(version)
                plugin_path = cache_root / market_name / name / version
                plugin = _contained(plugin_path, cache_root)
                if plugin != plugin_path.absolute() or not plugin.is_dir():
                    raise ValueError("Exact installed plugin version is absent or linked")
                plugin_skills: set[Path] = set()
                for declared in _manifest_roots(plugin):
                    if declared.is_file():
                        candidates = [declared] if declared.name == "SKILL.md" else []
                    elif (declared / "SKILL.md").is_file():
                        candidates = [declared / "SKILL.md"]
                    elif declared.is_dir():
                        candidates = [child / "SKILL.md" for child in declared.iterdir()
                                      if child.is_dir() and child.name.casefold() not in IGNORED_DIRS]
                    else:
                        candidates = []
                    for descriptor in candidates:
                        if not descriptor.is_file():
                            continue
                        descriptor = _contained(descriptor, plugin)
                        _contained(descriptor, declared if declared.is_dir() else declared.parent)
                        plugin_skills.add(descriptor.parent)
                discovered.update(plugin_skills)
            except (OSError, ValueError, AttributeError) as exc:
                diagnostic("invalid_installed_plugin", plugin_path, str(exc))
    return sorted(discovered), diagnostics
