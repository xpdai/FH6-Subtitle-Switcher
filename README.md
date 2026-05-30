# FH6 Subtitle Switcher 🌐

> **Forza Horizon 6 Subtitle / Voice Language Mix-and-Match Tool**
> **《極限競速：地平線 6》字幕與語音語言自由搭配工具**

[![Language](https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()
[![GUI](https://img.shields.io/badge/GUI-Tkinter-orange.svg)]()
[![Game Version](https://img.shields.io/badge/Game-Steam%20%7C%20MS%20Store-1b2838.svg)]()
[![UI Language](https://img.shields.io/badge/UI-Chinese%20%7C%20English-success.svg)]()

<p align="center">
  <img src="docs/screenshot_gui_zh.png" alt="Chinese GUI" width="49%"/>
  <img src="docs/screenshot_gui_en.png" alt="English GUI" width="49%"/>
</p>

> ✅ **平台支援 / Platform Support**
> 已驗證支援 **Steam 版**和 **Microsoft Store / Xbox PC App 版**（MS Store 需手動指定路徑，且使用前要先安裝想用的語言包；詳見[平台相容性](#-平台相容性--platform-compatibility)章節）。Xbox 主機版無法支援。
> Verified for **Steam** and **Microsoft Store / Xbox PC App** (MS Store users need to point the path manually and pre-install desired language packs — see [Platform Compatibility](#-平台相容性--platform-compatibility) for details). Xbox console not supported.

---

## 🌟 核心特色 / Key Features

### 🇹🇼 中文說明

1. **24 × 24 語言任意組合**：把 FH6 的 24 種介面／字幕語言和 24 種語音語言完全解耦，可做出例如「中文字幕 + 日文語音」「中文字幕 + 英文語音」這類官方沒給的搭配。
2. **工具本身雙語介面**：選單列「語言 / Language」可即時切換繁體中文 / English，啟動時依系統語言自動選擇，選擇會被記住。
3. **進遊戲完全不用調**：套用同時把 Forza 的 `UserPreferredLang` 設定檔改成你選的語音代碼，下次直接開遊戲就是你要的組合，**完全不用進設定選語言**。
3. **自動偵測 Steam 路徑**：讀 Steam 登錄檔與 `libraryfolders.vdf`，跨硬碟也能自動找到 FH6 的 `StringTables` 資料夾，找不到才會請使用者手動指定。
4. **SHA-256 狀態識別**：用內容雜湊比對告訴你「目前 JP.zip 內容其實是 CHT」、哪些檔已備份、哪些還是原版，狀態一目了然不會搞混。
5. **自動備份 / 一鍵還原**：第一次套用時把原檔備份到 `StringTables/_backup/`，按「還原全部」即可整批回原樣，Steam 完整性驗證也是後路。
6. **Steam 啟動補套 (Launch Wrapper)**：產生包裝腳本並把要貼到 Steam 啟動選項的字串複製到剪貼簿，遊戲每次更新後第一次啟動會自動補套，**省去手動再開工具的麻煩**。
7. **純檔案複製，不碰程序記憶體**：不對遊戲 process 做任何 `ReadProcessMemory` / `WriteProcessMemory`，不掛 hook，不改 DLL，理論上不會觸發 EAC 等反作弊機制。

### 🇬🇧 English Description

1. **24 × 24 Language Combinations**: Fully decouples FH6's 24 UI/subtitle languages from its 24 voice languages, enabling unofficial combos like "Chinese subs + Japanese voice" or "Chinese subs + English voice".
2. **Bilingual GUI (Traditional Chinese / English)**: Pick between the two from the *Language* menu at any time — switches live, with no restart. Defaults to your OS locale on first launch, and the choice is remembered.
3. **Zero In-Game Adjustment Required**: When applying a combo, the tool also rewrites Forza's `UserPreferredLang` preference file so the chosen language is auto-selected on next launch — **no in-game language menu fiddling needed**.
3. **Automatic Steam Path Detection**: Reads the Steam registry key and `libraryfolders.vdf` to locate the FH6 `StringTables` folder across all library drives; falls back to a folder picker only when detection fails.
4. **SHA-256 State Awareness**: Hash-compares every language zip against known originals and tells you exactly what each slot currently contains (e.g. "JP.zip currently holds CHT content"), so you always know the real state.
5. **Auto Backup / One-Click Restore**: Original zips are copied to `StringTables/_backup/` on first apply; one button restores everything. Steam's Verify Integrity is always available as a final fallback.
6. **Steam Launch Wrapper**: Generates a `.bat` wrapper and copies the matching Steam launch-options string to your clipboard. After every Forza update the wrapper auto-reapplies your combo, so **you never have to open the tool again** for repeat use.
7. **Pure File-Copy Tool, No Memory Hooks**: Performs zero `ReadProcessMemory` / `WriteProcessMemory` calls, no DLL injection, no hooks — should not trigger anti-cheat systems like EAC.

---

## 📂 專案架構 / Folder Layout

```text
FH6-Subtitle-Switcher/
├── fh6_switcher.py    # 主程式 (Tkinter GUI + 核心邏輯) / Main app
├── make_icon.py       # Icon 生成腳本 / Icon generator
├── icon.ico           # 程式 Icon (multi-size ICO) / App icon
├── build.bat          # PyInstaller 打包腳本 / Build script
├── README.md          # 本說明檔 / This file
└── LICENSE            # MIT 授權 / MIT License
```

---

## 🛠️ 安裝與使用 / Installation & Usage

### 🟢 方法 A：直接下載 EXE 用（推薦給一般使用者）

1. 到 [Releases](https://github.com/xpdai/FH6-Subtitle-Switcher/releases) 下載最新版的 `FH6_Subtitle_Switcher.exe`
2. 雙擊執行，**不需要裝 Python**
3. 工具會自動偵測 Steam 安裝的 FH6 位置

> 🛡️ **第一次執行 SmartScreen 會擋下來，這正常**
> 出現「Windows 已保護你的電腦」藍色視窗時：點「**更多資訊**」→「**仍要執行**」即可。
> 這不是病毒，是因為這個 EXE 沒有花錢買 code signing 憑證、且下載人數還不夠多，Windows 預設會擋下未知來源的 EXE。詳見 FAQ。
>
> First-run SmartScreen warning is normal: click **More info** → **Run anyway**. The EXE is unsigned and lacks download reputation yet — Windows blocks unknown EXEs by default. See FAQ for details.

### 🔵 方法 B：從原始碼執行 / Run from source

需要 **Python 3.10+**：

```bash
git clone https://github.com/xpdai/FH6-Subtitle-Switcher.git
cd FH6-Subtitle-Switcher
python fh6_switcher.py
```

### 🟣 方法 C：自己打包 EXE / Build your own EXE

```bash
pip install pyinstaller pillow
build.bat
```

成品出在 `dist\FH6_Subtitle_Switcher.exe`。

---

## 🚀 使用教學 / Step-by-Step Tutorial

### 第一步：偵測 / 設定遊戲路徑

開啟 `FH6_Subtitle_Switcher.exe`，工具會自動掃描 Steam 安裝的 FH6 位置。
找到就會自動填到「遊戲路徑」欄。找不到（例如非 Steam 版）按「**手動選擇…**」指到：

```
<你的 Steam 安裝路徑>\steamapps\common\ForzaHorizon6\media\Stripped\StringTables
```

### 第二步：選擇你想要的組合

- **字幕語言**：你希望介面、字幕顯示什麼語言（例如「繁體中文 (CHT)」）
- **語音語言**：你希望聽到哪一國的語音（例如「日本語 (JP)」）

兩個下拉選單裡都列出 FH6 全部 24 種語言。

### 第三步：套用

按「**套用**」。日誌會顯示類似：

```
[套用] JP.zip ← CHT.zip
[設定] UserPreferredLang ← JP
進遊戲不用再調語言，會直接是這個組合。
```

### 第四步：開遊戲

**完全關閉**遊戲（不只是回主選單）後，直接從 Steam 啟動 FH6。

✅ **你會看到中文字幕**（因為 JP.zip 的內容已被換成 CHT）
✅ **你會聽到日文語音**（因為遊戲讀「日本語」設定，載入日文語音檔）
✅ **遊戲內語言已經是「日本語」**（因為 `UserPreferredLang` 已被同步寫成 `JP`）

### 第五步（強烈建議，**僅 Steam 版**）：設定 Steam 啟動補套

> ⚠️ **此功能僅適用於 Steam 版**。MS Store / Xbox PC App 用 UWP 啟動，Xbox App 沒有「啟動選項」欄位可以掛 wrapper。MS Store 玩家請看下面的說明。

Forza 每次更新都會把 `StringTables` 重新解壓縮，把你套用的字幕內容覆蓋掉。
Steam 玩家為了避免每次更新後都得手動再開工具一次，按「**設定 Steam 啟動補套**」：

1. 工具會產生包裝 `.bat` 並把 Steam 啟動選項字串複製到剪貼簿
2. Steam → 對 Forza Horizon 6 按右鍵 → **內容** → **一般** → **啟動選項**
3. 貼上剛複製的字串（類似 `"C:\Users\你\AppData\Roaming\FH6SubtitleSwitcher\fh6_prelaunch_wrapper.bat" %command%`）
4. 關閉視窗（即自動儲存）

之後按 Steam 「**遊玩**」會：先自動套用你選的組合 → 再啟動 FH6。
無論遊戲怎麼更新都不用再開工具。

**MS Store / Xbox PC App 玩家**：v1.2.1 起工具會自動偵測安裝類型，看到 Xbox 安裝會把這個按鈕停用。目前 MS Store 沒有等效的自動套用機制，Forza 更新後請重新打開本工具按一次「套用」即可。（如果之後社群想到方法 — 例如用 Windows 排程或自製桌面捷徑包一層 — 歡迎開 Issue 討論。）

### 想還原原版？

按「**還原全部**」，工具會把 `_backup/` 內所有檔案還原回去。
保險的最後一招永遠是：Steam → FH6 → 內容 → 已安裝檔案 → **驗證遊戲檔案完整性**。

---

## 🔬 技術原理 / How It Works

FH6 把所有語言的介面／字幕文字分別存在 `StringTables/XX.zip`（XX 是兩三個字母的語言代碼）。
遊戲依「**目前語言設定**」決定載入哪個 zip：

- 設定為 `日本語` → 載入 `JP.zip`
- 設定為 `繁體中文` → 載入 `CHT.zip`

語音檔則是分離的、依語言設定載入對應的 Audio 檔案。

### 字幕切換（這個工具做的事）

把「字幕語言」zip 的內容**複製覆蓋**到「語音語言」zip 上：

```
CHT.zip 內容  →  覆蓋  →  JP.zip
```

之後遊戲設定為「日本語」時：
- 介面／字幕來自 JP.zip（內容已是 CHT）→ 中文字幕 ✓
- 語音來自 Japanese Audio → 日文語音 ✓

### 語言自動設定

FH6 把使用者選的語言存在純文字檔：

```
%LOCALAPPDATA%\ForzaHorizon6\UserPreferredLang
```

內容就是 2-3 byte 的語言代碼（例如 `JP` 或 `CHT`）。
工具把這個檔覆寫成你選的語音代碼，遊戲啟動時就會自動載入對應的語言設定。

---

## 🎮 平台相容性 / Platform Compatibility

| 平台 / Platform | 支援狀況 / Status |
|---|---|
| 🟢 **Steam (PC)** | ✅ 完整支援 / Full support |
| 🟢 **Microsoft Store / Xbox PC App** | ✅ 已驗證支援（需手動指定路徑＋預先安裝語言包）/ Verified (manual path + pre-install language packs) |
| 🔴 **Xbox 主機 (Series X/S, One)** | ❌ 不可能支援 / Impossible (closed system) |

### Microsoft Store / Xbox PC App 使用說明

MS Store 版玩家實測可用，但有幾點與 Steam 版不同，請依下面流程操作（感謝社群回報）：

1. **先在 Xbox App 安裝你想要的語言包**
   例如想要「中字 + 日語音」，要先在 Xbox App 把 FH6 的繁體中文和日文語言包都安裝過一次，這樣 `StringTables` 資料夾裡才會有 `CHT.zip` 和 `JP.zip` 可換。
2. **如果之前手動改過**，先把 `StringTables` 清乾淨（刪除你修改過的檔案），然後到 Xbox App **驗證遊戲檔案完整性**重新下載到乾淨狀態
3. **打開本工具**，按「手動選擇…」指到（路徑大小寫不重要）：
   ```
   <磁碟>:\XboxGames\Forza Horizon 6\Content\media\stripped\stringtables
   ```
   （v1.2.0 之後工具會自動掃磁碟，多數情況不用手動）
4. 之後使用方式跟 Steam 版完全一樣

### Microsoft Store / Xbox PC App user guide

The MS Store build works fine; community testing confirmed it. There are a few quirks vs Steam:

1. **Pre-install each language pack via Xbox App first.**
   For e.g. "Chinese subs + Japanese voice", the FH6 Traditional Chinese and Japanese language packs must already be installed in the Xbox App — that's how the corresponding `CHT.zip` and `JP.zip` files appear in `StringTables`.
2. **If you've previously hand-modified files**, clean out `StringTables` (delete your modified files) and use the Xbox App to **Verify game files** to restore a clean baseline.
3. **Open the tool** and click "Browse..." to point to (case-insensitive):
   ```
   <drive>:\XboxGames\Forza Horizon 6\Content\media\stripped\stringtables
   ```
   (Since v1.2.0 the tool scans all drives automatically — manual selection is usually unnecessary.)
4. After that, usage is identical to the Steam version.

### 為什麼 Xbox 主機完全不行？
主機是封閉系統，無法跑外部 `.exe`、無法存取遊戲檔案系統。**沒有任何辦法**。

### Why is Xbox console impossible?
Closed system — no way to run external `.exe`, no filesystem access. **No workaround exists.**

---

## ⚠️ 已知限制 / Known Limitations

### 伺服器拉的動態文字會跟著語音語言走 / Server-fetched text follows voice language

FH6 只有**一個**語言設定 (`UserPreferredLang`) 同時控制三件事：

1. 哪個 `StringTables\XX.zip` 載入（UI／字幕）✅ 工具可以換
2. 哪個語音檔載入 ✅ 我們刻意不動（這是你想聽的語音）
3. 跟 Forza 伺服器要動態內容時的 `Accept-Language` ❌ 我們改不了

第 3 點的結果就是：**信箱、新聞、活動文字、藍圖標題等從伺服器抓回來的內容會留在語音語言**，不是字幕語言。例如你選「英字 + 德音」，遊戲內信箱還是德文。

這些動態內容存在 `%LOCALAPPDATA%\ForzaHorizon6\CmsCache\` 是加密的二進位 blob，沒辦法解碼後改回字幕語言。

要做到也只剩下：A) 逆向解 CmsCache 加密（每次更新都會壞、又貴又脆）B) MITM HTTPS 改 `Accept-Language`（保證觸發 EAC）C) 改遊戲 exe（百分百觸發 EAC）— 沒一個值得做。

如果 Playground Games 哪天加上音／文分離選項就解了。在那之前這就是固定限制。詳見 [Issue #2](https://github.com/xpdai/FH6-Subtitle-Switcher/issues/2)。

### Server-fetched text follows the voice language

FH6 only has **one** language switch (`UserPreferredLang`) that drives three things at once:

1. Which `StringTables\XX.zip` to load (UI / subtitles) — ✅ swapped by the tool
2. Which voice audio bank to load — ✅ deliberately untouched (that's the voice you wanted)
3. The `Accept-Language` sent to Forza's CMS backend — ❌ we can't influence this

That third point means **in-game mail, news, event text, blueprint titles, and other server-pushed content stay in the voice language**, not the subtitle language. E.g. "EN subs + DE voice" still shows German mail.

This content is cached locally under `%LOCALAPPDATA%\ForzaHorizon6\CmsCache\` as encrypted binary blobs, so there is no easy way to retranslate it offline.

The only paths to a real fix are: (a) reverse-engineering and re-encrypting the CMS cache (fragile across patches), (b) MITMing the game's HTTPS traffic (guaranteed to trip EAC), or (c) patching the executable (also EAC-tripping). None are reasonable for a file-copy hobby tool.

Unless / until Playground Games ships separate audio + text language settings, this is a fixed limitation. Details in [Issue #2](https://github.com/xpdai/FH6-Subtitle-Switcher/issues/2).

---

## ❓ 常見問題 / FAQ

**Q：Windows SmartScreen 跳「Windows 已保護你的電腦」怎麼辦？**
A：點「**更多資訊**」→「**仍要執行**」即可。這是 Windows 對「未簽章且下載次數還不多的 EXE」的預設保護機制 —— 不是因為這支 EXE 有問題，而是因為它還沒有「信譽分數」。
原因：本工具用 PyInstaller 打包，沒有花錢買 Authenticode 簽章憑證（個人專案 $100/年以上）；SmartScreen 對未簽章執行檔的政策是「先擋，等下載多了再放行」。
如果你不放心，可以：
- 看 [GitHub 原始碼](https://github.com/xpdai/FH6-Subtitle-Switcher)（純 Python、~600 行、自己跑也可以）
- 自己用 `build.bat` 從原始碼編譯一份
- 把 EXE 上傳到 [VirusTotal](https://www.virustotal.com/) 掃一下

**Q：殺毒軟體把 EXE 當病毒刪了？**
A：少數殺毒軟體會把 PyInstaller 打包的 EXE 誤判為 PUA（Trojan:Win32/Wacatac 等）。
請到該殺毒軟體的隔離區把 EXE 還原並加入白名單，或從原始碼自己 build。

**Q：會被 EAC / 反作弊系統封號嗎？**
A：本工具完全不對遊戲程序做記憶體讀寫、不修改執行檔，只做「複製語言檔」和「寫一個 2-byte 文字檔」。技術上不會觸發任何反作弊偵測。但所有非官方修改本質上都自負風險。

**Q：套用後遊戲沒變化？**
A：請確認三件事：① 遊戲是否完全關閉並重啟（不是只回主選單）② 工具日誌是否顯示「[套用]」與「[設定]」兩行都成功 ③ 防毒是否阻擋了檔案寫入。

**Q：Forza 更新後失效了？**
A：這是預期行為。請使用「**Steam 啟動補套**」功能，設定一次後永久解決。

**Q：英文語音為什麼會動兩個檔（EN + GB）？**
A：FH6 有 US English (`EN.zip`) 和 UK English (`GB.zip`) 兩個英文語音版本。工具會兩個都覆蓋，這樣不論你在遊戲內選哪一個英文選項都能正常顯示中文字幕。



---

## ⚖️ 開源授權與致謝 / License & Credits

本專案採用 **MIT 授權條款** 開源。
This project is licensed under the **MIT License** — see [LICENSE](LICENSE).

- **Forza Horizon 6** © Microsoft / Playground Games / Turn 10 Studios
- 本工具與 Microsoft / Playground Games / Turn 10 Studios 無任何關聯
- This tool is not affiliated with or endorsed by Microsoft, Playground Games, or Turn 10 Studios

## 💬 回報問題 / Issues & Feedback

發現 bug 或想要新功能請開 [Issue](https://github.com/xpdai/FH6-Subtitle-Switcher/issues)。
歡迎 Pull Request！
