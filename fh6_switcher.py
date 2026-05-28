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

APP_NAME = "FH6 字幕語音切換工具"
APP_VERSION = "1.2.0"
WRAPPER_BAT_NAME = "fh6_prelaunch_wrapper.bat"
PREFERRED_LANG_FILENAME = "UserPreferredLang"


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


def validate_stringtables_dir(p: Path) -> tuple[bool, str]:
    """Sanity check: must contain CHT.zip + EN.zip + JP.zip at minimum."""
    if not p.exists() or not p.is_dir():
        return False, "資料夾不存在"
    required = ["CHT.zip", "EN.zip", "JP.zip"]
    missing = [r for r in required if not (p / r).exists()]
    if missing:
        return False, f"資料夾不像 FH6 StringTables（缺少 {', '.join(missing)}）"
    return True, "OK"


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


def apply_swap(st_dir: Path, sub_code: str, voice_code: str) -> str:
    """Copy <sub>.zip into <voice>.zip slot (so picking <voice> in-game shows <sub> text)."""
    src = st_dir / f"{sub_code}.zip"
    dst = st_dir / f"{voice_code}.zip"
    if not src.exists():
        raise FileNotFoundError(f"找不到 {src.name}")
    if not dst.exists():
        raise FileNotFoundError(f"找不到 {dst.name}")
    backup_dir = st_dir / "_backup"
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / dst.name
    actions = []
    if sub_code == voice_code:
        return "兩邊選一樣，不需要動作（這就是原版設定）。"
    # Refresh backup if it's missing OR if its content matches the current dst content
    # (i.e. game was just updated and current dst is actually the new fresh original)
    if not backup.exists():
        shutil.copy2(dst, backup)
        actions.append(f"[備份] {dst.name} → _backup/{dst.name}")
    else:
        # If current dst content == src (already applied) skip
        if sha256_file(dst) == sha256_file(src):
            return f"{dst.name} 已經是 {sub_code} 內容，不需要重複套用。"
    shutil.copy2(src, dst)
    actions.append(f"[套用] {dst.name} ← {src.name}")
    # English voice has two variants (EN + GB) — when target is EN, also do GB
    if voice_code == "EN":
        gb = st_dir / "GB.zip"
        if gb.exists():
            gb_bk = backup_dir / "GB.zip"
            if not gb_bk.exists():
                shutil.copy2(gb, gb_bk)
                actions.append(f"[備份] GB.zip → _backup/GB.zip")
            shutil.copy2(src, gb)
            actions.append(f"[套用] GB.zip ← {src.name}  (UK English 也覆蓋)")
    elif voice_code == "GB":
        en = st_dir / "EN.zip"
        if en.exists():
            en_bk = backup_dir / "EN.zip"
            if not en_bk.exists():
                shutil.copy2(en, en_bk)
                actions.append(f"[備份] EN.zip → _backup/EN.zip")
            shutil.copy2(src, en)
            actions.append(f"[套用] EN.zip ← {src.name}  (US English 也覆蓋)")
    return "\n".join(actions)


