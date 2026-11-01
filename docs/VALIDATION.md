# Validation scope

## Runtime derivative

The shipped runtime is byte-identical to the locally exercised 4.1.3-harness2.4 Skill. Earlier Harness² work used four candidate executions and a frozen independent validation to repair macOS installation and handoff behavior. Those approvals were synthetic fixtures; they did not establish real task delivery or a general model performance gain.

A later L-level task used real user requirement and plan approvals, actual current Codex host registry queries, selected local Skills, real CLI export and a working navigator. Three assigned Skills contributed actual module results. The public distribution omits the private inventory, source paths, runtime session IDs, continuation credentials, screenshots and raw logs.

One real host re-entry failed when the preferred plan approval omitted the frozen organization. Forwarding that exact organization, as the Skill contract requires, produced a real agent execution handoff. This failure was retained locally and is documented in the root usage instructions.

## Navigator

- Export: actual read-only host registry queries, a fresh Vibe index, two exports identical except generation time, and an independent path/enabled-state comparison.
- Boundary checks: 10 tests covering disabled entries, ambiguity, source hash drift, symlink escape, invalid host state, missing index entries and inactive cached files.
- Browser: agent-browser 0.27.0 controlled a real isolated Chrome instance against the local page; 31 interaction assertions passed against the actual exported metadata.
- Search, combined filters, reset, details, empty state, keyboard focus, and visible pagination from 24 to 48 records were exercised.
- Copying was verified by reading back the exact known entrypoint. The isolated headless browser required temporary clipboard test permissions on the loopback origin; permissions were revoked afterward. A success toast alone was not counted.
- Actual 1440px desktop and 390px mobile screenshots were inspected; the mobile document width did not exceed its viewport.
- An isolated server lacking the real data file returned HTTP 404. The page showed an explicit error, no results and unknown statistics; retry preserved the error. The actual source dataset was not modified.
- Normal-page browser console and uncaught-error checks were empty after repair.

The first browser visit uncovered a genuine render failure: a form control with id `reset` shadowed the native form method. Renaming it to `reset-filters` repaired the page; the affected chain and full browser matrix were rerun. Original failure evidence remains in the private local dossier.

A conditional browser-tool wait timed out after an offscreen action. It was not classified as a product failure. The final visible-button test verified both the rendered row count and user-visible pagination text. No unrelated browser processes were terminated.

This is one real local task, not a benchmark or proof that every installed Skill's external dependencies work. Other operating systems, physical phones and external account workflows were not exercised. Public-source checks are documented in the repository's initial publication commit and local closeout; local process receipts are not included in the public source tree.

## Interpreter environment boundary

The real run also exposed host interpreter drift: an absolute outer Python invocation and a different first Python on PATH produced cross-tag bytecode caches in one managed directory. Bootstrap rejected these files rather than ignoring them. Each foreign cache was independently verified with its matching interpreter against receipt-owned source and preserved in a private quarantine before removal from that directory. No runtime source, receipt, or validation rule was changed. The public bootstrap pins the selected interpreter directory on PATH so nested Python calls use the same version.

## Source package checks before publication

The public README bootstrap and actual host index/export commands were run successfully from this source checkout. A separate clean managed directory was installed through the packaged installer, its receipt self-check passed, and normal CLI use followed by resolver reuse passed. The navigator and exporter sources matched the browser-accepted local files byte for byte. All packaged Python files parsed, the JavaScript syntax check passed, the ten export boundary tests passed again, and the source allowlist contained no detected credentials or operator-specific paths. The current third-party disclosure covers all 32 required registry entries. Generated personal exports remain ignored and untracked.
