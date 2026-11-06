# Changelog

What changes for people who use this module, one section per published version, newest first. The heading is the git tag.

## owl1-3.1.928_owl2-3.1.928 (2026-11-06)

- README: new "Agents, roles and chains" section (English and Spanish). It explains the two agent types, the agents the module ships, the seven provider roles and their fallback, and how the provider chain is ordered and failed over.

## owl1-3.1.927_owl2-3.1.927 (2026-11-06)

- The module's website link now points to the public product page instead of the local description page. The description is still shown inside Odoo.
- README: the language line also links to the product page.

## owl1-3.1.926_owl2-3.1.926 (2026-11-05)

- README: new "What it does not do" and "Questions" sections, in English and Spanish, covering supported protocols, the MCP routes and the three MCP tools.

## owl1-3.1.925_owl2-3.1.925 (2026-11-05)

- App store description: the EN tab is now shown as selected, so the language switch reads as a switch.

## owl1-3.1.924_owl2-3.1.924 (2026-11-05)

- Security: sandboxed code can no longer reach the database connection or cursor, whether through the environment, error objects, string formatting or pattern matching. Only a short list of environment attributes is available.
- Security: skill code now runs in the read-only box (its own read-only cursor, secret columns closed), not on the caller's cursor.
- Fixed: simple results such as the current user's name failed to display after the sandbox hardening; they display again.
- App store description: the ES tab now jumps to the Spanish text and the tab bar stays fixed at the top.

## owl1-3.1.919_owl2-3.1.919 (2026-11-04)

- Store category changed to "Extra Tools", so the module can be found when browsing categories.
- New store summary: "Native AI engine and MCP server for Odoo: open LLM providers, a read-only sandbox, human-approved writes and agents as Odoo modules."
- New store thumbnail that shows the whole banner instead of a cropped one.

## owl1-3.1.917_owl2-3.1.917 (2026-11-04)

- Configuration backups and partial bundles now say what they are (`what`) and no longer write a schema version. Older files that carry one still import.

## owl1-3.1.916_owl2-3.1.916 (2026-11-04)

- Added ready-made provider examples (OpenRouter, OVH, OpenAI, Anthropic, Lemonade), without keys. Load them with Settings → AI Engine → Import configuration.
- README setup: install Chatboo if you want the chat (it brings the engine), and how to load a provider example.

## owl1-3.1.915_owl2-3.1.915 (2026-11-03)

- The module is now called "PNS AI Engine" in Apps and in the store. The menu inside Odoo is still "AI Engine".
- Refreshed banners, description page and README titles.

## owl1-3.1.914_owl2-3.1.914 (2026-11-03)

- README: Spanish banner, and an example `mcp.json` for connecting Cursor or another MCP client.
- README and description: Odoo 15.0 to 18.0 have no branch and are not tested. They can be built from `main` and should be tried on a test database first.

## owl1-3.1.913_owl2-3.1.913 (2026-11-03)

- Fixed: when capturing a skill, the usage example written by the user is kept as long as the keys it names are still in the schema. Before, it was always replaced by a generated one.
- Tests no longer depend on demo data, do not call the network on Odoo 14, and no longer commit in a separate cursor while a test runs.

## owl1-3.1.912_owl2-3.1.912 (2026-11-02)

- Maintenance release; no change in behaviour.

## owl1-3.1.911_owl2-3.1.911 (2026-11-02)

- Maintenance release; no change in behaviour.

## owl1-3.1.910_owl2-3.1.910 (2026-11-02)

- Maintenance release; no change in behaviour.

## owl1-3.1.909_owl2-3.1.909 (2026-11-02)

- README: full English and full Spanish versions, with "English · Español" links at the top.

## owl1-3.1.908_owl2-3.1.908 (2026-11-02)

- README: the banner image no longer shows broken.
- Setup reduced to four steps: install, become AI administrator, get the API key, add a provider.

## owl1-3.1.906_owl2-3.1.906 (2026-11-02)

- README now opens with the same content as the description page: banner, features and setup.

## owl1-3.1.905_owl2-3.1.905 (2026-11-02)

- First public release.
- Security: system actions are no longer callable over RPC; supervised plans run as the user who asked; per-user records are private; external server secrets are visible only to the AI administrator and left out of exports.
- Security: URL fetches block internal networks even after DNS changes; the sandbox cannot send mail or run actions; `/mcp` gives no details to unauthenticated callers and rejects other users' sessions.
- Fixed: skills that require a group were not imported. Voice: the provider form warns when an audio role is handled as chat.
