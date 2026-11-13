"""Offline WeiDU install, uninstall, idempotence, and "We Overwrite" policy tests."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from conftest import MOD_DIR, MOD_FOLDER_NAME
from fake_iwdee import (
    create_fake_iwdee_game,
    make_ui_menu_infinityui,
    make_ui_menu_leui,
    make_ui_menu_vanilla,
)


def _run_weidu(weidu_exe: Path, game_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    extra = () if "--use-lang" in args else ("--use-lang", "en_us")
    return subprocess.run(
        [str(weidu_exe), *extra, "--game", str(game_root), "--no-exit-pause", "--quick-log", *args],
        cwd=str(game_root),
        capture_output=True,
        text=True,
        check=False,
    )


def _install(weidu_exe: Path, game_root: Path) -> subprocess.CompletedProcess[str]:
    res = _run_weidu(
        weidu_exe,
        game_root,
        "--force-install-list",
        "0",
        "--language",
        "0",
        f"{MOD_FOLDER_NAME}/setup-{MOD_FOLDER_NAME}.tp2",
    )
    assert res.returncode == 0, f"WeiDU install failed ({res.returncode}):\n{res.stdout}\n{res.stderr}"
    assert "SUCCESSFULLY INSTALLED" in res.stdout
    assert "INSTALLED WITH WARNINGS" not in res.stdout
    assert "ERROR" not in res.stdout
    return res


def _uninstall(weidu_exe: Path, game_root: Path) -> subprocess.CompletedProcess[str]:
    res = _run_weidu(
        weidu_exe,
        game_root,
        f"{MOD_FOLDER_NAME}/setup-{MOD_FOLDER_NAME}.tp2",
        "--force-uninstall-list",
        "0",
    )
    assert res.returncode == 0, f"WeiDU uninstall failed ({res.returncode}):\n{res.stdout}\n{res.stderr}"
    assert "SUCCESSFULLY REMOVED" in res.stdout
    return res


def _decompile(weidu_exe: Path, game_root: Path, path: Path) -> str:
    out_dir = game_root / ".dec_tmp"
    out_dir.mkdir(exist_ok=True)
    res = _run_weidu(weidu_exe, game_root, "--no-auto-tp2", str(path), "--out", str(out_dir))
    assert res.returncode == 0, f"Decompile failed for {path}:\n{res.stdout}\n{res.stderr}"
    baf = out_dir / f"{path.stem}.baf"
    assert baf.is_file(), f"Expected decompiled {baf}"
    text = baf.read_text(encoding="utf-8", errors="replace")
    baf.unlink()
    return text


def _snapshot_tree(root: Path, subdirs: tuple[str, ...] = ("override", "scripts")) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    for sub in subdirs:
        base = root / sub
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                snap[f"{sub}/{p.relative_to(base).as_posix().lower()}"] = p.read_bytes()
    return snap


def _assert_weidu_parse_ok(res: subprocess.CompletedProcess[str]) -> None:
    combined = res.stdout + res.stderr
    assert res.returncode == 0, combined
    upper = combined.upper()
    assert "ERROR" not in upper and "FATAL" not in upper and "PARSE ERROR" not in upper, combined


def test_parse_check_all_sources(weidu_exe: Path, tmp_path: Path) -> None:
    game = tmp_path / "parse_game"
    create_fake_iwdee_game(game, weidu_exe, ui_menu_text=None, seed_scripts=False)

    tp2 = subprocess.run(
        [str(weidu_exe), "--no-auto-tp2", "--nogame", "--parse-check", "TP2",
         f"{MOD_FOLDER_NAME}/setup-{MOD_FOLDER_NAME}.tp2"],
        cwd=str(MOD_DIR.parent),
        capture_output=True,
        text=True,
        check=False,
    )
    _assert_weidu_parse_ok(tp2)

    for tpa in sorted((MOD_DIR / "lib").glob("*.tpa")):
        res = subprocess.run(
            [str(weidu_exe), "--no-auto-tp2", "--nogame", "--parse-check", "TPA", str(tpa)],
            capture_output=True,
            text=True,
            check=False,
        )
        _assert_weidu_parse_ok(res)

    for baf in sorted((MOD_DIR / "baf").glob("*.baf")):
        res = _run_weidu(weidu_exe, game, "--no-auto-tp2", "--parse-check", "BAF", str(baf))
        _assert_weidu_parse_ok(res)


def test_vanilla_install_scripts_ui_and_uninstall_restore(weidu_exe: Path, tmp_path: Path) -> None:
    game = tmp_path / "vanilla_biff_ui"
    create_fake_iwdee_game(
        game,
        weidu_exe,
        ui_menu_text=make_ui_menu_vanilla(),
        ui_in_override=False,
        seed_scripts=True,
    )
    before = _snapshot_tree(game)

    _install(weidu_exe, game)

    assert not (game / "override" / "SPELL.IDS.INSTALLED").exists()
    assert (game / "override" / "PARTYAI.2DA").read_text(encoding="ascii").split()[2] == "BDDEFAI"

    ui_out = (game / "override" / "UI.MENU").read_text(encoding="utf-8")
    assert "showingSmartOptions = (scriptList_idx == 2)" in ui_out
    assert "CHARACTER_SCRIPT_SMART_SCRIPT_DESCRIPTION" in ui_out
    assert "text color 'D'" in ui_out
    assert "SCRIPT_USE_ITEMS_LABEL" not in ui_out
    assert "SCRIPT_USE_SPECIAL_ABILITIES_LABEL" not in ui_out
    assert "SCRIPT_USE_OFFENSIVE_SPELLS_LABEL" not in ui_out
    assert "SCRIPT_USE_DEFENSIVE_SPELLS_LABEL" not in ui_out
    # Leave OTHER_MENU untouched outside CHARACTER_SCRIPT
    assert "name 'OTHER_MENU'\n\tonOpen\n\t\"\n\t\tshowingSmartOptions = false" in ui_out

    # Audit BDDEFAI.BCS and IWDPGEN.BCS: ActionListEmpty on every action block, zero spells/items
    bddefai_baf = _decompile(weidu_exe, game, game / "override" / "BDDEFAI.BCS")
    assert "AttackOneRound(NearestEnemyOf(Myself))" in bddefai_baf
    assert "AttackOneRound(SecondNearestEnemyOf(Myself))" in bddefai_baf
    assert "AttackOneRound(ThirdNearestEnemyOf(Myself))" in bddefai_baf
    assert 'HasItem("TROLLIMM",NearestEnemyOf(Myself))' in bddefai_baf
    assert "BattleSong()" in bddefai_baf
    assert "FindTraps()" in bddefai_baf
    assert "Turn()" in bddefai_baf
    assert "Hide()" in bddefai_baf
    for forbidden in ("Spell(", "SpellRES(", "UseItem(", "ReallyForceSpell(", "ApplySpell("):
        assert forbidden not in bddefai_baf

    iwdpgen_bcs_baf = _decompile(weidu_exe, game, game / "override" / "IWDPGEN.BCS")
    iwdpgen_bs_baf = _decompile(weidu_exe, game, game / "scripts" / "iwdpgen.BS")
    assert iwdpgen_bcs_baf == iwdpgen_bs_baf
    assert "AttackReevaluate(NearestEnemyOf(Myself),30)" in iwdpgen_bs_baf

    # Audit every non-empty .BS in scripts/
    for bs in sorted((game / "scripts").glob("*.BS")):
        if bs.stem.lower() == "none":
            continue
        txt = _decompile(weidu_exe, game, bs)
        blocks = re.findall(r"IF\r?\n(.*?)\r?\nEND", txt, re.S)
        assert blocks, f"{bs.name} has no script blocks"
        for idx, blk in enumerate(blocks):
            if any(tok in blk for tok in ("Attack(", "AttackOneRound(", "AttackReevaluate(")):
                assert "ActionListEmpty()" in blk, f"{bs.name} block {idx} missing ActionListEmpty()"
            # No bare [EVILCUTOFF] in Attack/See/InParty/Range (except !See([EVILCUTOFF]))
            assert "AttackReevaluate([EVILCUTOFF]" not in blk
            assert "AttackOneRound([EVILCUTOFF])" not in blk
            assert "Attack([EVILCUTOFF])" not in blk
            assert "!InParty([EVILCUTOFF])" not in blk
            for line in blk.splitlines():
                stripped = line.strip()
                if stripped.startswith("!See("):
                    continue
                assert stripped != "See([EVILCUTOFF])", f"{bs.name} block {idx} still has bare See([EVILCUTOFF])"

    # Out-of-combat !See([EVILCUTOFF]) must be preserved on bard0 / thief0
    bard0_baf = _decompile(weidu_exe, game, game / "scripts" / "bard0.BS")
    assert "!See([EVILCUTOFF])" in bard0_baf
    thief0_baf = _decompile(weidu_exe, game, game / "scripts" / "thief0.BS")
    assert "!See([EVILCUTOFF])" in thief0_baf

    # Idempotence on second install
    snap_after_first = _snapshot_tree(game)
    _install(weidu_exe, game)
    snap_after_second = _snapshot_tree(game)
    assert snap_after_first == snap_after_second

    # Clean byte-exact restore on uninstall
    _uninstall(weidu_exe, game)
    after_uninstall = _snapshot_tree(game)
    assert after_uninstall == before


def test_leui_and_infinityui_and_overwrite_edge_cases(weidu_exe: Path, tmp_path: Path) -> None:
    # 1. LeUI-IWDEE variant in override/
    leui_game = tmp_path / "leui_game"
    create_fake_iwdee_game(leui_game, weidu_exe, ui_menu_text=make_ui_menu_leui(), ui_in_override=True)
    leui_before = _snapshot_tree(leui_game)
    _install(weidu_exe, leui_game)
    leui_ui = (leui_game / "override" / "UI.MENU").read_text(encoding="utf-8")
    assert "text color S" in leui_ui
    assert "SCRIPT_USE_ITEMS_LABEL" not in leui_ui
    assert "CHARACTER_SCRIPT_SMART_SCRIPT_DESCRIPTION" in leui_ui
    snap1 = _snapshot_tree(leui_game)
    _install(weidu_exe, leui_game)
    assert _snapshot_tree(leui_game) == snap1
    _uninstall(weidu_exe, leui_game)
    assert _snapshot_tree(leui_game) == leui_before

    # 2. InfinityUI++ variant (dark skin rgdbcres + nil-index scriptDescription bug)
    inf_game = tmp_path / "inf_game"
    create_fake_iwdee_game(inf_game, weidu_exe, ui_menu_text=make_ui_menu_infinityui(), ui_in_override=True)
    inf_before = _snapshot_tree(inf_game)
    _install(weidu_exe, inf_game)
    inf_ui = (inf_game / "override" / "UI.MENU").read_text(encoding="utf-8")
    assert "scriptOptions[scriptList_idx]" not in inf_ui
    assert "text color 'D'" not in inf_ui
    assert "CHARACTER_SCRIPT_SMART_SCRIPT_DESCRIPTION" in inf_ui
    _uninstall(weidu_exe, inf_game)
    assert _snapshot_tree(inf_game) == inf_before

    # 3. Hand-edited / third-party files + corrupt unrelated script + missing UI.MENU
    weird_game = tmp_path / "weird_game"
    create_fake_iwdee_game(weird_game, weidu_exe, ui_menu_text=None, seed_scripts=True, corrupt_bs=True)
    (weird_game / "override" / "PARTYAI.2DA").write_text("2DA V1.0\nCUSTOMAI\n           AI_SCRIPT\n", encoding="ascii")
    (weird_game / "override" / "BDDEFAI.BCS").write_bytes(b"SC\nSC\n")
    (weird_game / "scripts" / "aGen.BS").write_bytes(b"SC\nSC\n")

    weird_res = _install(weidu_exe, weird_game)
    assert "UI.MENU not found" in weird_res.stdout
    assert "skipping unreadable script" in weird_res.stdout
    assert (weird_game / "override" / "PARTYAI.2DA").read_text(encoding="ascii").split()[2] == "BDDEFAI"
    assert len((weird_game / "override" / "BDDEFAI.BCS").read_bytes()) > 200
    assert len((weird_game / "scripts" / "aGen.BS").read_bytes()) > 200
    assert (weird_game / "scripts" / "broken.BS").read_bytes() == b"NOT_A_BCS_FILE"

    # 4. Missing scripts/ directory completely
    no_scripts_game = tmp_path / "no_scripts_game"
    create_fake_iwdee_game(
        no_scripts_game, weidu_exe, ui_menu_text=make_ui_menu_vanilla(), ui_in_override=True, seed_scripts=False
    )
    assert not (no_scripts_game / "scripts").exists()
    _install(weidu_exe, no_scripts_game)
    assert (no_scripts_game / "scripts" / "aGen.BS").is_file()
    assert (no_scripts_game / "scripts" / "apass.BS").is_file()
    assert (no_scripts_game / "scripts" / "iwdpgen.BS").is_file()

    # 5. CRLF UI.MENU preserves idempotence and byte-exact uninstall restore
    crlf_game = tmp_path / "crlf_ui_game"
    create_fake_iwdee_game(
        crlf_game,
        weidu_exe,
        ui_menu_text=make_ui_menu_vanilla().replace("\n", "\r\n"),
        ui_in_override=True,
        seed_scripts=False,
    )
    crlf_before = _snapshot_tree(crlf_game)
    _install(weidu_exe, crlf_game)
    crlf_ui = (crlf_game / "override" / "UI.MENU").read_bytes()
    assert b"CHARACTER_SCRIPT_SMART_SCRIPT_DESCRIPTION') end\r\n" in crlf_ui
    crlf_snap1 = _snapshot_tree(crlf_game)
    _install(weidu_exe, crlf_game)
    assert _snapshot_tree(crlf_game) == crlf_snap1
    _uninstall(weidu_exe, crlf_game)
    assert _snapshot_tree(crlf_game) == crlf_before
