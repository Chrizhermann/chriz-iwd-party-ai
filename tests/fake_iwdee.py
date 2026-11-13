"""Self-contained synthetic IWD:EE 2.7.3.0 game builder and UI/script fixtures for offline tests."""
from __future__ import annotations

import shutil
import struct
import subprocess
from pathlib import Path

from conftest import IWD_CLEAN_DIR, MOD_DIR, MOD_FOLDER_NAME

RTYPE_2DA = 0x3F4  # 1012
RTYPE_IDS = 0x3F0  # 1008
RTYPE_MENU = 0x408  # 1032

FALLBACK_IDS: dict[str, str] = {
    "ACTION": """IDS V1.0
0 NoAction()
3 Attack(O:Target*)
13 Hide()
18 FindTraps()
30 SetGlobal(S:Name*,S:Area*,I:Value*)
33 Turn()
36 Continue()
105 AttackOneRound(O:Target*)
115 SetGlobalTimer(S:Name*,S:Area*,I:Time*GTimes)
133 ClearActions(O:Object*)
134 AttackReevaluate(O:Target*,I:ReevaluationPeriod*)
149 EquipMostDamagingMelee()
174 EquipRanged()
269 DisplayStringHead(O:Object*,I:StrRef*)
296 BattleSong()
""",
    "TRIGGER": """IDS V1.0
0x0002 AttackedBy(O:Object*,I:Style*ATTSTYLE)
0x400F Global(S:Name*,S:Area*,I:Value*)
0x401C See(O:Object*)
0x4018 Range(O:Object*,I:Range*)
0x4027 Delay(I:Delay*)
0x402B ActionListEmpty()
0x4033 InParty(O:Object*)
0x4037 StateCheck(O:Object*,I:State*State)
0x4044 CheckStat(O:Object*,I:Value*,I:StatNum*Stats)
0x4045 CheckStatGT(O:Object*,I:Value*,I:StatNum*Stats)
0x4046 CheckStatLT(O:Object*,I:Value*,I:StatNum*Stats)
0x404B CombatCounter(I:Number*)
0x404C CombatCounterGT(I:Number*)
0x4051 HotKey(I:Key*HotKey)
0x405C Alignment(O:Object*,I:Alignment*Align)
0x4075 HasItem(S:ResRef*,O:Object*)
0x4089 OR(I:OrCount*)
0x4097 GlobalTimerNotExpired(S:Name*,S:Area*)
0x400A Class(O:Object*,I:Class*Class)
0x400B Kit(O:Object*,I:Kit*Kit)
0x40C9 ModalState(I:State*MODAL)
0x40D5 ActuallyInCombat()
0x40E6 IsWeaponRanged(O:Object*)
0x40E7 ButtonDisabled(I:Button*BUTTON)
0x40EC WeaponEffectiveVs(O:Object*,I:Hand*HAND)
0x40F2 WeaponCanDamage(O:Object*,I:Hand*HAND)
0x40F8 CanEquipRanged()
""",
    "OBJECT": """IDS V1.0
0 Nothing
1 Myself
2 LeaderOf
10 LastAttackerOf
12 NearestEnemyOf
13 SecondNearestEnemyOf
14 ThirdNearestEnemyOf
""",
    "MODAL": "IDS\n0 NONE\n1 BATTLESONG\n2 DETECTTRAPS\n3 STEALTH\n4 TURNUNDEAD\n5 SHAMANDANCE\n",
    "HAND": "IDS\n1 MAINHAND\n2 OFFHAND\n3 BOTH\n",
    "BUTTON": "IDS\n0 BUTTON_STEALTH\n1 BUTTON_THIEVING\n6 BUTTON_TURNUNDEAD\n",
    "STATE": "IDS\n0x00000001 STATE_SLEEPING\n0x00000010 STATE_INVISIBLE\n0x00000FC0 STATE_REALLY_DEAD\n",
    "STATS": "IDS\n56 LEVEL\n63 SANCTUARY\n",
    "CLASS": "IDS\n20 MONK\n21 SHAMAN\n204 CLERIC_ALL\n205 THIEF_ALL\n206 BARD_ALL\n207 PALADIN_ALL\n209 RANGER_ALL\n",
    "EA": "IDS\n0 ANYONE\n30 GOODCUTOFF\n200 EVILCUTOFF\n",
    "GENERAL": "IDS\n4 UNDEAD\n",
    "ATTSTYLE": "IDS\n0 DEFAULT\n",
    "GTIMES": "IDS\n7200 ONE_DAY\n",
    "KIT": "IDS\n0x4005 CAVALIER\n",
    "ALIGN": "IDS\n0x03 MASK_EVIL\n",
    "HOTKEY": "IDS\n68 D\n86 V\n",
}


