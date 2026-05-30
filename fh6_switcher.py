"""
FH6 字幕語音切換工具  (FH6 Subtitle / Voice Switcher)

Lets any Forza Horizon 6 owner mix and match subtitle language with voice language
by swapping the per-language StringTables zips.

This tool only does file copies — it never modifies the game executable, hooks the
process, or touches network traffic. Backups of each replaced zip are stored under
StringTables/_backup/ and can be restored at any time.

Author: built collaboratively with Claude
License: MIT
"""
from __future__ import annotations

import hashlib
import json
import locale
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_VERSION = "1.3.0"
WRAPPER_BAT_NAME = "fh6_prelaunch_wrapper.bat"
PREFERRED_LANG_FILENAME = "UserPreferredLang"


# ---------------------------------------------------------------- translations
# Two UI languages. Lookup falls back to English on missing keys.
TR: dict[str, dict[str, str]] = {
    "zh_TW": {
        # window / app
        "app_name": "FH6 字幕語音切換工具",
        # menu
        "menu_language": "語言 / Language",
        "lang_zh_TW": "繁體中文",
        "lang_en": "English",
        # frame titles
        "frame_path": "遊戲路徑",
        "frame_combo": "語言組合",
        "frame_wrapper_steam": "Steam 啟動前自動補套（強烈建議）",
        "frame_wrapper_xbox": "Steam 啟動前自動補套（不適用於 MS Store 版）",
        "frame_wrapper_default": "Steam 啟動前自動補套（僅限 Steam 版）",
        "frame_log": "日誌",
        # labels
        "label_path_undetected": "（尚未偵測）",
        "label_subtitle_lang": "字幕語言",
        "label_voice_lang": "語音語言",
        "wrapper_desc_steam": (
            "勾選後產生包裝腳本並把 Steam 啟動選項複製到剪貼簿。\n"
            "之後每次按 Steam「遊玩」會先自動套用你選的組合再啟動 FH6。"),
        "wrapper_desc_xbox": (
            "你目前用的是 MS Store / Xbox PC App 版 FH6，Xbox App 沒有 Steam\n"
            "那種「啟動選項」可以掛 wrapper，此功能不適用。\n"
            "Forza 更新後，重新打開本工具按一次「套用」即可。"),
        # buttons
        "btn_auto_detect": "自動偵測",
        "btn_browse": "手動選擇…",
        "btn_apply": "套用",
        "btn_restore": "還原全部",
        "btn_rescan": "重新掃描狀態",
        "btn_setup_wrapper": "設定 Steam 啟動補套",
        "btn_open_config": "開啟設定資料夾",
        # status messages
        "status_no_path": "尚未設定路徑",
        "status_read_error": "無法讀取狀態：{err}",
        "status_ingame_lang": "遊戲內語言設定 = {label}",
        "status_ingame_lang_missing": "遊戲內語言設定 = （尚未設定或檔案不存在）",
        "status_zip_swapped": "{code}.zip 目前內容 = {match} ({backup})",
        "status_backed_up": "已備份",
        "status_not_backed_up": "未備份",
        "status_all_original": "所有語言檔都是原始狀態。",
        # dialogs
        "dlg_warn_set_path": "請先設定遊戲路徑。",
        "dlg_warn_select_langs": "請選擇字幕和語音語言。",
        "dlg_warn_invalid_dir": "無效的資料夾：{msg}",
        "dlg_invalid_path_reason_missing": "資料夾不存在",
        "dlg_invalid_path_reason_no_fh6": "資料夾不像 FH6 StringTables（缺少 {files}）",
        "dlg_pick_folder": "選擇 FH6 的 StringTables 資料夾",
        "dlg_confirm_restore": "確定要把 _backup 裡的所有檔案還原回去嗎？",
        "dlg_autodetect_failed": (
            "找不到 Forza Horizon 6 的 StringTables 資料夾。\n\n"
            "請按「手動選擇…」指到：\n"
            r"<Steam>\steamapps\common\ForzaHorizon6\media\Stripped\StringTables"),
        "dlg_wrapper_xbox": (
            "此功能僅適用於 Steam 版。\n\n"
            "MS Store / Xbox PC App 透過 Xbox App 啟動 UWP 應用，"
            "沒有 Steam 那種「啟動選項」欄位可以掛 wrapper，"
            "所以無法做到「按遊玩自動套用」這件事。\n\n"
            "你目前的做法：Forza 每次更新後，重新打開本工具按一次「套用」即可。"),
        "dlg_wrapper_setup_failed": "寫入 wrapper 失敗：{err}",
        "dlg_wrapper_setup_title": " — Steam 設定",
        "dlg_wrapper_setup_body": (
            "已產生啟動包裝腳本。\n\n"
            "請開啟 Steam，依下列步驟：\n\n"
            "  1. 媒體庫 → 對「Forza Horizon 6」按右鍵 → 內容\n"
            "  2. 在「一般」頁籤找到「啟動選項」\n"
            "  3. 貼上以下這行（已複製到剪貼簿）：\n\n"
            "     {opts}\n\n"
            "  4. 關閉視窗即可生效\n\n"
            "之後每次按「遊玩」會自動套用目前的字幕／語音組合。"),
        # log messages
        "log_started": "{app} v{ver} 已啟動。",
        "log_autodetect_searching": "自動偵測 Steam 安裝中…",
        "log_autodetect_found": "偵測到：{path}",
        "log_autodetect_failed": "自動偵測失敗。請按「手動選擇…」指到 FH6 的 StringTables 資料夾。",
        "log_path_set": "已設定路徑：{path}",
        "log_apply_target": "[套用] {dst} ← {src}",
        "log_apply_target_with_other": "[套用] {dst} ← {src}  ({note} 也覆蓋)",
        "log_apply_failed": "[失敗] 覆蓋 {dst} 失敗，可能權限不足，請以系統管理員身分執行。",
        "log_apply_noop_same": "兩邊選一樣，不需要動作（這就是原版設定）。",
        "log_apply_noop_already": "{dst} 已經是 {code} 內容，不需要重複套用。",
        "log_apply_backup": "[備份] {dst} → _backup/{dst}",
        "log_apply_done_hint": "進遊戲不用再調語言，會直接是這個組合。",
        "log_set_preferred_lang": "[設定] UserPreferredLang ← {code}   ({path})",
        "log_set_preferred_lang_multi": "（同時寫入 {n} 個位置 — Steam + MS Store 沙盒）",
        "log_set_preferred_warn": "[警告] 無法寫入 UserPreferredLang：{err}（你還是可以手動進遊戲設定語言）",
        "log_restore_each": "[還原] {name}",
        "log_restore_failed_each": "[失敗] 還原 {name} 失敗",
        "log_restore_no_backup": "沒有 _backup 資料夾，沒東西需要還原。",
        "log_restore_empty": "_backup 是空的。",
        "log_wrapper_generated": "已產生 wrapper：{path}",
        "log_wrapper_launch_opts": "Steam 啟動選項：{opts}",
        "log_wrapper_copied": "（已複製到剪貼簿）",
        "log_error_generic": "[錯誤] {err}",
        # language change banner in log
        "log_lang_switched": "── 介面語言已切換 / UI language changed ──",
    },
    "en": {
        "app_name": "FH6 Subtitle Switcher",
        "menu_language": "Language",
        "lang_zh_TW": "繁體中文",
        "lang_en": "English",
        "frame_path": "Game Path",
        "frame_combo": "Language Combination",
        "frame_wrapper_steam": "Auto-Apply on Steam Launch (Highly Recommended)",
        "frame_wrapper_xbox": "Auto-Apply on Steam Launch (Not for MS Store)",
        "frame_wrapper_default": "Auto-Apply on Steam Launch (Steam only)",
        "frame_log": "Log",
        "label_path_undetected": "(not detected yet)",
        "label_subtitle_lang": "Subtitle language",
        "label_voice_lang": "Voice language",
        "wrapper_desc_steam": (
            "Generates a wrapper script and copies the Steam launch-options\n"
            "string to your clipboard. After setup, clicking Steam's Play\n"
            "button auto-applies your selected combo before launching FH6."),
        "wrapper_desc_xbox": (
            "You're on the MS Store / Xbox PC App version. The Xbox App has no\n"
            "equivalent of Steam's Launch Options, so this feature does not apply.\n"
            "After each Forza update, just reopen this tool and click \"Apply\"."),
        "btn_auto_detect": "Auto-Detect",
        "btn_browse": "Browse…",
        "btn_apply": "Apply",
        "btn_restore": "Restore All",
        "btn_rescan": "Rescan",
        "btn_setup_wrapper": "Set Up Launch Wrapper",
        "btn_open_config": "Open Config Folder",
        "status_no_path": "Game path not configured.",
        "status_read_error": "Unable to read state: {err}",
        "status_ingame_lang": "In-game language = {label}",
        "status_ingame_lang_missing": "In-game language = (not yet set or file missing)",
        "status_zip_swapped": "{code}.zip currently holds {match} ({backup})",
        "status_backed_up": "backed up",
        "status_not_backed_up": "not backed up",
        "status_all_original": "All language files are in their original state.",
        "dlg_warn_set_path": "Please set the game path first.",
        "dlg_warn_select_langs": "Please pick both a subtitle and a voice language.",
        "dlg_warn_invalid_dir": "Invalid folder: {msg}",
        "dlg_invalid_path_reason_missing": "Folder does not exist",
        "dlg_invalid_path_reason_no_fh6": "Folder doesn't look like FH6 StringTables (missing {files})",
        "dlg_pick_folder": "Select the FH6 StringTables folder",
        "dlg_confirm_restore": "Restore every file in _backup back to the parent folder?",
        "dlg_autodetect_failed": (
            "Couldn't find the Forza Horizon 6 StringTables folder.\n\n"
            "Please click \"Browse…\" and point to:\n"
            r"<Steam>\steamapps\common\ForzaHorizon6\media\Stripped\StringTables"),
        "dlg_wrapper_xbox": (
            "This feature is Steam-only.\n\n"
            "The MS Store / Xbox PC App launches UWP apps through AppContainer; "
            "there is no equivalent of Steam's Launch Options to hook a wrapper "
            "into, so the auto-apply-on-Play workflow cannot be reproduced.\n\n"
            "Workaround: after each Forza update, reopen this tool and click \"Apply\" once."),
        "dlg_wrapper_setup_failed": "Failed to write wrapper: {err}",
        "dlg_wrapper_setup_title": " — Steam Setup",
        "dlg_wrapper_setup_body": (
            "Launch wrapper generated.\n\n"
            "In Steam, do the following:\n\n"
            "  1. Library → right-click \"Forza Horizon 6\" → Properties\n"
            "  2. On the \"General\" tab, find \"Launch Options\"\n"
            "  3. Paste this line (already copied to your clipboard):\n\n"
            "     {opts}\n\n"
            "  4. Close the window — it saves automatically.\n\n"
            "After that, clicking \"Play\" will auto-apply your subtitle/voice combo before launching FH6."),
        "log_started": "{app} v{ver} started.",
        "log_autodetect_searching": "Auto-detecting Steam install…",
        "log_autodetect_found": "Detected: {path}",
        "log_autodetect_failed": "Auto-detect failed. Click \"Browse…\" and point to the FH6 StringTables folder.",
        "log_path_set": "Path set: {path}",
        "log_apply_target": "[Applied] {dst} ← {src}",
        "log_apply_target_with_other": "[Applied] {dst} ← {src}  ({note} also overwritten)",
        "log_apply_failed": "[Failed] Could not overwrite {dst}. Try running as Administrator.",
        "log_apply_noop_same": "Subtitle and voice language match — nothing to do (this is the original layout).",
        "log_apply_noop_already": "{dst} already contains {code} content — skipping.",
        "log_apply_backup": "[Backed up] {dst} → _backup/{dst}",
        "log_apply_done_hint": "All set. Just launch the game — no need to touch in-game language settings.",
        "log_set_preferred_lang": "[Set] UserPreferredLang ← {code}   ({path})",
        "log_set_preferred_lang_multi": "(Written to {n} locations — Steam + MS Store sandbox)",
        "log_set_preferred_warn": "[Warning] Couldn't write UserPreferredLang: {err}. You can still set the language manually in-game.",
        "log_restore_each": "[Restored] {name}",
        "log_restore_failed_each": "[Failed] Restoring {name} failed",
        "log_restore_no_backup": "No _backup folder — nothing to restore.",
        "log_restore_empty": "_backup is empty.",
        "log_wrapper_generated": "Wrapper generated: {path}",
        "log_wrapper_launch_opts": "Steam launch options: {opts}",
        "log_wrapper_copied": "(Copied to clipboard.)",
        "log_error_generic": "[Error] {err}",
        "log_lang_switched": "── UI language changed / 介面語言已切換 ──",
    },
}