def restore_all(st_dir: Path) -> str:
    backup_dir = st_dir / "_backup"
    if not backup_dir.exists():
        return "沒有 _backup 資料夾，沒東西需要還原。"
    restored = []
    for f in sorted(backup_dir.glob("*.zip")):
        target = st_dir / f.name
        shutil.copy2(f, target)
        restored.append(f"[還原] {f.name}")
    if not restored:
        return "_backup 是空的。"
    return "\n".join(restored)


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
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("680x620")
        self.minsize(680, 620)
        # icon (works when running .exe with embedded icon too — best-effort)
        try:
            ico = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "icon.ico"
            if ico.exists():
                self.iconbitmap(str(ico))
        except Exception:
            pass

        self.cfg = load_config()
        self.st_dir: Path | None = None
        if (saved := self.cfg.get("stringtables_dir")):
            p = Path(saved)
            ok, _ = validate_stringtables_dir(p)
            if ok:
                self.st_dir = p

        self._build_ui()
        # Run initial detection in background to avoid blocking UI
        self.after(100, self._auto_detect_if_needed)

    # ---- UI construction
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # ---- Path frame
        path_frame = ttk.LabelFrame(self, text="遊戲路徑")
        path_frame.pack(fill="x", **pad)
        self.path_var = tk.StringVar(value=str(self.st_dir) if self.st_dir else "（尚未偵測）")
        self.path_label = ttk.Label(path_frame, textvariable=self.path_var, foreground="#444")
        self.path_label.pack(fill="x", padx=8, pady=6)
        btns = ttk.Frame(path_frame)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btns, text="自動偵測", command=self._do_auto_detect).pack(side="left")
        ttk.Button(btns, text="手動選擇…", command=self._do_browse).pack(side="left", padx=(8, 0))

        # ---- Selection frame
        sel = ttk.LabelFrame(self, text="語言組合")
        sel.pack(fill="x", **pad)
        grid = ttk.Frame(sel)
        grid.pack(fill="x", padx=8, pady=8)
        ttk.Label(grid, text="字幕語言").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(grid, text="語音語言").grid(row=1, column=0, sticky="w", pady=4)
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
        ttk.Button(action, text="套用", command=self._do_apply, width=14).pack(side="left")
        ttk.Button(action, text="還原全部", command=self._do_restore, width=14).pack(side="left", padx=(8, 0))
        ttk.Button(action, text="重新掃描狀態", command=self._refresh_status, width=14).pack(side="right")

        # ---- Steam wrapper frame
        wrap = ttk.LabelFrame(self, text="Steam 啟動前自動補套（強烈建議）")
        wrap.pack(fill="x", **pad)
        ttk.Label(wrap, text="勾選後產生包裝腳本並把 Steam 啟動選項複製到剪貼簿。\n"
                              "之後每次按 Steam「遊玩」會先自動套用你選的組合再啟動 FH6。",
                  foreground="#444", justify="left").pack(anchor="w", padx=8, pady=(6, 4))
        wbtn = ttk.Frame(wrap)
        wbtn.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(wbtn, text="設定 Steam 啟動補套", command=self._do_setup_wrapper, width=22).pack(side="left")
        ttk.Button(wbtn, text="開啟設定資料夾", command=self._open_config_dir, width=18).pack(side="left", padx=(8, 0))

        # ---- Log
        logf = ttk.LabelFrame(self, text="日誌")
        logf.pack(fill="both", expand=True, **pad)
        self.log = tk.Text(logf, height=10, wrap="word", font=("Consolas", 9))
        sb = ttk.Scrollbar(logf, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", padx=(0, 8), pady=8)
        self._log(f"{APP_NAME} v{APP_VERSION} 已啟動。")

    # ---- helpers
    def _log(self, msg: str):
        stamp = time.strftime("[%H:%M:%S]")
        self.log.insert("end", f"{stamp} {msg}\n")
        self.log.see("end")

    def _auto_detect_if_needed(self):
        if self.st_dir is None:
            self._do_auto_detect()
        else:
            self._refresh_status()

    def _do_auto_detect(self):
        self._log("自動偵測 Steam 安裝中…")
        path = find_fh6_stringtables()
        if path:
            self.st_dir = path
            self.cfg["stringtables_dir"] = str(path)
            save_config(self.cfg)
            self.path_var.set(str(path))
            self._log(f"偵測到：{path}")
            self._refresh_status()
        else:
            self._log("自動偵測失敗。請按「手動選擇…」指到 FH6 的 StringTables 資料夾。")
            messagebox.showwarning(
                APP_NAME,
                "找不到 Forza Horizon 6 的 StringTables 資料夾。\n\n"
                "請按「手動選擇…」指到：\n"
                r"<Steam>\steamapps\common\ForzaHorizon6\media\Stripped\StringTables"
            )

    def _do_browse(self):
        d = filedialog.askdirectory(title="選擇 FH6 的 StringTables 資料夾")
        if not d:
            return
        p = Path(d)
        ok, msg = validate_stringtables_dir(p)
        if not ok:
            messagebox.showerror(APP_NAME, f"無效的資料夾：{msg}")
            return
        self.st_dir = p
        self.cfg["stringtables_dir"] = str(p)
        save_config(self.cfg)
        self.path_var.set(str(p))
        self._log(f"已設定路徑：{p}")
        self._refresh_status()

    def _refresh_status(self):
        if self.st_dir is None:
            self.status_var.set("尚未設定路徑")
            return
        try:
            state = scan_state(self.st_dir)
        except Exception as e:
            self.status_var.set(f"無法讀取狀態：{e}")
            return
        lines: list[str] = []
        # Forza's saved language preference
        pref = read_preferred_lang()
        if pref:
            label = CODE_TO_LABEL.get(pref, pref)
            lines.append(f"遊戲內語言設定 = {label}")
        else:
            lines.append("遊戲內語言設定 = （尚未設定或檔案不存在）")
        # Which voice slots have been swapped
        swaps = []
        for code, _ in LANGS:
            zp_state = state.get(code)
            if not zp_state:
                continue
            if zp_state.matches_code and zp_state.matches_code != code:
                swaps.append(
                    f"{code}.zip 目前內容 = {zp_state.matches_code} "
                    f"({'已備份' if zp_state.backed_up else '未備份'})"
                )
        if swaps:
            lines.extend(swaps)
        else:
            lines.append("所有語言檔都是原始狀態。")
        self.status_var.set("\n".join(lines))

    def _selected_codes(self) -> tuple[str | None, str | None]:
        sub = LABEL_TO_CODE.get(self.sub_var.get())
        voice = LABEL_TO_CODE.get(self.voice_var.get())
        return sub, voice

    def _do_apply(self):
        if self.st_dir is None:
            messagebox.showwarning(APP_NAME, "請先設定遊戲路徑。")
            return
        sub, voice = self._selected_codes()
        if not sub or not voice:
            messagebox.showwarning(APP_NAME, "請選擇字幕和語音語言。")
            return
        try:
            result = apply_swap(self.st_dir, sub, voice)
            self._log(result)
            # Also overwrite Forza's saved language preference so the user doesn't
            # have to touch the in-game language menu next time they launch.
            try:
                paths = write_preferred_lang(voice)
                for p in paths:
                    self._log(f"[設定] UserPreferredLang ← {voice}   ({p})")
                if len(paths) > 1:
                    self._log(f"（同時寫入 {len(paths)} 個位置 — Steam + MS Store 沙盒）")
                self._log("進遊戲不用再調語言，會直接是這個組合。")
            except Exception as e:
                self._log(f"[警告] 無法寫入 UserPreferredLang：{e}（你還是可以手動進遊戲設定語言）")
            self.cfg["sub"] = sub
            self.cfg["voice"] = voice
            save_config(self.cfg)
        except Exception as e:
            self._log(f"[錯誤] {e}")
            messagebox.showerror(APP_NAME, str(e))
        self._refresh_status()

    def _do_restore(self):
        if self.st_dir is None:
            messagebox.showwarning(APP_NAME, "請先設定遊戲路徑。")
            return
        if not messagebox.askyesno(APP_NAME, "確定要把 _backup 裡的所有檔案還原回去嗎？"):
            return
        try:
            result = restore_all(self.st_dir)
            self._log(result)
        except Exception as e:
            self._log(f"[錯誤] {e}")
            messagebox.showerror(APP_NAME, str(e))
        self._refresh_status()

    def _do_setup_wrapper(self):
        if self.st_dir is None:
            messagebox.showwarning(APP_NAME, "請先設定遊戲路徑。")
            return
        sub, voice = self._selected_codes()
        if not sub or not voice:
            messagebox.showwarning(APP_NAME, "請先選擇字幕和語音語言。")
            return
        try:
            wrapper = write_wrapper(self.st_dir, sub, voice)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"寫入 wrapper 失敗：{e}")
            return
        launch_opts = f'"{wrapper}" %command%'
        copied = copy_to_clipboard(launch_opts)
        self._log(f"已產生 wrapper：{wrapper}")
        self._log(f"Steam 啟動選項：{launch_opts}")
        if copied:
            self._log("（已複製到剪貼簿）")
        msg = (
            "已產生啟動包裝腳本。\n\n"
            "請開啟 Steam，依下列步驟：\n\n"
            "  1. 媒體庫 → 對「Forza Horizon 6」按右鍵 → 內容\n"
            "  2. 在「一般」頁籤找到「啟動選項」\n"
            "  3. 貼上以下這行（已複製到剪貼簿）：\n\n"
            f"     {launch_opts}\n\n"
            "  4. 關閉視窗即可生效\n\n"
            "之後每次按「遊玩」會自動套用目前的字幕／語音組合。"
        )
        messagebox.showinfo(APP_NAME + " — Steam 設定", msg)

    def _open_config_dir(self):
        try:
            os.startfile(str(_config_dir()))  # type: ignore[attr-defined]
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))


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
            mb.showerror(APP_NAME, err)
        except Exception:
            sys.stderr.write(err)
        raise


if __name__ == "__main__":
    main()
