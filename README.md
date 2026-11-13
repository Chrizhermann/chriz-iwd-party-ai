# Chriz Icewind Dale Party AI

Unlocks BG1/2:EE-style **Advanced AI** in Icewind Dale: Enhanced Edition (2.7.3.0) and repairs
IWD:EE's broken built-in player scripts (`Standard Attack`, `Bard0`, `Thief0`, `Cleric0`,
`Party Default`, etc.).

## What It Fixes

1. **Unlocks Advanced AI (`ADVANCED AI` + Settings Checkboxes):**
   - Exposes the hidden **Advanced AI** checkbox panel in `CHARACTER_SCRIPT` (`UI.MENU`),
     displaying dark ink text on the default parchment panel while keeping dark skins (`LeUI`,
     `InfinityUI++`) readable.
   - Displays the 7 active toggles for **Attack Enemies**, **Prefer Melee Weapons**,
     **Prefer Ranged Weapons**, **Find Traps**, **Hide in Shadows**, **Sing Battlesong**, and
     **Turn Undead** (automatic potions, spells, and special abilities are intentionally omitted
     in v0.1.0).
   - Ships clean-room `BDDEFAI.BCS` and `PARTYAI.2DA`: preserves player focus-fire and movement
     via `ActionListEmpty()`, selects the closest attackable enemy by distance instead of spawn
     order, switches cleanly between melee/ranged when configured, finishes downed trolls only with
     weapons that can harm them, and automates class modal skills out of/into combat without
     cancelling a manual bard song or manual Turn Undead.
2. **Repairs Built-in `.BS` Player Scripts:**
   - Rebuilds `aGen.BS` ("Standard Attack"), `apass.BS` ("Passive"), and `iwdpgen.BS` /
     `IWDPGEN.BCS` ("Party Default") so player commands are never overridden by enemy ranged pings
     and targets are chosen by nearest distance.
   - Repairs remaining `scripts/*.BS` scripts (`bard0.BS`, `thief0.BS`, `cleric0.BS`,
     `cleric3.BS`, `cleric4.BS`, `fighter4.BS`, etc.) that lacked `ActionListEmpty()` on attack
     blocks or targeted bare `[EVILCUTOFF]` instead of `NearestEnemyOf(Myself)`.

## Installation & Load Order

Install at the end of an IWD:EE mod order (after UI mods such as `LeUI-IWDEE` or `InfinityUI++`,
and after `Stratagems`):

1. Copy the `chriz-iwd-party-ai` folder into the game directory.
2. Copy 64-bit Windows `weidu.exe` into the game directory as `setup-chriz-iwd-party-ai.exe` and
   run component `0`.

## Documentation

- [Component specification](docs/components.md)
- [Changelog](CHANGELOG.md)
- [MIT License](LICENSE)
