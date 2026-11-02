# pns_ai_mcp — AI Engine and MCP server for Odoo

> **PATANEGRA Soft** (https://patanegra.com). Part of **Patanegra Soft Suite**.
> Reference implementation of the **Patanegra Application Agent Protocol (PAAP)**.
> Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

AI engine for Odoo: providers, agents, contexts, skills, Safe Plan writes,
and an inbound **MCP** server (Anthropic spec). Chatboo is a separate module
(the conversation UI). This engine does not depend on Chatboo.

| Path | Contents |
| :--- | :--- |
| `stacks/owl1/pns_ai_mcp/` | Odoo 14 |
| `stacks/owl2/pns_ai_mcp/` | Odoo 15 and later |
| `common/` | Version-agnostic code, skills, contexts, data, Apps sheet |

### `common/`

What is identical on every Odoo major lives once here. The installer overlays
`common/` then the stack. Edit agnostic files only in `common/`. A stack file
with the same path wins. Running a stack without the overlay will miss
`common/`.

Domain UI helpers: `utils/mcp_ui.py`.

## Python extras (not shipped by stock Odoo)

Install these in the Odoo Python (venv or container) **before** Apps. If they
are missing, Odoo refuses the module (`external_dependencies`).

Odoo 14 (`owl1`):

```text
openpyxl>=3.1.2
```

Odoo 19 (`owl2`): nothing extra.

Do not add `requests` or `reportlab` (Odoo already ships them). `pns_base`
needs no extra pip. On 14, use a current `openpyxl` (old wheels break with
recent NumPy).

## Install

A published clone (`14.0` or `19.0`) is a flat Odoo addon. Install the
Python extras, put this folder on `addons_path`, then Apps: `pns_base`
first, then this module.

Or, from the multi-version tree: `./install_flat.sh 19.0 /path/to/addons`.

## Odoo versions

| Series | Status |
| :--- | :--- |
| 14.0, 19.0 | Tested. Flat branch published. |
| 15.0 – 18.0 | Coming soon. `install_flat.sh` builds them and warns that they are not tested yet. |
| 13.0 and older | Not supported. |

Patanegra Soft Suite starts where its AI can run. Odoo 13 has no OWL, which the AI chat is built on. Odoo 8 to 10 run on Python 2, and Odoo 11 and 12 on Python 3.5; the AI engine needs Python 3.7. The suite keeps two stacks (`owl1` for 14.0, `owl2` for 15.0 and later) and no third one for older series.

## Tests

| Where you are | What runs |
| :--- | :--- |
| `main` (multi-version tree) | `python -m pytest unit_tests`, with no Odoo. Then the Odoo tests, after `./install_flat.sh 19.0 <dir>`. |
| A flat branch (`14.0`, `19.0`) | The Odoo tests in `tests/`. The unit tests live on `main`. |

Odoo tests, in an Odoo of a tested series with the module in `addons_path`:

```bash
odoo-bin -d <db> -i pns_ai_mcp --test-enable --stop-after-init --test-tags /pns_ai_mcp
```

## License, marks, training

Apache-2.0. PATANEGRA Soft™, PATANEGRA Soft Suite™, Chatboo™ and PAAP™ are
trademarks of PATANEGRA Soft SL; this license does not grant them.

TDM / AI training is allowed (TDMRep `tdm-reservation = 0`). See NOTICE.

Security: [SECURITY.md](SECURITY.md). Bugs, ideas and questions: [CONTRIBUTING.md](CONTRIBUTING.md).