def _extract_key_ids(game_root: Path) -> dict[str, bytes] | None:
    key_path = game_root / "chitin.key"
    if not key_path.is_file():
        return None
    kd = key_path.read_bytes()
    if kd[:8] != b"KEY V1  ":
        return None
    num_bif, num_res, bif_off, res_off = struct.unpack_from("<IIII", kd, 8)
    bifs: list[tuple[int, str]] = []
    for i in range(num_bif):
        flen, noff, nlen, loc = struct.unpack_from("<IIHH", kd, bif_off + i * 12)
        bname = kd[noff : noff + nlen].split(b"\0", 1)[0].decode("ascii", "replace")
        bifs.append((loc, bname))

    out: dict[str, bytes] = {}
    bif_cache: dict[int, bytes] = {}
    for i in range(num_res):
        rname, rtype, rloc = struct.unpack_from("<8sHI", kd, res_off + i * 14)
        if rtype != RTYPE_IDS:
            continue
        name = rname.split(b"\0", 1)[0].decode("ascii", "replace").upper()
        bidx = rloc >> 20
        ridx = rloc & 0xFFFFF
        if bidx not in bif_cache:
            rel = bifs[bidx][1].replace("\\", "/")
            bp = game_root / rel
            if not bp.is_file():
                bp = game_root / "data" / Path(rel).name
            bif_cache[bidx] = bp.read_bytes()
        bdata = bif_cache[bidx]
        if bdata[:8] != b"BIFFV1  ":
            continue
        _, _, tbl_off = struct.unpack_from("<III", bdata, 8)
        _, roff, rsz, _, _ = struct.unpack_from("<IIIHH", bdata, tbl_off + ridx * 16)
        out[name] = bdata[roff : roff + rsz]
    return out


def build_minimal_tlk() -> bytes:
    header = struct.pack("<4s4sHII", b"TLK ", b"V1  ", 0, 1, 0x12 + 26)
    entry = struct.pack("<H8sIIIIII", 0, b"", 0, 0, 0, 0, 0, 0)
    return header + entry


def write_biff_and_key(game_root: Path, resources: list[tuple[str, int, bytes]]) -> None:
    bif_rel = "data/test.bif"
    bif_path = game_root / "data" / "test.bif"
    bif_path.parent.mkdir(parents=True, exist_ok=True)

    # BIFF V1
    var_cnt = len(resources)
    tbl_off = 0x14
    payload_start = tbl_off + var_cnt * 16
    var_entries = bytearray()
    payload = bytearray()
    cur_off = payload_start
    for idx, (_name, rtype, data) in enumerate(resources):
        var_entries += struct.pack("<IIIHH", idx, cur_off, len(data), rtype, 0)
        payload += data
        cur_off += len(data)
    bif_hdr = struct.pack("<4s4sIII", b"BIFF", b"V1  ", var_cnt, 0, tbl_off)
    bif_bytes = bytes(bif_hdr + var_entries + payload)
    bif_path.write_bytes(bif_bytes)

    # KEY V1
    bif_name_bytes = bif_rel.encode("ascii") + b"\0"
    bif_off = 0x18
    res_off = bif_off + 12 + len(bif_name_bytes)
    key_hdr = struct.pack("<4s4sIIII", b"KEY ", b"V1  ", 1, var_cnt, bif_off, res_off)
    bif_entry = struct.pack("<IIHH", len(bif_bytes), bif_off + 12, len(bif_name_bytes), 1)
    res_entries = bytearray()
    for idx, (name, rtype, _data) in enumerate(resources):
        res8 = name.upper().encode("ascii")[:8].ljust(8, b"\0")
        res_entries += struct.pack("<8sHI", res8, rtype, idx)
    (game_root / "chitin.key").write_bytes(bytes(key_hdr + bif_entry + bif_name_bytes + res_entries))