def detect_system_lang() -> str:
    """Return a default UI lang code based on the OS locale."""
    try:
        loc = locale.getdefaultlocale()[0] or ""
    except Exception:
        loc = ""
    if loc.lower().startswith("zh"):
        return "zh_TW"
    return "en"


# ---------------------------------------------------------------- language map
# Maps StringTables zip filename (without .zip) to a display label.
# Order here is preserved in the dropdown.
LANGS: list[tuple[str, str]] = [
    ("CHT", "繁體中文 (Traditional Chinese)"),
    ("CHS", "简体中文 (Simplified Chinese)"),
    ("JP",  "日本語 (Japanese)"),
    ("KO",  "한국어 (Korean)"),
    ("EN",  "English (US)"),
    ("GB",  "English (UK)"),
    ("DE",  "Deutsch (German)"),
    ("FR",  "Français (French)"),
    ("ES",  "Español (Spanish)"),
    ("MX",  "Español de México (Latin American Spanish)"),
    ("IT",  "Italiano (Italian)"),
    ("PT",  "Português (Portuguese)"),
    ("BR",  "Português do Brasil (Brazilian Portuguese)"),
    ("RU",  "Русский (Russian)"),
    ("PL",  "Polski (Polish)"),
    ("CZ",  "Čeština (Czech)"),
    ("NL",  "Nederlands (Dutch)"),
    ("DK",  "Dansk (Danish)"),
    ("SV",  "Svenska (Swedish)"),
    ("NO",  "Norsk (Norwegian)"),
    ("FI",  "Suomi (Finnish)"),
    ("HU",  "Magyar (Hungarian)"),
    ("TR",  "Türkçe (Turkish)"),
    ("EL",  "Ελληνικά (Greek)"),
]
CODE_TO_LABEL = {code: f"{label}  [{code}]" for code, label in LANGS}
LABEL_TO_CODE = {v: k for k, v in CODE_TO_LABEL.items()}
ALL_LABELS = list(CODE_TO_LABEL.values())


