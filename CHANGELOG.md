# Changelog

## v0.1.0 (2026-11-14)

- Initial release of Chriz Icewind Dale Party AI (`chriz-iwd-party-ai`).
- Unlocked the native **Advanced AI** (`CHARACTER_SCRIPT` checkbox panel) in `UI.MENU` with the
  7 active combat/weapon/skill toggles (auto-items, auto-specials, and auto-spells omitted in v0.1.0).
- Added clean-room `BDDEFAI.BCS` and `PARTYAI.2DA` for IWD:EE 2.7.3.0 with `ActionListEmpty()`
  command protection, distance-ordered target selection, `Prefer Melee` / `Prefer Ranged` weapon
  switching, downed-troll handling, and class modal skills (`Find Traps`, `Hide in Shadows`,
  `Sing Battlesong`, `Turn Undead`).
- Overwrote `aGen.BS` ("Standard Attack"), `apass.BS` ("Passive"), and `iwdpgen.BS` / `IWDPGEN.BCS`
  ("Party Default"), and repaired remaining `scripts/*.BS` player scripts missing `ActionListEmpty()`
  or targeting bare `[EVILCUTOFF]`.