def make_ui_menu_vanilla() -> str:
    return """`
scriptOptions =
{
	{'SCRIPT_ATTACK_ENEMIES_LABEL',			'SCRIPT_ATTACK_ENEMIES_DESCRIPTION',		 1, 0, 0},
	{'SCRIPT_USE_MELEE_WEAPONS_LABEL',		'SCRIPT_USE_MELEE_WEAPONS_DESCRIPTION',		 2, 0, 0},
	{'SCRIPT_USE_RANGED_WEAPONS_LABEL',		'SCRIPT_USE_RANGED_WEAPONS_DESCRIPTION',	 3, 0, 0},
	{'SCRIPT_USE_ITEMS_LABEL',				'SCRIPT_USE_ITEMS_DESCRIPTION',				 4, 0, 0},
	{'SCRIPT_USE_SPECIAL_ABILITIES_LABEL',	'SCRIPT_USE_SPECIAL_ABILITIES_DESCRIPTION',	 5, 0, 0},
	{'SCRIPT_USE_OFFENSIVE_SPELLS_LABEL',	'SCRIPT_USE_OFFENSIVE_SPELLS_DESCRIPTION',	 6, 0, 0},
	{'SCRIPT_USE_DEFENSIVE_SPELLS_LABEL',	'SCRIPT_USE_DEFENSIVE_SPELLS_DESCRIPTION',	 7, 0, 0},
	{'SCRIPT_FIND_TRAPS_LABEL',				'SCRIPT_FIND_TRAPS_DESCRIPTION',			 8, 0, 0},
	{'SCRIPT_HIDE_IN_SHADOWS_LABEL',		'SCRIPT_HIDE_IN_SHADOWS_DESCRIPTION',		 9, 0, 0},
	{'SCRIPT_SING_BATTLESONG_LABEL',		'SCRIPT_SING_BATTLESONG_DESCRIPTION',		10, 0, 0},
	{'SCRIPT_TURN_UNDEAD_LABEL',			'SCRIPT_TURN_UNDEAD_DESCRIPTION',			11, 0, 0}
}

function handleScriptOptionChange(option)
	local wasOn = scriptOptions[option][4] == 2
	if option == 2 then
		if wasOn == true then
			scriptOptions[option][4] = 0
			scriptOptions[option][5] = false
		else
			scriptOptions[option][4] = 2
			scriptOptions[option][5] = true
			scriptOptions[option+1][4] = 0
			scriptOptions[option+1][5] = false
		end
	else
		scriptOptions[option][4] = toggleFrame(scriptOptions[option][4])
		if scriptOptions[option][4] == 0 then
			scriptOptions[option][5] = false
		else
			scriptOptions[option][5] = true
		end
	end
end
`
menu
{
	name 'CHARACTER_SCRIPT'
	align center center
	ignoreesc
	onOpen
	"
		doneEnabled = characterScreen:IsDoneButtonClickable(currentID)
		currentPanelID = const.SCRIPT_ID

		showingSmartOptions = false

		for index, var in pairs(scriptOptions) do
			var[5] = characterScreen:GetTempSmartScriptLocal(var[3])
			if var[5] == false then
				var[4] = 0
			else
				var[4] = 2
			end
		end
	"
	label
	{
		area 0 0 864 710
		mosaic GUICHISD
	}
	list
	{
		column
		{
			width 100
			label
			{
				area 0 0 -1 -1
				text lua "formatScriptName(scriptList[rowNumber])"
				text style "normal"
				text color 'D'
			}
		}
		area 40 194 360 414
		table "scriptList"
		var "scriptList_idx"
		action
		"
			showingSmartOptions = false
			if scriptList[scriptList_idx] ~= '' then
				Infinity_OnScriptItemSelect(scriptList_idx - 1)
				doneEnabled = characterScreen:IsDoneButtonClickable(currentID)
			else
				scriptList_idx = 0
				scriptDescription = ''
				doneEnabled = false
			end
		"
	}
	list
	{
		column
		{
			width 80
			label
			{
				area 10 0 -1 -1
				text lua "getUiString( scriptOptions[rowNumber][1])"
				text style	"normal"
				text align right center
			}
		}
		column
		{
			width 20
			label
			{
				area 8 8 32 32
				bam ROUNDBUT
				frame lua "scriptOptions[rowNumber][4]"
			}
		}
		area 444 194 376 266
		table "scriptOptions"
		var selScriptOpt
		enabled "showingSmartOptions == true"
		action
		"
			scriptDescription = getUiString(scriptOptions[selScriptOpt][2])
			if(cellNumber == 2) then
				Infinity_PlaySound('GAM_09')
				handleScriptOptionChange(selScriptOpt)
			end
		"
	}
	button
	{
		area 464 653 236 44
		text "DONE_BUTTON"
		action
		"
			if showingSmartOptions == true then
				for index, var in pairs(scriptOptions) do
					characterScreen:SetTempSmartScriptLocal(var[3], var[5])
				end
			end
			characterScreen:OnDoneButtonClick()
			Infinity_PopMenu()
		"
	}
}
`
nextUiVar = 1
`
menu
{
	name 'OTHER_MENU'
	onOpen
	"
		showingSmartOptions = false
	"
}
"""