# ---------------------------------------------------------------- config store
def _config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(base) / "FH6SubtitleSwitcher"
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_config() -> dict:
    cfg_file = _config_dir() / "config.json"
    if cfg_file.exists():
        try:
            return json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg: dict) -> None:
    cfg_file = _config_dir() / "config.json"
    cfg_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- steam detect
def _steam_install_path() -> Path | None:
    """Read SteamPath from registry."""
    try:
        import winreg  # type: ignore
    except ImportError:
        return None
    for hive, key in [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
    ]:
        try:
            with winreg.OpenKey(hive, key) as k:
                for value_name in ("SteamPath", "InstallPath"):
                    try:
                        val, _ = winreg.QueryValueEx(k, value_name)
                        p = Path(str(val).replace("/", "\\"))
                        if p.exists():
                            return p
                    except FileNotFoundError:
                        continue
        except FileNotFoundError:
            continue
    return None


def _parse_libraryfolders(vdf_path: Path) -> list[Path]:
    """Crude VDF parse — extract every 'path' value."""
    libs: list[Path] = []
    try:
        text = vdf_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return libs
    import re
    for m in re.finditer(r'"path"\s*"([^"]+)"', text):
        raw = m.group(1).replace("\\\\", "\\")
        p = Path(raw)
        if p.exists():
            libs.append(p)
    return libs


def _available_drives() -> list[Path]:
    """Enumerate fixed/removable drives that currently have a root directory."""
    drives: list[Path] = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        p = Path(f"{letter}:\\")
        if p.exists():
            drives.append(p)
    return drives


