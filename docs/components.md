# Components

Behaviour is described in engine-neutral terms (IDS symbol names) rather than WeiDU mechanics.

## 0: BG-style Advanced AI and repaired player scripts for IWD:EE

### Target and compatibility policy

Targets IWD:EE 2.7.3.0. Always overwrites `PARTYAI.2DA`, `BDDEFAI.BCS`, `IWDPGEN.BCS`,
`aGen.BS`, `apass.BS`, and `iwdpgen.BS`, and repairs `CHARACTER_SCRIPT` in `UI.MENU` plus
the remaining `scripts/*.BS` player scripts regardless of prior file state.

### 1. Native Advanced AI panel (`UI.MENU`)

- Unlocks `CHARACTER_SCRIPT` Smart Script options whenever row 2 (`ADVANCED AI`) is selected
  (`showingSmartOptions = (scriptList_idx == 2)`), both on menu open and on list click.
- On menu open with `ADVANCED AI` selected, sets the description text to
  `CHARACTER_SCRIPT_SMART_SCRIPT_DESCRIPTION` instead of indexing `scriptOptions` by
  `scriptList_idx` (preventing a nil-index error when scrolling/selecting scripts beyond row 7).
- Exposes only the 7 implemented Smart Script options in `scriptOptions`, addressed by their
  engine option ID (`entry[3]`):
  - `1` (`BDAI_DISABLE_ATTACK`): **Attack Enemies** (`0` = enabled, `1` = disabled)
  - `2` (`BDAI_ATTACK_MODE = 1`): **Prefer Melee Weapons** (mutually exclusive with `3`)
  - `3` (`BDAI_ATTACK_MODE = 2`): **Prefer Ranged Weapons** (mutually exclusive with `2`; neither checked = `0`, keep equipped weapon)
  - `8` (`BDAI_SKILL_MODE = 1`): **Find Traps** (mutually exclusive with `9`, `10`, `11`)
  - `9` (`BDAI_SKILL_MODE = 2`): **Hide in Shadows** (mutually exclusive with `8`, `10`, `11`)
  - `10` (`BDAI_SKILL_MODE = 3`): **Sing Battlesong** (mutually exclusive with `8`, `9`, `11`)
  - `11` (`BDAI_SKILL_MODE = 4`): **Turn Undead** (mutually exclusive with `8`, `9`, `10`; none checked = `0`)
- Automatic items/potions (`4`), special abilities (`5`), offensive spells (`6`), and
  defensive spells (`7`) are intentionally omitted in v0.1.0 and hidden from the UI.
- When `CHARACTER_SCRIPT` uses the default light parchment background (`GUICHISD`) without
  explicit label colors, adds dark ink text color (`D`) to the checkbox labels for readability.

### 2. Advanced AI script (`PARTYAI.2DA` -> `BDDEFAI.BCS`)

Runs only while `InParty(Myself)` and every non-init action requires `ActionListEmpty()` so
manual player commands and manual focus-fire are never interrupted.

1. **First-time initialization:**
   - Resets `BDAI_INIT_SKILL` / `BDAI_INIT_ATTACK` when `GLOBAL` `BDAI_RESET_TIMERS` is `1`.
   - Sets default `BDAI_SKILL_MODE = 1` (Find Traps) once for `THIEF_ALL`, `MONK`, or `SHAMAN`
     when no skill mode is already selected.
   - Sets default `BDAI_ATTACK_MODE = 2` (Prefer Ranged) once when a ranged weapon is equipped.
2. **Modal protection & cleanup:**
   - Keeps `ModalState(SHAMANDANCE)` active without interrupting it (`NoAction()`).
   - Clears internal `CIPA_AUTO_SONG` / `CIPA_AUTO_TURN` markers when the corresponding modal
     state ends externally, so manually toggled modes (such as out-of-combat *War Chant of Sith*)
     are never cancelled.
3. **Weapon switching (`BDAI_ATTACK_MODE`):**
   - `1` (Prefer Melee): switches from a ranged weapon via `EquipMostDamagingMelee()`.
   - `2` (Prefer Ranged): switches to melee if `NearestEnemyOf(Myself)` is visible within range 4,
     and switches back via `EquipRanged()` when no enemy is within range 4 and `CanEquipRanged()` holds.
   - `0` (Default): leaves equipped weapons unchanged.