def make_ui_menu_leui() -> str:
    return """`
scriptOptions =
{
	{'SCRIPT_ATTACK_ENEMIES_LABEL', 'SCRIPT_ATTACK_ENEMIES_DESCRIPTION', 1, 0, 0},
	{'SCRIPT_USE_MELEE_WEAPONS_LABEL', 'SCRIPT_USE_MELEE_WEAPONS_DESCRIPTION', 2, 0, 0},
	{'SCRIPT_USE_RANGED_WEAPONS_LABEL', 'SCRIPT_USE_RANGED_WEAPONS_DESCRIPTION', 3, 0, 0},
	{'SCRIPT_USE_ITEMS_LABEL', 'SCRIPT_USE_ITEMS_DESCRIPTION', 4, 0, 0},
	{'SCRIPT_USE_SPECIAL_ABILITIES_LABEL', 'SCRIPT_USE_SPECIAL_ABILITIES_DESCRIPTION', 5, 0, 0},
	{'SCRIPT_USE_OFFENSIVE_SPELLS_LABEL', 'SCRIPT_USE_OFFENSIVE_SPELLS_DESCRIPTION', 6, 0, 0},
	{'SCRIPT_USE_DEFENSIVE_SPELLS_LABEL', 'SCRIPT_USE_DEFENSIVE_SPELLS_DESCRIPTION', 7, 0, 0},
	{'SCRIPT_FIND_TRAPS_LABEL', 'SCRIPT_FIND_TRAPS_DESCRIPTION', 8, 0, 0},
	{'SCRIPT_HIDE_IN_SHADOWS_LABEL', 'SCRIPT_HIDE_IN_SHADOWS_DESCRIPTION', 9, 0, 0},
	{'SCRIPT_SING_BATTLESONG_LABEL', 'SCRIPT_SING_BATTLESONG_DESCRIPTION', 10, 0, 0},
	{'SCRIPT_TURN_UNDEAD_LABEL', 'SCRIPT_TURN_UNDEAD_DESCRIPTION', 11, 0, 0}
}

function handleScriptOptionChange(option)
	scriptOptions[option][4] = toggleFrame(scriptOptions[option][4])
end
`
menu
{
	name 'CHARACTER_SCRIPT'
	align center center
	ignoreesc
	onOpen
	"
		currentPanelID = const.SCRIPT_ID
		Infinity_OnScriptItemSelect(scriptList_idx - 1)
		showingSmartOptions = (scriptList_idx == 2)
		scriptList_savedIdx = scriptList_idx

		for index, var in pairs(scriptOptions) do
			var[5] = characterScreen:GetTempSmartScriptLocal(var[3])
			if var[5] == false then
				var[4] = 0
			else
				var[4] = 2
			end
		end
	"
	label
	{
		area 0 0 864 710
		mosaic GUICHISD
	}
	list
	{
		column
		{
			width 100
			label
			{
				area 0 0 -1 -1
				text lua "formatScriptName(scriptList[rowNumber])"
				text style "normal"
				text color D
			}
		}
		area 46 198 354 410
		table "scriptList"
		var "scriptList_idx"
		action
		"
			Infinity_OnScriptItemSelect(scriptList_idx - 1)
			showingSmartOptions = (scriptList_idx == 2)
			scriptList_savedIdx = scriptList_idx
		"
	}
	list
	{
		column
		{
			width 80
			label
			{
				enabled "rowNumber ~= selScriptOpt"
				area 0 0 -1 -1
				text lua "t(scriptOptions[rowNumber][1])"
				text style "normal"
				text align right center
				text color D
			}
			label
			{
				enabled "rowNumber == selScriptOpt"
				area 0 0 -1 -1
				text lua "t(scriptOptions[rowNumber][1])"
				text style "normal"
				text align right center
				text color S
			}
		}
		column
		{
			width 20
			label
			{
				area 20 4 -1 -1
				bam ROUNDBUT
				frame lua "scriptOptions[rowNumber][4]"
			}
		}
		area 450 198 366 310
		table "scriptOptions"
		var selScriptOpt
		enabled "showingSmartOptions == true"
		action
		"
			scriptDescription = t(scriptOptions[selScriptOpt][2])
			if(cellNumber == 2) then
				handleScriptOptionChange(selScriptOpt)
			end
		"
	}
	button
	{
		area 464 653 236 44
		text "DONE_BUTTON"
		action
		"
			if showingSmartOptions == true then
				for index, var in pairs(scriptOptions) do
					characterScreen:SetTempSmartScriptLocal(var[3], var[5])
				end
			end
			characterScreen:OnDoneButtonClick()
			Infinity_PopMenu()
		"
	}
}
"""