def find_xbox_stringtables() -> Path | None:
    """Find FH6 StringTables for the MS Store / Xbox PC App install.

    Xbox PC App stores games at `<drive>:\\XboxGames\\<game name>\\Content\\`.
    The folder name may vary slightly between editions, so glob it.
    """
    for drive in _available_drives():
        xbox_root = drive / "XboxGames"
        if not xbox_root.exists():
            continue
        # match "Forza Horizon 6", "Forza Horizon 6 Standard Edition", etc.
        for sub in xbox_root.glob("Forza Horizon 6*"):
            # Xbox PC App paths are case-insensitive on Windows but report
            # in lowercase from the reporter — accept either.
            for candidate in [
                sub / "Content" / "media" / "Stripped" / "StringTables",
                sub / "Content" / "media" / "stripped" / "stringtables",
            ]:
                if candidate.exists():
                    return candidate
    return None


def find_fh6_stringtables() -> Path | None:
    """Look for FH6 StringTables across all Steam libraries and Xbox installs."""
    # Try Steam first
    steam = _steam_install_path()
    libs: list[Path] = []
    if steam:
        libs.append(steam)
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            libs.extend(_parse_libraryfolders(vdf))
    seen, ordered = set(), []
    for p in libs:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            ordered.append(rp)
    for lib in ordered:
        candidate = lib / "steamapps" / "common" / "ForzaHorizon6" / "media" / "Stripped" / "StringTables"
        if candidate.exists():
            return candidate
    # Fall back to Xbox / MS Store
    return find_xbox_stringtables()


def _localappdata() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base)


def forza_appdata_dir() -> Path:
    """%LOCALAPPDATA%\\ForzaHorizon6 — the Steam-build preference location."""
    return _localappdata() / "ForzaHorizon6"


def forza_appdata_candidates() -> list[Path]:
    """All plausible locations of Forza's UserPreferredLang.

    Steam build:  %LOCALAPPDATA%\\ForzaHorizon6\\
    MS Store / Xbox PC App:  %LOCALAPPDATA%\\Packages\\<UWP-package>\\LocalState\\
    """
    candidates: list[Path] = [forza_appdata_dir()]
    packages = _localappdata() / "Packages"
    if packages.exists():
        for sub in packages.iterdir():
            if not sub.is_dir():
                continue
            name = sub.name
            # FH6 UWP package family. The publisher hash 8wekyb3d8bbwe is Microsoft's.
            if ("Forza" in name) or ("624F8B84B80" in name) or ("FH6" in name):
                local_state = sub / "LocalState"
                if local_state.exists():
                    candidates.append(local_state)
                else:
                    candidates.append(sub)
    return candidates


def read_preferred_lang() -> str | None:
    """Return the first non-empty UserPreferredLang value found."""
    for d in forza_appdata_candidates():
        f = d / PREFERRED_LANG_FILENAME
        if f.exists():
            try:
                v = f.read_text(encoding="ascii", errors="strict").strip()
                if v:
                    return v
            except Exception:
                continue
    return None


def write_preferred_lang(code: str) -> list[Path]:
    """Write Forza's preferred-language to every candidate location.

    Always writes to %LOCALAPPDATA%\\ForzaHorizon6\\ (Steam location).
    Also writes to any MS Store / UWP sandbox locations found under
    %LOCALAPPDATA%\\Packages\\. Returns the list of paths actually written.
    """
    payload = code.encode("ascii")
    written: list[Path] = []
    # Steam location — create folder if missing (cheap and idempotent)
    steam_dir = forza_appdata_dir()
    steam_dir.mkdir(parents=True, exist_ok=True)
    target = steam_dir / PREFERRED_LANG_FILENAME
    target.write_bytes(payload)
    written.append(target)
    # MS Store sandbox locations — only if folder already exists
    packages = _localappdata() / "Packages"
    if packages.exists():
        for sub in packages.iterdir():
            if not sub.is_dir():
                continue
            name = sub.name
            if ("Forza" in name) or ("624F8B84B80" in name) or ("FH6" in name):
                local_state = sub / "LocalState"
                if not local_state.exists():
                    continue
                f = local_state / PREFERRED_LANG_FILENAME
                try:
                    f.write_bytes(payload)
                    written.append(f)
                except Exception:
                    pass
    return written


def is_xbox_install(p: Path) -> bool:
    """Detect MS Store / Xbox PC App install by path marker."""
    return any(part.lower() == "xboxgames" for part in p.parts)


def is_steam_install(p: Path) -> bool:
    """Detect Steam install by path marker."""
    return any(part.lower() == "steamapps" for part in p.parts)


def validate_stringtables_dir(p: Path) -> tuple[bool, str, dict]:
    """Sanity check. Returns (ok, error_key, fmt_kwargs)."""
    if not p.exists() or not p.is_dir():
        return False, "dlg_invalid_path_reason_missing", {}
    required = ["CHT.zip", "EN.zip", "JP.zip"]
    missing = [r for r in required if not (p / r).exists()]
    if missing:
        return False, "dlg_invalid_path_reason_no_fh6", {"files": ", ".join(missing)}
    return True, "", {}


# ---------------------------------------------------------------- file helpers
def sha256_file(p: Path, _cache: dict[str, str] = {}) -> str:
    key = f"{p}:{p.stat().st_mtime_ns}:{p.stat().st_size}"
    if key in _cache:
        return _cache[key]
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()
    _cache[key] = digest
    return digest


