# VibeSkills Local

A source release of the VibeSkills **4.1.3-harness2.4** derivative, based on [Vibe-Skills](https://github.com/foryourhealth111-pixel/Vibe-Skills) **4.1.1**, plus a reusable local Skill Navigator. This is an independent derivative, not an official upstream release.

Vibe freezes requirements and a module plan, binds selected Skills, returns execution to the agent, and accepts actual module results before cleanup. Discovery reads the Codex host registry for exact installed and enabled plugin versions. Cached versions are not activation evidence; ambiguous IDs and unavailable dependencies remain explicit.

## Use Vibe

Requirements: a local agent host, supported Python 3.10+, PowerShell `pwsh`, and filesystem access. Codex host discovery also requires its app-server executable. macOS ARM64 was exercised with Python 3.14 and PowerShell 7.6.9; Windows/Linux runtime acceptance is not claimed.

Install the repository as a local plugin using your host's plugin workflow, or follow [skills/vibe/SKILL.md](skills/vibe/SKILL.md) from the checked-out Skill directory. The source package is a runtime distribution, not the entire upstream development tree.

The managed-runtime resolver uses the included official installer outside discovered Skill roots. It checks owned source files, rejects drift and unexpected files, and isolates Python bytecode caches by interpreter tag. Run from the repository root in Bash-like hosts:

```sh
source skills/vibe/scripts/common/python_helpers.sh
PYTHON_BIN="$(pick_supported_python)"
export PATH="$(dirname "$PYTHON_BIN"):$PATH"
"$PYTHON_BIN" skills/vibe/scripts/runtime/resolve-managed-runtime.py --repo-root "$PWD/skills/vibe" > runtime.json
REPO_ROOT="$("$PYTHON_BIN" -c 'import json; print(json.load(open("runtime.json"))["runtime_root"])')"
PYTHONPATH="$REPO_ROOT/apps/vgo-cli/src" "$PYTHON_BIN" -m vgo_cli.main --help
```

Keep `REPO_ROOT`, the selected interpreter and the workspace fixed for bounded continuation. Prepending the selected interpreter directory keeps nested PowerShell Python calls consistent with the managed runtime cache tag. Obtain the actual result contract from the runtime. Requirement and plan approvals come from the user; the agent performs actual work rather than fabricating receipts. On plan approval, forward the previously frozen `agent_skill_organization` unchanged, including when the preferred approval payload contains a null organization. Selection or loading alone does not prove Skill use.

## Run the local Skill Navigator

The public tree contains reusable source only. Generate your own private inventory before opening the page. From the repository root, after the bootstrap above:

```sh
PYTHONPATH="$REPO_ROOT/apps/vgo-cli/src" "$PYTHON_BIN" -m vgo_cli.main index --repo-root "$REPO_ROOT" --host-id codex --agent-root "$HOME/.agents" --workspace-root "$PWD" --json > vibe-index.json
"$PYTHON_BIN" examples/skill-navigator/source-data/export_enabled_skills.py --vibe-index vibe-index.json --workspace "$PWD" --output examples/skill-navigator/source-data/enabled-skills.json --guide examples/skill-navigator/source-data/skills-guide.md --json
"$PYTHON_BIN" examples/skill-navigator/site/serve.py --port 8765
```

Open <http://127.0.0.1:8765/site/>. The server binds loopback only; stop it with Ctrl+C. Use another port if occupied. Do not open the HTML directly as `file://`.

Search names, IDs and descriptions; combine source and binding filters; inspect a Skill's actual metadata and copy its entrypoint. Keyboard controls include Tab, Enter, `/` for search and Esc for details. Desktop and mobile layouts are provided. Missing or invalid data produces an explicit error.

Host-enabled, Vibe-bindable and dependency-verified are separate states. The exporter defaults dependency status to unknown and does not test external accounts or all installed tools. The app does not execute Skills or alter host activation.

The exporter uses only Python's standard library and read-only `initialize`, `plugin/installed`, and `skills/list` app-server methods. It does not directly inspect account files or credentials; the host may still write normal operational logs. Its protocol sequence follows the included Apache-2.0 Vibe adapter.

## Validation

[Validation scope and observed fixes](docs/VALIDATION.md) separates the earlier bounded Harness² regression from the later real task. Run the reusable export boundary checks with:

```sh
"$PYTHON_BIN" -B -m unittest discover -s examples/skill-navigator/source-data -p 'test_*.py' -v
node --check examples/skill-navigator/site/app.js
```

Never commit your actual inventory, generated Vibe index, personal paths, private screenshots or raw account/session logs. Generated data is intentionally absent from this repository. Keep `runtime.json` and `vibe-index.json` local.

## License and provenance

Apache-2.0; preserve [LICENSE](LICENSE), [NOTICE](NOTICE), and [third-party disclosures](THIRD_PARTY_LICENSES.md). Upstream base commit: `5ce2258ecb57a9532257dcadaca571dc7fe54868`; original archive SHA-256: `746b5b44a9cc7852d33eadbbe9b9b950f83f104d0d33ea4cf33876b4bba9e3b8`.

The exact modified runtime-file hashes and previous bounded regression context are retained in [LOCAL-UPGRADE.json](skills/vibe/LOCAL-UPGRADE.json). Reusable navigator source and this release documentation were added for the real task. The original author and contributors remain credited; this source release does not publish anyone's installed Skill library.
