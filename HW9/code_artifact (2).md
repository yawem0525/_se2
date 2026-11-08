# 專案成果報告：萌萌小帳本 (Cute Edge Expense Tracker)
**基於 Cloudflare Workers 與 Hono 的邊緣分帳 Web 應用**

---

## 1. 專案簡介 (Overview)

本專案為一個部署於 **Cloudflare Workers** 邊緣網路（Edge Computing）的全端 Web 應用程式。使用者可在輕快可愛的視覺化介面中，快速記錄與朋友出遊聚會的消費項目，系統會自動標註時間戳記、追蹤付款人與分攤名單，並即時以邊緣運算計算每位成員的應收付差額，化解拆帳計算的不便。

* **正式線上網址**：`https://se2.48085328m.workers.dev`
* **原始碼倉庫**：`yawem0525/_se2`（子目錄：`/HW9`）
* **架構型態**：Serverless 邊緣原生架構（SSR + RESTful API）

---

## 2. 技術堆疊 (Tech Stack)

| 層級 | 使用技術 | 說明 |
| :--- | :--- | :--- |
| **運算平台** | Cloudflare Workers | 全球分散式邊緣運算環境，具備極低冷啟動延遲與自動水平擴展能力 |
| **持久化儲存** | Cloudflare Workers KV | 分散式鍵值（Key-Value）資料庫，用於持久化儲存各筆消費紀錄 |
| **後端框架** | Hono (TypeScript) | 專為 Cloudflare Workers 設計的超輕量極速 Web 框架 |
| **前端設計** | Tailwind CSS (CDN) + HTML5 | 採粉嫩馬卡龍主題與圓角卡片風格，免打包即時載入 |
| **字體排印** | Google Fonts (Zen Maru Gothic) | 日系圓體字型，強化親和可愛的使用者體驗 |
| **CI/CD 自動化** | GitHub + Cloudflare Integration | 透過 Git commit 自動觸發雲端邊緣建置與無縫部署 |

---

## 3. 專案目錄結構 (Project Structure)

專案整合於 GitHub 倉庫的 `HW9` 子資料夾內：

```text
HW9/
├── package.json          # Node.js 專案依賴定義 (Hono, Wrangler, Types)
├── tsconfig.json         # TypeScript 編譯設定
├── wrangler.jsonc        # Cloudflare Workers 配置檔 (Worker 名稱、入口點、KV 綁定)
└── src/
    └── index.ts          # 核心程式碼：包含 SSR 前端介面與 RESTful API 端點
```

---

## 4. 系統功能與特色 (Core Features)

### 4.1. 視覺與互動體驗
* **馬卡龍粉嫩主題**：以柔和的粉紅、暖橙與卡片陰影設計，降低嚴肅金錢計算的緊張感。
* **泡泡膠囊式按鈕（Pill Chips）**：
  * **付款人選擇**：單選切換，選中時附帶皇冠圖示（👑），直觀辨識出資者。
  * **分攤成員**：多選切換，支援一鍵「全選 / 取消全選」。
* **常用名單動態管理**：
  * 支援手動輸入新朋友名字並以 `Enter` 或按鈕新增。
  * 每個好友膠囊右側附帶 `✕` 按鈕，可安全自常用名單移除。
  * 結合瀏覽器 `localStorage`，重新整理後名單自動保留。

### 4.2. 財務與邊緣計算
* **消費歷史明細**：記錄項目名稱、消費總額、墊付人、分攤對象清單與建立時間戳記。
* **即時分攤結算算法**：
  系統依據每筆紀錄的成員名單動態拆分應攤額：
  $$\text{PerPerson} = \frac{\text{Amount}}{\text{MemberCount}}$$
  並即時彙整每位成員的淨收支：
  * 應收餘額（綠色標籤 💰）
  * 應付餘額（紅色標籤 💸）
  * 已結清狀態（灰色標籤 ✨）

### 4.3. 後端 API 設計

| 請求方式 | 路徑 | 功能說明 |
| :--- | :--- | :--- |
| `GET` | `/` | 渲染並回傳前端 HTML 單一介面 (SSR) |
| `GET` | `/api/expenses` | 取得所有歷史分帳紀錄 (自 KV 或快取讀取) |
| `POST` | `/api/expenses` | 新增一筆分帳紀錄並同步寫入 KV 永久儲存 |
| `DELETE` | `/api/expenses/:id` | 刪除指定 ID 的消費紀錄並自 KV 移除 |

---

## 5. 部署與 CI/CD 流程 (Deployment Process)

本專案採用 **GitOps** 自動化流程部署：

1. **GitHub 倉庫同步**：在本地或 GitHub 網頁端編輯 `HW9` 資料夾下的原始碼。
2. **Cloudflare 連動設定**：
   * 將 Cloudflare Workers & Pages 綁定 GitHub 倉庫。
   * 設定 **Root directory** 為 `/HW9`，確保建置環境正確定位套件路徑。
3. **KV 命名空間建立**：
   * 建立名稱為 `NOTES_STORE` 的 KV 空間。
   * 於 `wrangler.jsonc` 綁定 `NOTES_KV` 及其對應的 Namespace ID。
4. **自動化建置上線**：每次執行 `git commit` 時，Cloudflare 會自動執行依賴安裝與 `wrangler deploy`，將最新版本推播至全球節點。

---

## 6. 開發遭遇問題與除錯紀錄 (Troubleshooting & Lessons Learned)

在本次實作邊緣計算的過程中，曾遇過以下挑戰並逐一排除：

1. **子目錄路徑識別問題**：
   * **問題**：專案位於儲存庫的 `/HW9` 資料夾，初次部署時 Cloudflare 在根目錄找不到設定檔導致建置失敗。
   * **解決**：在 Cloudflare 後台的 `Builds & deployments` ➔ `Build configuration` 將 **Root directory** 修正為 `/HW9`。

2. **KV Namespace ID 格式語法錯誤 (Code: 10042)**：
   * **問題**：在 `wrangler.jsonc` 設定 KV 時，誤將佔位符角括號包含進去（例如 `"<93e7...9b>"`），導致 API 驗證判定 ID 無效中斷部署。
   * **解決**：移除 `< >` 符號，改為標準純字串 ID 格式：`"id": "93e7565e21244dfbb53a0a570a7c8e9b"`。

3. **伺服器字串樣板閉合錯誤 (Unterminated String Literal)**：
   * **問題**：使用 Server-Side Template String 產生前端客戶端程式碼時，因內部反引號與雙引號嵌套，以及複製時末端文字被截斷，造成 esbuild 打包報錯。
   * **解決**：重構客戶端 JavaScript 結構，全面採用標準字串相加，並加入健壯的 `try...catch` 容錯與記憶體 Fallback 機制，確保即使 KV 短暫連線波動，應用程式依然穩定運作。

---

## 7. 結論與未來展望 (Conclusion & Future Work)

本專案成功運用現代 Serverless 技術打造出輕量、快速且具備持久化儲存的社交分帳應用程式。相較於傳統 VPS 託管，具備零伺服器維護負擔、極低營運成本與高可用性的優勢。

**後續可擴充方向**：
* 串接 LINE Notify 或 Telegram Bot，提供即時推播結算明細給好友。
* 整合行動支付 QR Code（如台灣 Pay、街口或 LINE Pay 轉帳連結），提升收款便利性。