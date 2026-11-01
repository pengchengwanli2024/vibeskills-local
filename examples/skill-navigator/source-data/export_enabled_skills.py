#!/usr/bin/env python3
"""Export Codex's actual Skill registry and reconcile a Vibe index, read-only.

Python 3.10+, standard library only. No account/configuration files are read.
Only initialize, plugin/installed and skills/list RPCs are sent to app-server.
The protocol sequence follows Vibe's Apache-2.0 codex_plugins.py adapter;
the export, filtering and reconciliation logic are original navigator code.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time


SCHEMA = "skill_navigator_v1"


def registry_snapshot(binary: str, codex_home: Path, workspace: Path, timeout: float) -> tuple[dict, dict]:
    """Read both host registries in one bounded, explicitly terminated session."""
    messages: queue.Queue = queue.Queue()
    process = subprocess.Popen(
        [binary, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="strict",
        env=dict(os.environ, CODEX_HOME=str(codex_home)),
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
    deadline = time.monotonic() + timeout

    def send(payload: dict) -> None:
        process.stdin.write(json.dumps(payload) + "\n")
        process.stdin.flush()

    def request(identity: int, method: str, params: dict) -> dict:
        send({"id": identity, "method": method, "params": params})
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Codex registry request timed out")
            try:
                item = messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError("Codex registry request timed out") from exc
            if not isinstance(item, dict):
                raise RuntimeError("Codex registry stream ended or contained invalid JSON")
            if item.get("id") != identity:
                continue
            if "error" in item or not isinstance(item.get("result"), dict):
                raise RuntimeError(f"Codex registry rejected {method}")
            return item["result"]

    try:
        request(1, "initialize", {
            "clientInfo": {"name": "skill-navigator-readonly", "version": "1"},
            "capabilities": {"experimentalApi": True, "explicitGatewayOauth": True},
        })
        send({"method": "initialized"})
        plugins = request(2, "plugin/installed", {"cwds": [str(workspace)]})
        skills = request(3, "skills/list", {"cwds": [str(workspace)], "forceReload": True})
        return plugins, skills
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


def host_rows(payload: dict) -> list[dict]:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("Host Skill registry has no data rows")
    result: dict[str, dict] = {}
    for row in data:
        if (not isinstance(row, dict) or not isinstance(row.get("errors"), list)
                or row["errors"] or not isinstance(row.get("skills"), list)):
            raise ValueError("Host Skill registry is incomplete; export refused")
        for skill in row["skills"]:
            if (not isinstance(skill, dict) or not isinstance(skill.get("enabled"), bool)
                    or not isinstance(skill.get("name"), str) or not skill["name"]
                    or not isinstance(skill.get("path"), str)):
                raise ValueError("Malformed host Skill entry")
            path = Path(skill["path"])
            if not path.is_absolute() or path.name != "SKILL.md":
                raise ValueError("Host Skill entrypoint must be an absolute SKILL.md path")
            key = str(path.absolute())
            if key in result and result[key] != skill:
                raise ValueError("Conflicting host entries for the same Skill path")
            result[key] = skill
    return sorted(result.values(), key=lambda r: (r["name"].casefold(), r["path"]))


def plugin_summary(payload: dict) -> tuple[list[dict], int]:
    if (not isinstance(payload.get("marketplaces"), list)
            or payload.get("marketplaceLoadErrors")):
        raise ValueError("Plugin registry is incomplete; export refused")
    plugins = []
    inactive = 0
    for market in payload["marketplaces"]:
        if not isinstance(market, dict) or not isinstance(market.get("plugins"), list):
            raise ValueError("Malformed plugin marketplace row")
        for plugin in market["plugins"]:
            if not isinstance(plugin, dict):
                raise ValueError("Malformed installed plugin row")
            if plugin.get("installed") is True and plugin.get("enabled") is True:
                source_type = (plugin.get("source") or {}).get("type", "unknown")
                version = (plugin.get("version") if source_type == "remote"
                           else plugin.get("localVersion") or plugin.get("version"))
                plugins.append({"marketplace": market.get("name", ""),
                                "name": plugin.get("name", ""),
                                "version": version, "source_type": source_type})
            else:
                inactive += 1
    return sorted(plugins, key=lambda p: (p["marketplace"], p["name"])), inactive


def contained(path: Path, roots: list[Path]) -> bool:
    resolved = path.resolve()
    return any(resolved.is_relative_to(root.resolve()) for root in roots)


def source_identity(path: Path, codex_home: Path, roots: list[Path], scope: str) -> tuple[str, str]:
    cache = codex_home / "plugins/cache"
    try:
        parts = path.absolute().relative_to(cache.absolute()).parts
        if len(parts) >= 4:
            return "plugin", f"{parts[0]} / {parts[1]} · {parts[2]}"
    except ValueError:
        pass
    if (codex_home / "skills/.system") in path.parents:
        return "system", "Codex 系统技能"
    if contained(path, roots):
        return ("project", "当前项目技能") if scope == "repo" else ("local", "本机技能")
    return "external", "声明根目录之外"


def reconcile(host: dict, plugins: dict, index: dict, roots: list[Path], codex_home: Path) -> dict:
    rows = host_rows(host)
    enabled_plugins, inactive_plugins = plugin_summary(plugins)
    plugin_versions = {(p['marketplace'], p['name'], p['version']) for p in enabled_plugins}
    indexed = index.get("skills")
    if not isinstance(indexed, list):
        raise ValueError("Vibe index must contain a skills array")
    candidates: dict[str, list[dict]] = {}
    for entry in indexed:
        if not isinstance(entry, dict):
            raise ValueError("Malformed Vibe index entry")
        source = entry.get("resolved_skill_file") or entry.get("skill_entrypoint")
        if isinstance(source, str):
            candidates.setdefault(str(Path(source).resolve()), []).append(entry)
    diagnostics = []
    invalid_paths: dict[str, list[str]] = {}
    raw_diagnostics = index.get("discovery_diagnostics", {})
    if not isinstance(raw_diagnostics, dict):
        raise ValueError("Malformed Vibe discovery diagnostics")
    for group, values in raw_diagnostics.items():
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            diag = {k: item[k] for k in ("skill_id", "reason", "path", "message") if k in item}
            diag["group"] = group
            diagnostics.append(diag)
            if isinstance(item.get("path"), str):
                invalid_paths.setdefault(str(Path(item["path"]).resolve()), []).append(item.get("reason", group))
    skills = []
    for row in rows:
        path = Path(row["path"])
        resolved = str(path.resolve())
        matches = candidates.get(resolved, [])
        active = [m for m in matches if m.get("active", True) is True and m.get("enabled", True) is True]
        reasons = invalid_paths.get(resolved, [])
        source_kind, source_label = source_identity(path, codex_home, roots, row.get("scope", ""))
        digest = None
        source_valid = contained(path, roots) and path.is_file()
        if source_kind == "plugin":
            parts = path.absolute().relative_to((codex_home/"plugins/cache").absolute()).parts
            # Bundled components are reported by skills/list, not plugin/installed.
            if parts[0] != "openai-bundled" and tuple(parts[:3]) not in plugin_versions:
                source_valid = False
                reasons = [*reasons, "plugin_not_exact_installed_enabled_version"]
        if source_valid:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if not row["enabled"]:
            binding = "disabled"
        elif not source_valid:
            binding = "invalid_source"
        elif any("ambiguous" in r for r in reasons) or len(active) > 1:
            binding = "ambiguous"
        elif len(active) == 1 and active[0].get("content_sha256") == digest:
            binding = "bindable"
        elif active:
            binding = "stale"
        else:
            binding = "not_indexed"
        explicit = active[0].get("explicit_only") if len(active) == 1 else None
        skills.append({
            "key": hashlib.sha256(row["path"].encode()).hexdigest()[:16],
            "id": path.parent.name, "name": row["name"],
            "description": str(row.get("description", "")),
            "source_kind": source_kind, "source_label": source_label,
            "host_scope": row.get("scope", "unknown"),
            "entrypoint": row["path"], "resolved_entrypoint": resolved,
            "host_enabled": row["enabled"], "binding_status": binding,
            "binding_reasons": reasons, "explicit_only": explicit,
            "dependency_status": "unknown", "content_sha256": digest,
        })
    statuses = Counter(s["binding_status"] for s in skills)
    return {
        "schema_version": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_origin": "live_codex_app_server",
        "source_methods": ["plugin/installed", "skills/list"],
        "vibe_index_generated_at": index.get("generated_at"),
        "summary": {
            "total": len(skills), "host_list_count": len(rows),
            "host_enabled": sum(s["host_enabled"] for s in skills),
            "vibe_bindable": statuses["bindable"], "disabled": statuses["disabled"],
            "dependency_unknown": len(skills),
            "index_active_count": sum(e.get("active", True) is True and e.get("enabled", True) is True for e in indexed),
            "enabled_plugins_count": len(enabled_plugins), "inactive_plugins_excluded": inactive_plugins,
            "binding_counts": dict(sorted(statuses.items())),
            "source_counts": dict(sorted(Counter(s["source_kind"] for s in skills).items())),
        },
        "enabled_plugins": enabled_plugins,
        "skills": skills, "diagnostics": diagnostics,
        "limits": [
            "Host enabled does not prove external tools, accounts or dependencies are usable.",
            "Bindable means current host enabled plus one matching active Vibe path and source hash.",
            "Dependency state is unknown until a task-specific invocation is actually verified.",
            "Vibe index is a supplied snapshot; stale source hashes fail closed.",
            "Real local inventory and paths are private outputs; do not commit them publicly.",
        ],
    }


def render_guide(data: dict) -> str:
    summary = data["summary"]
    lines = ["# 本机真实技能使用指南", "", "此文件由当前 Codex 原生注册表导出，不以缓存目录推断启用。", "",
             f"- 原生 Skill 数：{summary['host_list_count']}；启用：{summary['host_enabled']}。",
             f"- 当前 Vibe 可绑定：{summary['vibe_bindable']}；依赖未知：{summary['dependency_unknown']}。", "",
             "## 状态含义", "", "`host_enabled` 是 skills/list 的布尔状态；plugin/installed 提供确切已装启用版本。",
             "`bindable` 要求当前路径与活跃 Vibe 索引唯一匹配，且 SKILL.md 原始字节哈希一致。",
             "`not_indexed`、`ambiguous`、`stale`、`invalid_source` 和 `disabled` 均不能当作 Vibe 可绑定。",
             "系统/内置技能和嵌套技能可能已启用却未被 Vibe 索引；诊断会保留这个差异。",
             "所有 dependency_status 初始为 unknown；导出器不会登录账户、调用业务API或测试全部外部依赖。", "",
             "## 任务入口建议", "", "下表仅从本次实际元数据挑选入口；不是自动选定、调用或质量认证。", ""]
    purposes = {"cli-toolkit": "需要可复用导出器或命令行自动化时，先读该入口的 CLI 标准。",
                "minimalist-ui": "需要平面、简洁的可用界面时，核对该入口的视觉和交互约束。",
                "agent-browser": "需要真实网页操作或验收时，先运行其文档要求的 skills get core。"}
    for skill_id, purpose in purposes.items():
        for skill in data["skills"]:
            if skill["id"] == skill_id:
                lines.extend([f"### {skill['name']}", "", purpose, "",
                              f"- 当前绑定状态：`{skill['binding_status']}`；依赖：`{skill['dependency_status']}`。",
                              f"- 真实元数据：{skill['description']}", f"- 入口：`{skill['entrypoint']}`", ""])
    lines.extend(["## 使用与隐私", "", "1. 先按任务搜索和筛选，再阅读候选 SKILL.md 的适用条件和负边界。",
                  "2. 只有实际完成该技能负责的工作并通过对应检查后，才记为已经使用。",
                  "3. 不把未启用缓存或未知依赖标成可执行；更新 Vibe 索引后重新导出。",
                  "4. 本地 enabled-skills.json、指南和含个人路径的截图不得进入公开源码。", ""])
    return "\n".join(lines)


def write_if_changed(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == value:
        return
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vibe-index", type=Path, required=True, help="Current Vibe index JSON or index --json result")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Private local JSON output")
    parser.add_argument("--guide", type=Path, help="Optional local usage guide")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Host registry workspace context")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home()/".codex")))
    parser.add_argument("--codex-bin", help="Explicit Codex binary (default plugin app-server, then PATH)")
    parser.add_argument("--skill-root", action="append", type=Path, default=[], help="Additional permitted Skill source root")
    parser.add_argument("--timeout", type=float, default=30, help="Total registry timeout seconds (1..120)")
    parser.add_argument("--json", action="store_true", help="Print structured summary (dataset is always JSON)")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 120:
        parser.error("--timeout must be between 1 and 120 seconds")
    try:
        workspace, codex_home = args.workspace.expanduser().resolve(), args.codex_home.expanduser().resolve()
        if not workspace.is_dir():
            raise ValueError("Workspace does not exist")
        preferred = codex_home / "plugins/.plugin-appserver" / ("codex.exe" if os.name == "nt" else "codex")
        binary = args.codex_bin or (str(preferred) if preferred.is_file() else shutil.which("codex"))
        if not binary or Path(binary).suffix.casefold() in {".cmd", ".bat"}:
            raise ValueError("Codex app-server binary unavailable; supply --codex-bin")
        index = json.loads(args.vibe_index.read_text(encoding="utf-8-sig"))
        if not isinstance(index, dict):
            raise ValueError("Vibe index must be a JSON object")
        plugins, host = registry_snapshot(binary, codex_home, workspace, args.timeout)
        roots = [codex_home/"skills", codex_home/"plugins/cache", codex_home.parent/".agents/skills",
                 workspace/".agents/skills", workspace/".codex/skills", *args.skill_root]
        result = reconcile(host, plugins, index, roots, codex_home)
        write_if_changed(args.output, json.dumps(result, ensure_ascii=False, indent=2)+"\n")
        if args.guide:
            write_if_changed(args.guide, render_guide(result))
        print(json.dumps(result["summary"], ensure_ascii=False) if args.json else
              f"Exported {result['summary']['host_list_count']} host Skills; {result['summary']['vibe_bindable']} Vibe-bindable")
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc), "status": "export_refused"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
