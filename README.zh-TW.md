# agent-guardrails

[English](README.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · **繁體中文** · [한국어](README.ko.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Bahasa Melayu](README.ms.md) · [ไทย](README.th.md)

Claude Code 的**防錯掛勾集**。讓重複犯的錯**由機器擋下**，而不是再寫一條
「下次注意」的筆記。

> 靠機制擔保，別靠人的注意力。

## 為什麼做這個

實測了 30 個工作階段、887 則使用者訊息：使用者糾正我的地方共 **44 處**，收斂成 6 類。
而**這 6 類全都只靠「寫在筆記裡的文字」在防**。筆記早就寫好了，錯還是照犯。

| 實測次數 | 模式 | 目前的防線 |
| --- | --- | --- |
| 12 | 文字與呈現的品質 | `reply_check.py` 偵測 |
| 9 | 太早宣稱做完了 | `reply_check.py` 偵測 |
| 9 | 交付沒人要的東西 | `outward_action_guard.py` **拒絕** |
| 7 | 沒試就說「做不到」 | `reply_check.py` 偵測 |
| 4 | 漏讀指令 | 留在基準檔（未達門檻） |
| 3 | 弄錯目標儲存庫／環境 | 留在基準檔（未達門檻） |

採用的界線是：**出現 ≥5 次 = 正在反覆犯 = 筆記治不好**——那條筆記已經失效過一次了。
4 次以下仍留作文字。若全都做成攔截，警告會飽和到沒人看。

## 內容

### 掛勾（註冊在 `~/.claude/settings.json`，所有目錄都生效）

| 檔案 | 事件 | 做什麼 |
| --- | --- | --- |
| `reply_check.py` | Stop | 偵測缺少狀態區塊、沒有證據的「已完成」、沒試就說的「做不到」、機器寫作的句式痕跡（`X, not Y` 對仗、數數式開頭、分裂句開頭、清嗓子式前言），以及聊天機器人的口頭禪。**只告警**——在 Stop 硬擋有無窮迴圈的風險 |
| `outward_action_guard.py` | PreToolUse(Bash) | **拒絕**難以復原的對外動作（PR／push／建立儲存庫／發行／gist）。同時拒絕 `<check> \| tail; echo $?`——那讀到的是 `tail` 的結束碼，不是檢查的 |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | 編輯檢查程式、掛勾、設定或記憶時要求確認。防止**被審的一方去改評分者**，而不是改產出 |
| `daily-retro-reminder.sh` | PostToolUse | 寫完每日報告時提醒做回顧 |

### 技能

`skills/daily-retro/` — 以「寫每日報告」為觸發點的改善迴圈。把每個錯誤盡量往下推：

> 記憶 → 文件 → 指令稿 → 前置檢查 → 測試 → 權限

### 指令稿

| 檔案 | 用途 |
| --- | --- |
| `mistake-frequency.py` | 從全部歷史工作階段裡**數**各類糾正出現過幾次，讓「這個我已經改好了」變成實測而非印象 |
| `verify-gates.py` | **替攔截器本身做自我測試。**餵該觸發的輸入與不該觸發的輸入各一遍 |

### 參考資料

`reference/anti-self-deception/` — 另一支團隊成熟的防錯機制（24 條規則、15 支指令稿、
29 項常駐檢查），經許可、去識別化後收錄。詳見該目錄的 `ATTRIBUTION.md`。

## 最有用的兩個

**`guard_the_guards.py`** — 其他所有防線看的都是「產出」，沒有一層擋住
**被審的人去改評分者**。我剛建好三個掛勾和一套自我測試，而它們全都能被我隨手改掉。

**`verify-gates.py`** — 陳舊偵測我寫了三個版本，三次都是 18 條全過。
若不去讀那些數字，我會連著三次回報「一切健康」。
**從沒失敗過的檢查，可能什麼都沒在守。**

## 安裝

複製下來後執行 `bash install.sh`。會複製到 `~/.claude/hooks/` 與 `~/.claude/skills/`，
並把掛勾註冊進 `~/.claude/settings.json`——只新增，保留既有設定。

`CLAUDE.example.md` 要先讀過，依自己的環境調整（記憶的絕對路徑、每日報告存放位置），
再放到 `~/.claude/CLAUDE.md`。

裝完一定要跑自我測試：

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

全新環境 21/21，已設定環境 26/26。

## 注意

- 掛勾放在 `~/.claude/` 底下，所以**在任何目錄都生效**。記憶則不然——它依 Claude
  啟動的目錄分區，所以跨專案的原則要寫進每次都會讀的 `~/.claude/CLAUDE.md`。
- `outward_action_guard.py` 會擋 push。確實要推的加上 `CLAUDE_OUTWARD_OK=1`；
  嫌吵就從 `GUARDED` 裡刪掉項目。
- `reply_check.py` 用的是正規表示式，會誤判。誤判時**把樣式收窄，不要刪掉這項檢查**。
- 掛勾的執行期訊息目前是日文。那部分是給 agent 讀的，不影響行為，歡迎翻譯。

## 授權

MIT