def make_ui_menu_infinityui() -> str:
    return """`
scriptOptions =
{
	{'SCRIPT_ATTACK_ENEMIES_LABEL', 'SCRIPT_ATTACK_ENEMIES_DESCRIPTION', 1, 0, 0},
	{'SCRIPT_USE_MELEE_WEAPONS_LABEL', 'SCRIPT_USE_MELEE_WEAPONS_DESCRIPTION', 2, 0, 0},
	{'SCRIPT_USE_RANGED_WEAPONS_LABEL', 'SCRIPT_USE_RANGED_WEAPONS_DESCRIPTION', 3, 0, 0},
	{'SCRIPT_USE_ITEMS_LABEL', 'SCRIPT_USE_ITEMS_DESCRIPTION', 4, 0, 0},
	{'SCRIPT_USE_SPECIAL_ABILITIES_LABEL', 'SCRIPT_USE_SPECIAL_ABILITIES_DESCRIPTION', 5, 0, 0},
	{'SCRIPT_USE_OFFENSIVE_SPELLS_LABEL', 'SCRIPT_USE_OFFENSIVE_SPELLS_DESCRIPTION', 6, 0, 0},
	{'SCRIPT_USE_DEFENSIVE_SPELLS_LABEL', 'SCRIPT_USE_DEFENSIVE_SPELLS_DESCRIPTION', 7, 0, 0},
	{'SCRIPT_FIND_TRAPS_LABEL', 'SCRIPT_FIND_TRAPS_DESCRIPTION', 8, 0, 0},
	{'SCRIPT_HIDE_IN_SHADOWS_LABEL', 'SCRIPT_HIDE_IN_SHADOWS_DESCRIPTION', 9, 0, 0},
	{'SCRIPT_SING_BATTLESONG_LABEL', 'SCRIPT_SING_BATTLESONG_DESCRIPTION', 10, 0, 0},
	{'SCRIPT_TURN_UNDEAD_LABEL', 'SCRIPT_TURN_UNDEAD_DESCRIPTION', 11, 0, 0}
}

function handleScriptOptionChange(option)
	scriptOptions[option][4] = toggleFrame(scriptOptions[option][4])
end
`
menu
{
	name 'CHARACTER_SCRIPT'
	align center center
	ignoreesc
	onOpen
	"
		doneEnabled = characterScreen:IsDoneButtonClickable(currentID)
		currentPanelID = const.SCRIPT_ID

		showingSmartOptions = (scriptList_idx == 2)
		scriptDescription = t(scriptOptions[scriptList_idx][2])

		for index, var in pairs(scriptOptions) do
			var[5] = characterScreen:GetTempSmartScriptLocal(var[3])
			if var[5] == false then
				var[4] = 0
			else
				var[4] = 2
			end
		end
	"
	label
	{
		area 0 0 768 768
		bam 'rgdbcres'
	}
	list
	{
		column
		{
			width 80
			label
			{
				area 10 0 -1 -1
				text lua "t( scriptOptions[rowNumber][1])"
				text style "normal"
				text align right center
			}
		}
		area 780 102 318 552
		table "scriptOptions"
		var selScriptOpt
		enabled "showingSmartOptions == true"
		action
		"
			scriptDescription = t(scriptOptions[selScriptOpt][2])
			if(cellNumber == 2) then
				Infinity_PlaySound('GAM_09')
				handleScriptOptionChange(selScriptOpt)
			end
		"
	}
	button
	{
		area 464 653 236 44
		text "DONE_BUTTON"
		action
		"
			if showingSmartOptions == true then
				for index, var in pairs(scriptOptions) do
					characterScreen:SetTempSmartScriptLocal(var[3], var[5])
				end
			end
			characterScreen:OnDoneButtonClick()
			Infinity_PopMenu()
		"
	}
}
"""