@dataclass
class ZipState:
    code: str
    size: int
    sha: str
    backed_up: bool
    matches_code: str | None      # which other language code its content matches, if any

    @property
    def label(self) -> str:
        return CODE_TO_LABEL.get(self.code, self.code)


def scan_state(st_dir: Path) -> dict[str, ZipState]:
    """Build a state map for all known language zips."""
    backup_dir = st_dir / "_backup"
    # Index by sha to find duplicates
    sha_to_code: dict[str, str] = {}
    sizes: dict[str, int] = {}
    shas: dict[str, str] = {}
    for code, _ in LANGS:
        zp = st_dir / f"{code}.zip"
        if zp.exists():
            sizes[code] = zp.stat().st_size
            shas[code] = sha256_file(zp)
            sha_to_code.setdefault(shas[code], code)
    state: dict[str, ZipState] = {}
    for code, _ in LANGS:
        if code not in shas:
            continue
        s = shas[code]
        backed = (backup_dir / f"{code}.zip").exists()
        matches = sha_to_code.get(s) if sha_to_code.get(s) != code else None
        state[code] = ZipState(code=code, size=sizes[code], sha=s,
                                backed_up=backed, matches_code=matches)
    return state


def apply_swap(st_dir: Path, sub_code: str, voice_code: str) -> list[tuple[str, dict]]:
    """Copy <sub>.zip → <voice>.zip slot. Returns a list of (translation_key, fmt_kwargs)."""
    src = st_dir / f"{sub_code}.zip"
    dst = st_dir / f"{voice_code}.zip"
    if not src.exists():
        raise FileNotFoundError(str(src))
    if not dst.exists():
        raise FileNotFoundError(str(dst))
    backup_dir = st_dir / "_backup"
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / dst.name
    actions: list[tuple[str, dict]] = []
    if sub_code == voice_code:
        return [("log_apply_noop_same", {})]
    # Refresh backup if missing; else short-circuit if already applied
    if not backup.exists():
        shutil.copy2(dst, backup)
        actions.append(("log_apply_backup", {"dst": dst.name}))
    else:
        if sha256_file(dst) == sha256_file(src):
            return [("log_apply_noop_already", {"dst": dst.name, "code": sub_code})]
    shutil.copy2(src, dst)
    actions.append(("log_apply_target", {"dst": dst.name, "src": src.name}))
    # English voice has two variants (EN + GB) — when target is one, also do the other
    if voice_code in ("EN", "GB"):
        other_name = "GB.zip" if voice_code == "EN" else "EN.zip"
        other = st_dir / other_name
        if other.exists():
            other_bk = backup_dir / other_name
            if not other_bk.exists():
                shutil.copy2(other, other_bk)
                actions.append(("log_apply_backup", {"dst": other_name}))
            shutil.copy2(src, other)
            note = "UK English" if voice_code == "EN" else "US English"
            actions.append(("log_apply_target_with_other",
                           {"dst": other_name, "src": src.name, "note": note}))
    return actions


def restore_all(st_dir: Path) -> list[tuple[str, dict]]:
    backup_dir = st_dir / "_backup"
    if not backup_dir.exists():
        return [("log_restore_no_backup", {})]
    actions: list[tuple[str, dict]] = []
    for f in sorted(backup_dir.glob("*.zip")):
        target = st_dir / f.name
        try:
            shutil.copy2(f, target)
            actions.append(("log_restore_each", {"name": f.name}))
        except Exception:
            actions.append(("log_restore_failed_each", {"name": f.name}))
    if not actions:
        return [("log_restore_empty", {})]
    return actions


# ---------------------------------------------------------------- steam wrapper
def write_wrapper(st_dir: Path, sub_code: str, voice_code: str) -> Path:
    """Create a wrapper .bat in %APPDATA% that re-applies the swap before launch."""
    wrapper_dir = _config_dir()
    wrapper = wrapper_dir / WRAPPER_BAT_NAME
    extra_gb = ""
    if voice_code in ("EN", "GB"):
        other = "GB.zip" if voice_code == "EN" else "EN.zip"
        extra_gb = (
            f'    if exist "{other}" (\n'
            f'        if not exist "_backup\\{other}" copy /Y "{other}" "_backup\\{other}" >nul\n'
            f'        copy /Y "{sub_code}.zip" "{other}" >nul\n'
            f"    )\n"
        )
    # Bake in all detected UserPreferredLang candidate dirs so the wrapper
    # works for both Steam and MS Store installs.
    pref_lines = []
    for d in forza_appdata_candidates():
        pref_lines.append(
            f'if exist "{d}" <nul set /p="{voice_code}" > "{d}\\{PREFERRED_LANG_FILENAME}"\r\n'
        )
    # Always include Steam location even if it does not yet exist
    steam_dir = forza_appdata_dir()
    if not any(str(steam_dir) in line for line in pref_lines):
        pref_lines.insert(0,
            f'if not exist "{steam_dir}" mkdir "{steam_dir}" >nul 2>nul\r\n'
            f'<nul set /p="{voice_code}" > "{steam_dir}\\{PREFERRED_LANG_FILENAME}"\r\n'
        )
    pref_block = "".join(pref_lines)

    content = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "setlocal\r\n"
        "\r\n"
        f'set "FH6DIR={st_dir}"\r\n'
        f'set "SUB={sub_code}.zip"\r\n'
        f'set "VOICE={voice_code}.zip"\r\n'
        "\r\n"
        'if exist "%FH6DIR%\\%SUB%" if exist "%FH6DIR%\\%VOICE%" (\r\n'
        '    pushd "%FH6DIR%" >nul\r\n'
        '    if not exist "_backup" mkdir "_backup"\r\n'
        '    if not exist "_backup\\%VOICE%" copy /Y "%VOICE%" "_backup\\%VOICE%" >nul\r\n'
        '    copy /Y "%SUB%" "%VOICE%" >nul\r\n'
        f"{extra_gb}"
        '    popd >nul\r\n'
        ")\r\n"
        "\r\n"
        "REM Also overwrite Forza's saved UI language so the in-game setting is auto-set\r\n"
        f"{pref_block}"
        "\r\n"
        "%*\r\n"
    )
    wrapper.write_text(content, encoding="utf-8")
    return wrapper