4. **Modal skill automation (`BDAI_SKILL_MODE`):**
   - `1` (Find Traps): enables `FindTraps()` out of combat when no enemy is seen for `THIEF_ALL`,
     `MONK`, or `SHAMAN` unless stealth, turn undead, or thieving button is active/disabled.
   - `2` (Hide in Shadows): activates `Hide()` on a 6-tick (`CIPA_HIDE_TMR`) cooldown out of sight
     of enemies while visible for `THIEF_ALL`, `RANGER_ALL`, or `MONK`.
   - `3` (Sing Battlesong): starts `BattleSong()` and sets `CIPA_AUTO_SONG = 1` for `BARD_ALL`
     when an enemy is seen or `ActuallyInCombat()` is true; clears the song only if
     `CIPA_AUTO_SONG == 1` after combat ends and `Delay(6)` passes.
   - `4` (Turn Undead): starts `Turn()` and sets `CIPA_AUTO_TURN = 1` for `CLERIC_ALL` or
     `PALADIN_ALL` (without Sanctuary, non-invisible) when hostile undead are within range 15;
     clears Turn only if `CIPA_AUTO_TURN == 1` after no hostile undead remain in sight and `Delay(6)`.
5. **Weapon target selection (`BDAI_DISABLE_ATTACK == 0`):**
   - Guarded by `!StateCheck(Myself,STATE_INVISIBLE)`, `CheckStat(Myself,0,SANCTUARY)`,
     `!ModalState(STEALTH)`, `!ModalState(BATTLESONG)`, and `!ModalState(TURNUNDEAD)`.
   - Attacks by distance (`NearestEnemyOf`, `SecondNearestEnemyOf`, `ThirdNearestEnemyOf`)
     checking `See`, `!StateCheck(...,STATE_REALLY_DEAD)`, `!Allegiance(...,GOODCUTOFF)`,
     `!InParty`, `WeaponEffectiveVs(...,MAINHAND)`, and `WeaponCanDamage(...,MAINHAND)` using
     `AttackOneRound` — allowing fire/acid weapons to finish downed trolls while mundane weapons
     advance to the next valid target.
   - Falls back to `NearestEnemyOf(Myself)` if all three fail weapon-damage checks (excluding
     downed trolls with `TROLLIMM` or `STATE_SLEEPING`), and finally retaliates against a visible
     `LastAttackerOf(Myself)` (`AttackedBy([EVILCUTOFF],DEFAULT)`).

### 3. Repaired built-in `.BS` scripts and `IWDPGEN.BCS`

- **Overwritten:**
  - `scripts/aGen.BS` ("Standard Attack"): adds `ActionListEmpty()`, invisibility/Sanctuary/modal
    guards, and the same distance-first `AttackReevaluate(...,30)` priority chain as `BDDEFAI.BCS`
    before `AttackedBy` retaliation (stopping random ranged ping-pong).
  - `scripts/apass.BS` ("Passive"): retaliates only when `ActionListEmpty()` on
    `AttackedBy([EVILCUTOFF],DEFAULT)` with visible `LastAttackerOf(Myself)`, matching weapon
    range (`Range(...,4)` -> melee, otherwise ranged if `CanEquipRanged()`).
  - `scripts/iwdpgen.BS` & `override/IWDPGEN.BCS` ("Party Default"): guards `SHAMANDANCE`, runs
    out-of-combat `FindTraps()` for `THIEF_ALL`/`MONK`/`SHAMAN`, and uses distance-ordered
    `AttackReevaluate(...,30)` combat targeting with `ActionListEmpty()`.
- **Patched (`scripts/*.BS` except `agen`, `apass`, `iwdpgen`, `none`):**
  - Replaces bare `[EVILCUTOFF]` target specifiers in `See([EVILCUTOFF])`, `!InParty([EVILCUTOFF])`,
    `Range([EVILCUTOFF],N)`, `!Range([EVILCUTOFF],N)`, `AttackReevaluate([EVILCUTOFF],N)`,
    `AttackOneRound([EVILCUTOFF])`, and `Attack([EVILCUTOFF])` with `NearestEnemyOf(Myself)`
    (preserving `!See([EVILCUTOFF])` out-of-combat checks and `[EVILCUTOFF.UNDEAD]` undead checks).
  - Ensures every `IF ... END` block containing `Attack(`, `AttackOneRound(`, or
    `AttackReevaluate(` includes `ActionListEmpty()`.