SAMPLE_BS_BAFS: dict[str, str] = {
    "aGen": """IF
  AttackedBy([EVILCUTOFF],DEFAULT)
THEN
  RESPONSE #100
    AttackReevaluate(LastAttackerOf(Myself),30)
END

IF
  See(NearestEnemyOf(Myself))
THEN
  RESPONSE #100
    AttackReevaluate(NearestEnemyOf(Myself),30)
END
""",
    "bard0": """IF
  Global("OH_BRDA","LOCALS",0)
  ActionListEmpty()
  Class(Myself,BARD_ALL)
  !ModalState(BATTLESONG)
  OR(2)
    See([EVILCUTOFF])
    CombatCounterGT(0)
THEN
  RESPONSE #100
    BattleSong()
END

IF
  Global("OH_BRDA","LOCALS",0)
  ActionListEmpty()
  Class(Myself,BARD_ALL)
  ModalState(BATTLESONG)
  !See([EVILCUTOFF])
  CombatCounter(0)
  Delay(30)
THEN
  RESPONSE #100
    ClearActions(Myself)
END

IF
  Global("OH_BRDA","LOCALS",1)
  ActionListEmpty()
  !StateCheck(Myself,STATE_INVISIBLE)
  CheckStatLT(Myself,1,SANCTUARY)
  See([EVILCUTOFF])
  !InParty([EVILCUTOFF])
THEN
  RESPONSE #100
    AttackReevaluate([EVILCUTOFF],30)
END
""",
    "thief0": """IF
  Global("OH_THFS","LOCALS",0)
  ActionListEmpty()
  OR(2)
    !See([EVILCUTOFF])
    Global("OH_THFA","LOCALS",0)
  !ModalState(DETECTTRAPS)
THEN
  RESPONSE #100
    FindTraps()
END

IF
  Global("OH_THFA","LOCALS",1)
  ActionListEmpty()
  !StateCheck(Myself,STATE_INVISIBLE)
  CheckStatLT(Myself,1,SANCTUARY)
  See([EVILCUTOFF])
  !InParty([EVILCUTOFF])
THEN
  RESPONSE #100
    AttackReevaluate([EVILCUTOFF],30)
END
""",
    "cleric0": """IF
  ActionListEmpty()
  !StateCheck(Myself,STATE_INVISIBLE)
  CheckStatLT(Myself,1,SANCTUARY)
  !Range([EVILCUTOFF.UNDEAD],12)
  See([EVILCUTOFF])
  !InParty([EVILCUTOFF])
THEN
  RESPONSE #100
    AttackOneRound([EVILCUTOFF])
END
""",
    "cleric3": """IF
  See(NearestEnemyOf(Myself))
  Range(NearestEnemyOf(Myself),4)
THEN
  RESPONSE #100
    EquipMostDamagingMelee()
    AttackReevaluate(NearestEnemyOf(Myself),30)
END
""",
    "none": "",
}


