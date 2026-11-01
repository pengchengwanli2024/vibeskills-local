# VibeSkills (Local)

Private local build **4.1.3-harness2.4**, based on official VibeSkills **4.1.1**.
This is a derivative build, not an official upstream release.

Invoke `$vibe` in a local host with Python 3.10+ and filesystem access.
Codex plugin discovery queries read-only `plugin/installed` and `skills/list`
in a bounded app-server session. It admits exact installed and enabled versions
and manifest-declared Skill roots. It never chooses the greatest cached version
or recursively scans undeclared backup, vendor, staging or dependency trees. Host-disabled ordinary Skills
are excluded; genuine same-id collisions remain explicit. If host state cannot
be verified, plugin admission fails closed with diagnostics.

The native associated Codex app-server executable is preferred. The Windows
adapter does not run a `.cmd` or `.bat` wrapper as an executable. Ordinary explicit
non-host Skill roots remain usable without plugin inventory. Each scan refreshes
host state; it does not reuse a persisted activation snapshot.

Local integration tests use synthetic inputs and test-generated stage decisions,
real canonical CLI calls, a real module worker, an independent verifier, and both
success and failure cleanup gates. They do not establish live-model task quality.
Existing canonical requirement and plan approval contracts are preserved.

Earlier portability, optional Git and UTF-8 BOM fixes are retained. This package
does not change shared Codex settings, actual plugin enable states, or business data.
The separately managed local Skill has its own install receipt. Account publication
does not prove that the current client has reloaded the saved plugin release.

See `skills/vibe/LOCAL-UPGRADE.json` for base commit and modified-file hashes.
Original LICENSE, NOTICE, THIRD_PARTY_LICENSES.md and icon are retained.
VibeSkills is by foryourhealth111-pixel and contributors, Apache License 2.0.

macOS upgrade: official managed-runtime bootstrap outside discovered roots, complete installed self-check dependencies, literal host-shell handoff commands, verified generated-cache handling, and per-CPython-tag runtime isolation. Four local Harness2 candidate probes and an independent validation passed against the initial snapshot; the concurrent installed/enabled discovery changes are preserved and the combined package receives a separate post-merge workflow check. All stage approvals are synthetic tests, not real-user or production acceptance. No general benchmark gain is claimed.
