#!/usr/bin/env python3
"""Resolve an immutable, receipt-verified runtime without changing the plugin copy."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import marshal
import os
from pathlib import Path
import re
import stat
import sys
import types

# Bootstrap imports must never write into a read-only plugin cache.
sys.dont_write_bytecode = True


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outside(home: Path, root: Path) -> None:
    if home == root or home.is_relative_to(root) or root.is_relative_to(home):
        raise RuntimeError(f"Managed home overlaps a source or discovered skill root: {root}")


def genuine_cache(path: Path, runtime: Path, owned: set[str]) -> bool:
    """Allow only CPython caches compiled from receipt-owned, verified source."""
    if path.parent.name != '__pycache__' or path.suffix != '.pyc':
        return False
    try:
        source = Path(importlib.util.source_from_cache(str(path)))
        if source.relative_to(runtime).as_posix() not in owned or source.suffix != '.py':
            return False
        match = re.fullmatch(r'.+\.' + re.escape(sys.implementation.cache_tag) + r'(?:\.opt-([12]))?\.pyc', path.name)
        if not match:
            return False
        optimization = int(match.group(1) or '0')
        expected = Path(importlib.util.cache_from_source(str(source), optimization='' if optimization == 0 else str(optimization)))
        if path != expected:
            return False
        payload = path.read_bytes()
        if len(payload) < 16 or payload[:4] != importlib.util.MAGIC_NUMBER:
            return False
        flags = int.from_bytes(payload[4:8], 'little')
        if flags not in (0, 1, 3):
            return False
        stream = io.BytesIO(payload[16:])
        code = marshal.load(stream)
        if stream.read(1) or not isinstance(code, types.CodeType):
            return False
        return code == compile(source.read_bytes(), str(source), 'exec', dont_inherit=True, optimize=optimization)
    except (OSError, ValueError, EOFError, TypeError, SyntaxError):
        return False


def verify(runtime: Path, files: list[dict[str, str]], package_digest: str, installer) -> None:
    for path in (runtime, *runtime.parents):
        if path.is_symlink():
            raise RuntimeError(f'Managed runtime has a symlink component: {path}')
    receipt_path = runtime / '.vibeskills/install-receipt.json'
    if runtime.is_symlink() or not receipt_path.is_file() or receipt_path.is_symlink():
        raise RuntimeError('Managed runtime is partial or has an invalid receipt; refusing replacement')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if (receipt.get('schema_version') != 1 or receipt.get('receipt_kind') != 'vibe-skill-install'
            or receipt.get('skill_id') != 'vibe' or receipt.get('install_root') != str(runtime)
            or receipt.get('skills_dir') != str(runtime.parent) or receipt.get('files') != files
            or receipt.get('package_digest_sha256') != package_digest):
        raise RuntimeError('Managed runtime receipt identity or source binding differs')
    result = installer.check_vibe_skill(skills_dir=runtime.parent)
    if not result.get('ok'):
        raise RuntimeError(f'Managed runtime owned-file integrity failed: {result}')
    owned = {entry['path'] for entry in files}
    allowed = owned | {'.vibeskills/install-receipt.json'}
    for path in runtime.rglob('*'):
        mode = path.lstat()
        if stat.S_ISLNK(mode.st_mode) or (stat.S_ISREG(mode.st_mode) and mode.st_nlink != 1):
            raise RuntimeError(f'Managed runtime contains a link: {path}')
        if stat.S_ISDIR(mode.st_mode):
            continue
        if not stat.S_ISREG(mode.st_mode):
            raise RuntimeError(f'Managed runtime contains an unexpected special file: {path}')
        relpath = path.relative_to(runtime).as_posix()
        if relpath not in allowed and not genuine_cache(path, runtime, owned):
            raise RuntimeError(f'Managed runtime contains an unexpected file: {relpath}')


def resolve(repo: Path, home: Path) -> Path:
    # Validate destination separation before any managed-home writes. These roots
    # include the host defaults and user-declared discovery roots, not just source.
    for relpath in ('packages/contracts/src', 'packages/installer-core/src', 'packages/runtime-core/src'):
        sys.path.insert(0, str(repo / relpath))
    from vgo_installer import simple_skill_installer as installer
    from vgo_runtime.kernel.host_skill_roots import resolve_host_skill_roots

    outside(home, repo)
    for host in ('codex', 'claude-code'):
        for root in resolve_host_skill_roots(repo_root=repo, host_id=host,
                                            agent_root=Path.home() / '.agents', workspace_root=None):
            outside(home, root.path)
    # Also reject cache/skills locations that may not exist yet.
    for relpath in ('.agents/skills', '.codex/skills', '.codex/plugins/cache', '.claude/skills'):
        outside(home, Path.home() / relpath)

    files = [{'path': relpath, 'sha256': digest(repo / relpath)}
             for relpath in installer.runtime_surface_relpaths(repo)]
    if not files:
        raise RuntimeError('Source selects no installable runtime files')
    package_digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode('utf-8')).hexdigest()
    # Supported Python versions have incompatible bytecode caches. Keep each
    # interpreter's normal CLI writes in its own content-addressed runtime.
    runtime = home / package_digest / sys.implementation.cache_tag / 'vibe'
    # Use the installer's OS-backed lock to serialize resolution and installation;
    # install_vibe_skill itself additionally locks the content-specific directory.
    with installer._cross_process_operation_lock(installer._operation_lock_path(home)):
        if runtime.parent.exists():
            verify(runtime, files, package_digest, installer)
        else:
            installer.install_vibe_skill(
                repo_root=repo, skills_dir=runtime.parent,
                installed_at_utc=datetime.now(timezone.utc).isoformat(),
                source_kind='developer_repo', source_git_commit='unknown', source_git_dirty=True)
            verify(runtime, files, package_digest, installer)
    return runtime


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', required=True)
    parser.add_argument('--runtime-home', default=str(Path.home() / '.local/share/vibeskills/runtimes'))
    args = parser.parse_args()
    try:
        repo = Path(args.repo_root).expanduser().resolve(strict=True)
        raw_home = Path(args.runtime_home).expanduser().absolute()
        # Preserve symlink evidence before resolve(), which would hide aliases.
        for path in (raw_home, *raw_home.parents):
            if path.is_symlink():
                raise RuntimeError(f'Managed home has a symlink component: {path}')
        runtime = resolve(repo, raw_home.resolve())
        print(json.dumps({'runtime_root': str(runtime)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'Unable to resolve managed Vibe runtime: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