def compile_baf_to_bytes(weidu_exe: Path, game_root: Path, baf_text: str, stem: str, ext: str) -> bytes:
    tmp_dir = game_root / ".bs_compile_tmp"
    tmp_dir.mkdir(exist_ok=True)
    baf_path = tmp_dir / f"{stem}.baf"
    baf_path.write_text(baf_text, encoding="utf-8")
    out_path = tmp_dir / f"{stem}.bcs"
    proc = subprocess.run(
        [str(weidu_exe), "--no-auto-tp2", "--use-lang", "en_us", "--game", str(game_root),
         "--no-exit-pause", str(baf_path), "--out", str(tmp_dir)],
        cwd=str(game_root),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "ERROR" not in proc.stdout and out_path.is_file(), (
        f"WeiDU BAF compile failed:\n{proc.stdout}\n{proc.stderr}"
    )
    data = out_path.read_bytes()
    shutil.rmtree(tmp_dir)
    return data


def create_fake_iwdee_game(
    game_root: Path,
    weidu_exe: Path,
    *,
    ui_menu_text: str | None = None,
    ui_in_override: bool = True,
    seed_scripts: bool = True,
    corrupt_bs: bool = False,
) -> None:
    game_root.mkdir(parents=True, exist_ok=True)
    (game_root / "override").mkdir(exist_ok=True)
    (game_root / "lang" / "en_us").mkdir(parents=True, exist_ok=True)

    tlk = build_minimal_tlk()
    (game_root / "lang" / "en_us" / "dialog.tlk").write_bytes(tlk)
    (game_root / "dialog.tlk").write_bytes(tlk)

    # Place mod folder junction/copy inside game_root for standard weidu invocation
    mod_dst = game_root / MOD_FOLDER_NAME
    if mod_dst.exists():
        shutil.rmtree(mod_dst)
    shutil.copytree(MOD_DIR, mod_dst)

    ids_map = _extract_key_ids(IWD_CLEAN_DIR)
    resources: list[tuple[str, int, bytes]] = [
        ("HOWPARTY", RTYPE_2DA, b"2DA V1.0\r\nDEFAULT\r\n"),
    ]
    if ids_map:
        for name, data in sorted(ids_map.items()):
            resources.append((name, RTYPE_IDS, data))
    else:
        for name, txt in sorted(FALLBACK_IDS.items()):
            resources.append((name, RTYPE_IDS, txt.encode("ascii")))

    if ui_menu_text is not None:
        if ui_in_override:
            (game_root / "override" / "UI.MENU").write_bytes(ui_menu_text.encode("utf-8"))
        else:
            resources.append(("UI", RTYPE_MENU, ui_menu_text.encode("utf-8")))

    write_biff_and_key(game_root, resources)

    if seed_scripts:
        sdir = game_root / "scripts"
        sdir.mkdir(exist_ok=True)
        for name, baf_txt in SAMPLE_BS_BAFS.items():
            bs_bytes = compile_baf_to_bytes(weidu_exe, game_root, baf_txt, name, "BS")
            (sdir / f"{name}.BS").write_bytes(bs_bytes)
        (sdir / "apass.BS").write_bytes(
            compile_baf_to_bytes(
                weidu_exe, game_root,
                "IF AttackedBy([EVILCUTOFF],DEFAULT) THEN RESPONSE #100 AttackReevaluate(LastAttackerOf(Myself),30) END\n",
                "apass", "BS",
            )
        )
        (sdir / "iwdpgen.BS").write_bytes(
            compile_baf_to_bytes(
                weidu_exe, game_root,
                "IF ActionListEmpty() See([EVILCUTOFF]) THEN RESPONSE #100 AttackReevaluate([EVILCUTOFF],30) END\n",
                "iwdpgen", "BS",
            )
        )
        if corrupt_bs:
            (sdir / "broken.BS").write_bytes(b"NOT_A_BCS_FILE")
