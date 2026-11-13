"""Real Lua 5.2 execution tests on WeiDU-patched CHARACTER_SCRIPT UI.MENU variants."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from lupa import lua52

from conftest import MOD_FOLDER_NAME
from fake_iwdee import (
    create_fake_iwdee_game,
    make_ui_menu_infinityui,
    make_ui_menu_leui,
    make_ui_menu_vanilla,
)


def _patch_ui_with_weidu(weidu_exe: Path, tmp_path: Path, name: str, ui_text: str) -> str:
    game = tmp_path / f"lua_{name}"
    create_fake_iwdee_game(game, weidu_exe, ui_menu_text=ui_text, ui_in_override=True, seed_scripts=False)
    res = subprocess.run(
        [
            str(weidu_exe),
            "--game", str(game),
            "--no-exit-pause", "--quick-log",
            "--force-install-list", "0",
            "--language", "0", "--use-lang", "en_us",
            f"{MOD_FOLDER_NAME}/setup-{MOD_FOLDER_NAME}.tp2",
        ],
        cwd=str(game),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "SUCCESSFULLY INSTALLED" in res.stdout
    return (game / "override" / "UI.MENU").read_text(encoding="utf-8")


def _extract_menu_scripts(ui_text: str, *, require_script_list: bool = True) -> tuple[str, str, str, str, str]:
    lua_blocks = re.findall(r"`\r?\n(.*?)\r?\n`", ui_text, re.S)
    assert lua_blocks, "No Lua chunk found"
    main_lua = lua_blocks[0]

    cs_match = re.search(r"name\s+['\"]CHARACTER_SCRIPT['\"].*?(?=\r?\n(?:`|menu\s*\{)|$)", ui_text, re.S)
    assert cs_match, "CHARACTER_SCRIPT menu not found"
    cs_text = cs_match.group(0)

    def _quote_body(pattern: str) -> str:
        m = re.search(pattern, cs_text, re.S)
        assert m, f"Pattern not found in CHARACTER_SCRIPT: {pattern}"
        return m.group(1)

    on_open = _quote_body(r"onOpen\s*\"(.*?)\"")
    script_list_action = (
        _quote_body(r"table\s+\"scriptList\".*?action\s*\"(.*?)\"")
        if require_script_list
        else ""
    )
    options_action = _quote_body(r"table\s+\"scriptOptions\".*?action\s*\"(.*?)\"")
    done_action = _quote_body(r"text\s+\"DONE_BUTTON\".*?action\s*\"(.*?)\"")
    return main_lua, on_open, script_list_action, options_action, done_action


def _new_lua_harness(main_lua: str, initial_locals: dict[int, bool], initial_idx: int):
    lua = lua52.LuaRuntime()
    locals_tbl = lua.table_from(initial_locals)
    saved_tbl = lua.table()

    lua.execute(
        """
        const = { SCRIPT_ID = 9 }
        currentID = 1
        scriptList = { "NONE", "ADVANCED AI", "", "aGen", "Bard0", [18] = "aGen" }
        scriptList_idx = ...
        scriptDescription = ""
        doneEnabled = true
        selScriptOpt = 1
        cellNumber = 2
        function getUiString(k) return "STR:" .. tostring(k) end
        t = getUiString
        function toggleFrame(f) return (f == 0) and 2 or 0 end
        function Infinity_PlaySound(s) end
        function Infinity_PopMenu() end
        function Infinity_OnScriptItemSelect(idx0)
            if idx0 == 1 then
                scriptDescription = getUiString("CHARACTER_SCRIPT_SMART_SCRIPT_DESCRIPTION")
            else
                scriptDescription = "OTHER:" .. tostring(idx0)
            end
        end
        """,
        initial_idx,
    )
    cs = lua.eval(
        """
        (function(loc, saved)
            return {
                IsDoneButtonClickable = function(self, id) return true end,
                GetTempSmartScriptLocal = function(self, optId)
                    local v = loc[optId]
                    if v == nil then return false end
                    return v
                end,
                SetTempSmartScriptLocal = function(self, optId, val)
                    saved[optId] = val
                end,
                OnDoneButtonClick = function(self) end,
            }
        end)
        """
    )(locals_tbl, saved_tbl)
    lua.globals().characterScreen = cs
    lua.execute(main_lua)
    return lua, saved_tbl


@pytest.mark.parametrize(
    ("name", "ui_builder", "has_script_list_click"),
    [
        ("vanilla", make_ui_menu_vanilla, True),
        ("leui", make_ui_menu_leui, True),
        ("infinityui", make_ui_menu_infinityui, False),
    ],
)
def test_character_script_lua_behavior(
    weidu_exe: Path, tmp_path: Path, name: str, ui_builder, has_script_list_click: bool
) -> None:
    patched_ui = _patch_ui_with_weidu(weidu_exe, tmp_path, name, ui_builder())
    assert "`" not in re.findall(r"`\r?\n(.*?)\r?\n`", patched_ui, re.S)[0]

    main_lua, on_open, list_action, opts_action, done_action = _extract_menu_scripts(
        patched_ui, require_script_list=has_script_list_click
    )

    # Opening with Standard Attack selected (index 18) must not index nil in scriptOptions
    lua_other, _ = _new_lua_harness(main_lua, {1: True}, initial_idx=18)
    lua_other.execute(on_open)
    assert lua_other.globals().showingSmartOptions is False

    # Opening with ADVANCED AI selected (index 2) unlocks options and sets description cleanly
    lua, saved = _new_lua_harness(
        main_lua,
        {1: True, 2: False, 3: True, 8: False, 9: True, 10: False, 11: False},
        initial_idx=2,
    )
    lua.execute(on_open)
    g = lua.globals()
    assert g.showingSmartOptions is True
    assert g.scriptDescription == "STR:CHARACTER_SCRIPT_SMART_SCRIPT_DESCRIPTION"
    assert len(g.scriptOptions) == 7

    # Row order & initial state
    expected_ids = [1, 2, 3, 8, 9, 10, 11]
    assert [g.scriptOptions[i][3] for i in range(1, 8)] == expected_ids
    assert [g.scriptOptions[i][4] for i in range(1, 8)] == [2, 0, 2, 0, 2, 0, 0]

    if has_script_list_click:
        g.scriptList_idx = 4
        lua.execute(list_action)
        assert g.showingSmartOptions is False
        g.scriptList_idx = 2
        lua.execute(list_action)
        assert g.showingSmartOptions is True

    # Toggle Attack Enemies (row 1, id=1) off then on
    g.selScriptOpt = 1
    g.cellNumber = 2
    lua.execute(opts_action)
    assert g.scriptOptions[1][5] is False and g.scriptOptions[1][4] == 0
    lua.execute(opts_action)
    assert g.scriptOptions[1][5] is True and g.scriptOptions[1][4] == 2

    # Prefer Melee (row 2, id=2) clears Prefer Ranged (row 3, id=3); clicking again turns both off
    g.selScriptOpt = 2
    lua.execute(opts_action)
    assert g.scriptOptions[2][5] is True and g.scriptOptions[3][5] is False
    assert g.scriptDescription == "STR:SCRIPT_USE_MELEE_WEAPONS_DESCRIPTION"
    lua.execute(opts_action)
    assert g.scriptOptions[2][5] is False and g.scriptOptions[3][5] is False

    # Clicking any of the 4 skills (rows 4..7 = ids 8, 9, 10, 11) keeps the other three off
    for row in (4, 5, 6, 7):
        g.selScriptOpt = row
        lua.execute(opts_action)
        for other in (4, 5, 6, 7):
            assert g.scriptOptions[other][5] is (other == row)
            assert g.scriptOptions[other][4] == (2 if other == row else 0)

    # Leave Turn Undead (row 7, id=11) active and Ranged (row 3, id=3) active, then click DONE
    g.selScriptOpt = 3
    lua.execute(opts_action)
    lua.execute(done_action)

    persisted = dict(saved.items())
    assert persisted == {1: True, 2: False, 3: True, 8: False, 9: False, 10: False, 11: True}
    for omitted_id in (4, 5, 6, 7):
        assert omitted_id not in persisted
