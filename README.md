# Chriz Icewind Dale Party AI

Brings BG1/2:EE-style **Advanced AI** toggles to **Icewind Dale: Enhanced Edition (2.7.3.0)**
and repairs IWD:EE's built-in player scripts so party members honor your move and attack orders
and target the nearest enemy.

Part of **[Chriz Easy IWD](https://bg.chrizfader.org/iwd)**

---

## Part 1: For Players

### What It Changes

- **Unlocks Advanced AI in Character Script Settings:** Exposes the hidden **Advanced AI**
  script option and 7 in-game toggles:

  | Toggle | Behavior |
  | --- | --- |
  | **Attack Enemies** | Automatically attacks visible foes when idle |
  | **Prefer Melee Weapons** | Switches to your strongest melee weapon |
  | **Prefer Ranged Weapons** | Uses ranged weapons until an enemy closes to melee range (`4`) |
  | **Find Traps** | Activates Find Traps out of combat (Thief, Monk, Shaman) |
  | **Hide in Shadows** | Activates Stealth out of sight of enemies (Thief, Ranger, Monk) |
  | **Sing Battlesong** | Starts Bard Song in combat without cancelling a manual song |
  | **Turn Undead** | Turns hostile undead in range without cancelling manual Turn Undead |

- **Honors your orders:** Party members no longer drop your move or focus-fire commands when an
  enemy attacks from afar, and downed trolls are only finished with weapons that can harm them.
- **Fixes built-in `.BS` scripts:** Rebuilds `Standard Attack` (`aGen.BS`), `Passive`
  (`apass.BS`), and `Party Default` (`iwdpgen.BS`), and repairs `bard0.BS`, `thief0.BS`,
  `cleric0.BS`, `cleric3.BS`, `cleric4.BS`, `fighter4.BS`, and remaining `scripts/*.BS` files.

### Requirements & Install Order

- **Icewind Dale: Enhanced Edition 2.7.3.0** (Windows x64)
- Install **near the end** of your IWD:EE load order — after UI mods (`LeUI-IWDEE`,
  `InfinityUI++`) and after `Stratagems`.

### Installation

1. Close Icewind Dale: Enhanced Edition completely.
2. Copy the `chriz-iwd-party-ai` folder into your IWD:EE game directory (next to `chitin.key`).
3. Copy 64-bit Windows `weidu.exe` into the game directory as `setup-chriz-iwd-party-ai.exe`.
4. Run `setup-chriz-iwd-party-ai.exe` and install component `0`.

---

## Part 2: Technical Details & License

### How It Works

- **`CHARACTER_SCRIPT` `UI.MENU` integration (`lib/cipa_ui.tpa`):** Unlocks
  `showingSmartOptions = (scriptList_idx == 2)` on menu open and click, sets the description
  to `CHARACTER_SCRIPT_SMART_SCRIPT_DESCRIPTION` (preventing nil-index crashes past row 7),
  keeps dark ink (`D`) readable on the parchment `GUICHISD` panel while preserving dark-skin
  text colors (`LeUI`, `InfinityUI++`), and hides unimplemented auto-potion/ability/spell
  toggles (`4`–`7`) in `v0.1.0`.
- **Clean-room `BDDEFAI.BCS` & `PARTYAI.2DA` (`lib/cipa_scripts.tpa`):** Maps Advanced AI to
  `BDDEFAI.BCS`, gates every combat and modal action with `ActionListEmpty()`, orders targeting
  (`NearestEnemyOf`, `SecondNearestEnemyOf`, `ThirdNearestEnemyOf`) with `WeaponEffectiveVs` /
  `WeaponCanDamage` checks, and tracks `CIPA_AUTO_SONG` / `CIPA_AUTO_TURN` / `SHAMANDANCE`.
- **Built-in `.BS` & `IWDPGEN.BCS` repairs:** Overwrites `aGen.BS`, `apass.BS`, and
  `iwdpgen.BS` / `IWDPGEN.BCS`, and patches remaining `scripts/*.BS` scripts to require
  `ActionListEmpty()` on attack blocks and replace bare `[EVILCUTOFF]` selectors with
  `NearestEnemyOf(Myself)` (keeping out-of-combat `!See([EVILCUTOFF])` and `[EVILCUTOFF.UNDEAD]`).

### Documentation & Tests

- Engine-neutral component specification: [docs/components.md](docs/components.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)
- Offline verification (`pytest`, requires `weidu.exe` and `lupa`): WeiDU parse checks plus
  synthetic vanilla, `LeUI`, and `InfinityUI++` install, idempotence, and byte-exact uninstall
  restoration tests.

## License

Licensed under the [MIT License](LICENSE).
