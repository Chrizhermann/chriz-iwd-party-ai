# chriz-iwd-party-ai

Standalone WeiDU mod ("Chriz Icewind Dale Party AI") for Icewind Dale: Enhanced Edition (2.7.3.0):
unlocks BG1/2:EE-style Advanced AI (`BDDEFAI.BCS` + `CHARACTER_SCRIPT` UI options) and repairs
broken built-in `.BS` player AI scripts (`aGen.BS` "Standard Attack", `bard0.BS`, `thief0.BS`,
`cleric0.BS`, `iwdpgen.BS`, `apass.BS`, `cleric3.BS`, `cleric4.BS`, `fighter4.BS`, etc.).

- Target: IWD:EE 2.7.3.0. Follow the mandatory "We Overwrite" compatibility policy in the
  `bg-modding` skill (`compatibility-policy.md`): never skip, abort, or warn on unexpected game
  data; write the decided result cleanly.
- Never copy or commit upstream installed-game files (`UI.MENU`, `.BS`, `.BCS`, `.IDS`,
  `dialog.tlk`) or SCS files.
- Never modify Christopher's live game installs or saves, and never launch a game while he is
  working or streaming.
- Describe component behaviour in `docs/components.md` in engine-neutral terms.
- Offline test suite: `pytest` (requires `weidu.exe` via `WEIDU_EXE` env var or sibling
  `chriz-bg-rebalance/weidu.exe`, plus `lupa` for real Lua 5.2 execution checks).
- Public release, tags, and GitHub push only with Christopher's explicit OK.
