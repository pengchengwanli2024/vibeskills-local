# Third-party licenses and distribution boundaries

This derivative retains the original Apache-2.0 LICENSE and NOTICE. It does not relicense referenced code, datasets or services.

The canonical registry is [config/upstream-lock.json](config/upstream-lock.json), byte-identical to the packaged [Skill registry](skills/vibe/config/upstream-lock.json). The original disclosure is preserved in [docs/UPSTREAM-THIRD-PARTY-LICENSES.md](docs/UPSTREAM-THIRD-PARTY-LICENSES.md). Its historical matrix contains distribution tiers that differ from the current registry; the table below follows that registry.

Reference-only dependencies are not vendored. External-optional dependencies require separate installation and their own terms. No installed host Skills or plugin libraries are copied into this source release.

| Upstream | SPDX | Distribution tier | Shipped by default |
|---|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | `MIT` | `reference-only` | `false` |
| [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code) | `MIT` | `reference-only` | `false` |
| [f/prompts.chat](https://github.com/f/prompts.chat) | `CC0-1.0` | `external-optional` | `false` |
| [SuperClaude-Org/SuperClaude_Framework](https://github.com/SuperClaude-Org/SuperClaude_Framework) | `MIT` | `external-optional` | `false` |
| [feiskyer/claude-code-settings](https://github.com/feiskyer/claude-code-settings) | `MIT` | `reference-only` | `false` |
| [github/spec-kit](https://github.com/github/spec-kit) | `MIT` | `reference-only` | `false` |
| [medialab/xan](https://github.com/medialab/xan) | `Unlicense` | `external-optional` | `false` |
| [Done-0/fuck-u-code](https://github.com/Done-0/fuck-u-code) | `MIT` | `external-optional` | `false` |
| [ivy-llc/ivy](https://github.com/ivy-llc/ivy) | `NOASSERTION` | `external-optional` | `false` |
| [GokuMohandas/Made-With-ML](https://github.com/GokuMohandas/Made-With-ML) | `MIT` | `reference-only` | `false` |
| [zedr/clean-code-python](https://github.com/zedr/clean-code-python) | `MIT` | `reference-only` | `false` |
| [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | `NOASSERTION` | `reference-only` | `false` |
| [xlite-dev/LeetCUDA](https://github.com/xlite-dev/LeetCUDA) | `GPL-3.0` | `reference-only` | `false` |
| [RUC-NLPIR/FlashRAG](https://github.com/RUC-NLPIR/FlashRAG) | `MIT` | `external-optional` | `false` |
| [RUC-NLPIR/WebThinker](https://github.com/RUC-NLPIR/WebThinker) | `MIT` | `external-optional` | `false` |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | `Apache-2.0` | `external-optional` | `false` |
| [letta-ai/letta](https://github.com/letta-ai/letta) | `Apache-2.0` | `reference-only` | `false` |
| [dair-ai/Prompt-Engineering-Guide](https://github.com/dair-ai/Prompt-Engineering-Guide) | `MIT` | `reference-only` | `false` |
| [browser-use/browser-use](https://github.com/browser-use/browser-use) | `MIT` | `external-optional` | `false` |
| [simular-ai/Agent-S](https://github.com/simular-ai/Agent-S) | `Apache-2.0` | `reference-only` | `false` |
| [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) | `GPL-3.0` | `reference-only` | `false` |
| [muratcankoylan/Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) | `MIT` | `reference-only` | `false` |
| [awslabs/agent-squad](https://github.com/awslabs/agent-squad) | `Apache-2.0` | `reference-only` | `false` |
| [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | `MIT` | `reference-only` | `false` |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | `MIT` | `reference-only` | `false` |
| [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) | `MIT` | `reference-only` | `false` |
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | `NOASSERTION` | `reference-only` | `false` |
| [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) | `MIT` | `reference-only` | `false` |
| [e2b-dev/awesome-ai-agents](https://github.com/e2b-dev/awesome-ai-agents) | `NOASSERTION` | `reference-only` | `false` |
| [mahseema/awesome-ai-tools](https://github.com/mahseema/awesome-ai-tools) | `MIT` | `reference-only` | `false` |
| [filipecalegario/awesome-vibe-coding](https://github.com/filipecalegario/awesome-vibe-coding) | `CC0-1.0` | `reference-only` | `false` |
| [tukuaiai/vibe-coding-cn](https://github.com/tukuaiai/vibe-coding-cn) | `MIT` | `reference-only` | `false` |

`NOASSERTION` does not grant redistribution rights. Do not vendor referenced or optional sources without checking their licenses and preserving their notices. This repository retains upstream provenance; it does not certify external providers or imply their endorsement.