def copy_to_clipboard(text: str) -> bool:
    try:
        proc = subprocess.run(
            ["clip"], input=text.encode("utf-16-le"), check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return proc.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------- main UI
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # icon (works when running .exe with embedded icon too — best-effort)
        try:
            ico = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "icon.ico"
            if ico.exists():
                self.iconbitmap(str(ico))
        except Exception:
            pass

        self.cfg = load_config()
        self.lang = self.cfg.get("ui_lang") or detect_system_lang()
        if self.lang not in TR:
            self.lang = "en"
        self.lang_var = tk.StringVar(value=self.lang)

        self.st_dir: Path | None = None
        if (saved := self.cfg.get("stringtables_dir")):
            p = Path(saved)
            ok, _, _ = validate_stringtables_dir(p)
            if ok:
                self.st_dir = p

        # Tracked widgets/menus for live language switching.
        # Each entry: (widget, attr_name, key) or for menus: ("menu", menu, index, key)
        self._text_refs: list[tuple] = []

        self.title(f"{self.t('app_name')}  v{APP_VERSION}")
        self.geometry("680x640")
        self.minsize(680, 640)

        self._build_menubar()
        self._build_ui()
        # Run initial detection in background to avoid blocking UI
        self.after(100, self._auto_detect_if_needed)

    # ---- translation
    def t(self, key: str, **kwargs) -> str:
        table = TR.get(self.lang, TR["en"])
        s = table.get(key) or TR["en"].get(key) or key
        if kwargs:
            try:
                return s.format(**kwargs)
            except Exception:
                return s
        return s

    def _track(self, widget, key: str, attr: str = "text"):
        """Remember a widget so we can re-translate it on language switch."""
        widget.configure(**{attr: self.t(key)})
        self._text_refs.append(("widget", widget, attr, key))
        return widget

    def _track_var(self, var: tk.StringVar, key: str):
        var.set(self.t(key))
        self._text_refs.append(("var", var, key))
        return var

    def _track_menu(self, menu: tk.Menu, index, key: str, kind: str = "label"):
        menu.entryconfigure(index, **{kind: self.t(key)})
        self._text_refs.append(("menu", menu, index, kind, key))

    # ---- UI construction
    def _build_menubar(self):
        menubar = tk.Menu(self)
        lang_menu = tk.Menu(menubar, tearoff=0)
        lang_menu.add_radiobutton(label=self.t("lang_zh_TW"),
                                  variable=self.lang_var, value="zh_TW",
                                  command=self._on_lang_change)
        lang_menu.add_radiobutton(label=self.t("lang_en"),
                                  variable=self.lang_var, value="en",
                                  command=self._on_lang_change)
        self._lang_menu = lang_menu
        menubar.add_cascade(label=self.t("menu_language"), menu=lang_menu)
        self._menubar = menubar
        self._menu_lang_idx = menubar.index("end")
        self.configure(menu=menubar)
        # Track for re-translation
        self._text_refs.append(("menubar", menubar, self._menu_lang_idx, "menu_language"))
        self._text_refs.append(("submenu", lang_menu, 0, "lang_zh_TW"))
        self._text_refs.append(("submenu", lang_menu, 1, "lang_en"))

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # ---- Path frame
        path_frame = ttk.LabelFrame(self)
        self._track(path_frame, "frame_path")
        path_frame.pack(fill="x", **pad)
        self.path_var = tk.StringVar(
            value=str(self.st_dir) if self.st_dir else self.t("label_path_undetected"))
        self.path_label = ttk.Label(path_frame, textvariable=self.path_var, foreground="#444")
        self.path_label.pack(fill="x", padx=8, pady=6)
        btns = ttk.Frame(path_frame)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        b1 = ttk.Button(btns, command=self._do_auto_detect)
        self._track(b1, "btn_auto_detect")
        b1.pack(side="left")
        b2 = ttk.Button(btns, command=self._do_browse)
        self._track(b2, "btn_browse")
        b2.pack(side="left", padx=(8, 0))

        # ---- Selection frame
        sel = ttk.LabelFrame(self)
        self._track(sel, "frame_combo")
        sel.pack(fill="x", **pad)
        grid = ttk.Frame(sel)
        grid.pack(fill="x", padx=8, pady=8)
        lbl_sub = ttk.Label(grid)
        self._track(lbl_sub, "label_subtitle_lang")
        lbl_sub.grid(row=0, column=0, sticky="w", pady=4)
        lbl_voice = ttk.Label(grid)
        self._track(lbl_voice, "label_voice_lang")
        lbl_voice.grid(row=1, column=0, sticky="w", pady=4)
        self.sub_var = tk.StringVar(value=CODE_TO_LABEL[self.cfg.get("sub", "CHT")])
        self.voice_var = tk.StringVar(value=CODE_TO_LABEL[self.cfg.get("voice", "JP")])
        self.sub_combo = ttk.Combobox(grid, textvariable=self.sub_var, values=ALL_LABELS,
                                      state="readonly", width=46)
        self.voice_combo = ttk.Combobox(grid, textvariable=self.voice_var, values=ALL_LABELS,
                                        state="readonly", width=46)
        self.sub_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.voice_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)
        grid.columnconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="—")
        ttk.Label(sel, textvariable=self.status_var, foreground="#0066aa",
                  wraplength=620, justify="left").pack(fill="x", padx=8, pady=(0, 6))

        action = ttk.Frame(sel)
        action.pack(fill="x", padx=8, pady=(0, 8))
        ba = ttk.Button(action, command=self._do_apply, width=14)
        self._track(ba, "btn_apply")
        ba.pack(side="left")
        br = ttk.Button(action, command=self._do_restore, width=14)
        self._track(br, "btn_restore")
        br.pack(side="left", padx=(8, 0))
        bs = ttk.Button(action, command=self._refresh_status, width=16)
        self._track(bs, "btn_rescan")
        bs.pack(side="right")

        # ---- Steam wrapper frame
        self.wrap_frame = ttk.LabelFrame(self)
        self._track(self.wrap_frame, "frame_wrapper_default")
        self.wrap_frame.pack(fill="x", **pad)
        self.wrap_desc_var = tk.StringVar(value=self.t("wrapper_desc_steam"))
        ttk.Label(self.wrap_frame, textvariable=self.wrap_desc_var,
                  foreground="#444", justify="left", wraplength=620).pack(anchor="w", padx=8, pady=(6, 4))
        wbtn = ttk.Frame(self.wrap_frame)
        wbtn.pack(fill="x", padx=8, pady=(0, 8))
        self.wrap_button = ttk.Button(wbtn, command=self._do_setup_wrapper, width=24)
        self._track(self.wrap_button, "btn_setup_wrapper")
        self.wrap_button.pack(side="left")
        bo = ttk.Button(wbtn, command=self._open_config_dir, width=20)
        self._track(bo, "btn_open_config")
        bo.pack(side="left", padx=(8, 0))

        # ---- Log
        self.logf = ttk.LabelFrame(self)
        self._track(self.logf, "frame_log")
        self.logf.pack(fill="both", expand=True, **pad)
        self.log = tk.Text(self.logf, height=10, wrap="word", font=("Consolas", 9))
        sb = ttk.Scrollbar(self.logf, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", padx=(0, 8), pady=8)
        self._log(self.t("log_started", app=self.t("app_name"), ver=APP_VERSION))

    # ---- live language switching
    def _on_lang_change(self):
        new_lang = self.lang_var.get()
        if new_lang == self.lang or new_lang not in TR:
            return
        self.lang = new_lang
        self.cfg["ui_lang"] = new_lang
        save_config(self.cfg)
        self.title(f"{self.t('app_name')}  v{APP_VERSION}")
        # Re-translate every tracked widget/menu
        for entry in self._text_refs:
            kind = entry[0]
            try:
                if kind == "widget":
                    _, widget, attr, key = entry
                    widget.configure(**{attr: self.t(key)})
                elif kind == "var":
                    _, var, key = entry
                    var.set(self.t(key))
                elif kind == "menubar":
                    _, mb, idx, key = entry
                    mb.entryconfigure(idx, label=self.t(key))
                elif kind == "submenu":
                    _, m, idx, key = entry
                    m.entryconfigure(idx, label=self.t(key))
            except Exception:
                pass
        # Update dynamic / contextual texts
        if self.st_dir is None:
            self.path_var.set(self.t("label_path_undetected"))
        self._update_wrapper_ui()
        self._refresh_status()
        # Visible marker in the log
        self._log(self.t("log_lang_switched"))

    # ---- helpers
    def _log(self, msg: str):
        stamp = time.strftime("[%H:%M:%S]")
        self.log.insert("end", f"{stamp} {msg}\n")
        self.log.see("end")

    def _log_key(self, key: str, **kwargs):
        self._log(self.t(key, **kwargs))

    def _auto_detect_if_needed(self):
        if self.st_dir is None:
            self._do_auto_detect()
        else:
            self._refresh_status()

    def _do_auto_detect(self):
        self._log_key("log_autodetect_searching")
        path = find_fh6_stringtables()
        if path:
            self.st_dir = path
            self.cfg["stringtables_dir"] = str(path)
            save_config(self.cfg)
            self.path_var.set(str(path))
            self._log_key("log_autodetect_found", path=str(path))
            self._refresh_status()
        else:
            self._log_key("log_autodetect_failed")
            messagebox.showwarning(self.t("app_name"), self.t("dlg_autodetect_failed"))

    def _do_browse(self):
        d = filedialog.askdirectory(title=self.t("dlg_pick_folder"))
        if not d:
            return
        p = Path(d)
        ok, err_key, err_kwargs = validate_stringtables_dir(p)
        if not ok:
            err_msg = self.t(err_key, **err_kwargs)
            messagebox.showerror(self.t("app_name"),
                                 self.t("dlg_warn_invalid_dir", msg=err_msg))
            return
        self.st_dir = p
        self.cfg["stringtables_dir"] = str(p)
        save_config(self.cfg)
        self.path_var.set(str(p))
        self._log_key("log_path_set", path=str(p))
        self._refresh_status()

    def _update_wrapper_ui(self):
        """Frame title + description + button state reflect install type."""
        if self.st_dir is None:
            self.wrap_frame.configure(text=self.t("frame_wrapper_default"))
            self.wrap_desc_var.set(self.t("wrapper_desc_steam"))
            self.wrap_button.configure(state="normal")
            return
        if is_xbox_install(self.st_dir):
            self.wrap_frame.configure(text=self.t("frame_wrapper_xbox"))
            self.wrap_desc_var.set(self.t("wrapper_desc_xbox"))
            self.wrap_button.configure(state="disabled")
        else:
            self.wrap_frame.configure(text=self.t("frame_wrapper_steam"))
            self.wrap_desc_var.set(self.t("wrapper_desc_steam"))
            self.wrap_button.configure(state="normal")

    def _refresh_status(self):
        if self.st_dir is None:
            self.status_var.set(self.t("status_no_path"))
            return
        try:
            state = scan_state(self.st_dir)
        except Exception as e:
            self.status_var.set(self.t("status_read_error", err=str(e)))
            return
        lines: list[str] = []
        pref = read_preferred_lang()
        if pref:
            label = CODE_TO_LABEL.get(pref, pref)
            lines.append(self.t("status_ingame_lang", label=label))
        else:
            lines.append(self.t("status_ingame_lang_missing"))
        swaps = []
        for code, _ in LANGS:
            zp_state = state.get(code)
            if not zp_state:
                continue
            if zp_state.matches_code and zp_state.matches_code != code:
                bk = self.t("status_backed_up") if zp_state.backed_up else self.t("status_not_backed_up")
                swaps.append(self.t("status_zip_swapped",
                                    code=code, match=zp_state.matches_code, backup=bk))
        if swaps:
            lines.extend(swaps)
        else:
            lines.append(self.t("status_all_original"))
        self.status_var.set("\n".join(lines))
        self._update_wrapper_ui()

    def _selected_codes(self) -> tuple[str | None, str | None]:
        sub = LABEL_TO_CODE.get(self.sub_var.get())
        voice = LABEL_TO_CODE.get(self.voice_var.get())
        return sub, voice

    def _do_apply(self):
        if self.st_dir is None:
            messagebox.showwarning(self.t("app_name"), self.t("dlg_warn_set_path"))
            return
        sub, voice = self._selected_codes()
        if not sub or not voice:
            messagebox.showwarning(self.t("app_name"), self.t("dlg_warn_select_langs"))
            return
        try:
            for key, kwargs in apply_swap(self.st_dir, sub, voice):
                self._log_key(key, **kwargs)
            try:
                paths = write_preferred_lang(voice)
                for p in paths:
                    self._log_key("log_set_preferred_lang", code=voice, path=str(p))
                if len(paths) > 1:
                    self._log_key("log_set_preferred_lang_multi", n=len(paths))
                self._log_key("log_apply_done_hint")
            except Exception as e:
                self._log_key("log_set_preferred_warn", err=str(e))
            self.cfg["sub"] = sub
            self.cfg["voice"] = voice
            save_config(self.cfg)
        except Exception as e:
            self._log_key("log_error_generic", err=str(e))
            messagebox.showerror(self.t("app_name"), str(e))
        self._refresh_status()

    def _do_restore(self):
        if self.st_dir is None:
            messagebox.showwarning(self.t("app_name"), self.t("dlg_warn_set_path"))
            return
        if not messagebox.askyesno(self.t("app_name"), self.t("dlg_confirm_restore")):
            return
        try:
            for key, kwargs in restore_all(self.st_dir):
                self._log_key(key, **kwargs)
        except Exception as e:
            self._log_key("log_error_generic", err=str(e))
            messagebox.showerror(self.t("app_name"), str(e))
        self._refresh_status()

    def _do_setup_wrapper(self):
        if self.st_dir is None:
            messagebox.showwarning(self.t("app_name"), self.t("dlg_warn_set_path"))
            return
        if is_xbox_install(self.st_dir):
            messagebox.showinfo(self.t("app_name"), self.t("dlg_wrapper_xbox"))
            return
        sub, voice = self._selected_codes()
        if not sub or not voice:
            messagebox.showwarning(self.t("app_name"), self.t("dlg_warn_select_langs"))
            return
        try:
            wrapper = write_wrapper(self.st_dir, sub, voice)
        except Exception as e:
            messagebox.showerror(self.t("app_name"),
                                 self.t("dlg_wrapper_setup_failed", err=str(e)))
            return
        launch_opts = f'"{wrapper}" %command%'
        copied = copy_to_clipboard(launch_opts)
        self._log_key("log_wrapper_generated", path=str(wrapper))
        self._log_key("log_wrapper_launch_opts", opts=launch_opts)
        if copied:
            self._log_key("log_wrapper_copied")
        messagebox.showinfo(
            self.t("app_name") + self.t("dlg_wrapper_setup_title"),
            self.t("dlg_wrapper_setup_body", opts=launch_opts),
        )

    def _open_config_dir(self):
        try:
            os.startfile(str(_config_dir()))  # type: ignore[attr-defined]
        except Exception as e:
            messagebox.showerror(self.t("app_name"), str(e))


def main():
    try:
        app = App()
        app.mainloop()
    except Exception:
        # last-ditch error reporter so a packaged .exe never silently dies
        err = traceback.format_exc()
        try:
            from tkinter import messagebox as mb, Tk
            r = Tk()
            r.withdraw()
            mb.showerror("FH6 Subtitle Switcher", err)
        except Exception:
            sys.stderr.write(err)
        raise


if __name__ == "__main__":
    main()
