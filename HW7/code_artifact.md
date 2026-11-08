# 測試執行指引 (Testing Execution Guide)

本文件整理專案中三個測試層級（單元測試、系統 API 測試、端到端 E2E 測試）的執行指令、常用參數及除錯技巧。

---

## 目錄
- [環境需求](#環境需求)
- [1. 單元測試 (Unit Tests)](#1-單元測試-unit-tests)
- [2. 系統測試 (System / Web API Tests)](#2-系統測試-system--web-api-tests)
- [3. 端到端測試 (E2E Tests)](#3-端到端測試-e2e-tests)
- [4. 一鍵自動化配置 (整合 webServer)](#4-一鍵自動化配置-整合-webserver)
- [5. 常用指令快速速查表](#5-常用指令快速速查表)

---

## 環境需求

- **Rust 工具鏈**：`cargo`, `rustc` (建議 1.75+)
- **Node.js**：`node` (v18+), `npm`
- **瀏覽器驅動**：Playwright 專用 Chromium

---

## 1. 單元測試 (Unit Tests)

針對後端 Rust 的領域模型驗證與純邏輯函式進行測試（位於 `src/lib.rs` 的 `unit_tests` 模組）。此層級不依賴網路與外部資源。

### 基本執行
```bash
# 僅執行 lib.rs 中的單元測試模組
cargo test --lib unit_tests
```

### 指定測試案例
```bash
# 僅執行特定的單元測試函式
cargo test test_validate_task_title_valid
```

### 檢視除錯輸出
```bash
# 顯示程式碼中 println! 或 log 的標準輸出內容
cargo test --lib unit_tests -- --nocapture
```

---

## 2. 系統測試 (System / Web API Tests)

針對 HTTP 路由、狀態碼（Status Codes）、JSON 序列化與記憶體狀態進行測試（位於 `tests/api_test.rs`）。

### 基本執行
```bash
# 執行所有 API 整合測試
cargo test --test api_test
```

### 指定 API 測試案例
```bash
# 執行特定的 API 測試
cargo test --test api_test test_api_create_and_get_tasks
```

### 避免共用狀態競爭 (單執行緒模式)
```bash
# 強制以單執行緒依序執行，防止共用記憶體狀態衝突
cargo test --test api_test -- --test-threads=1
```

### 執行全專案 Rust 測試 (單元測試 + 系統測試)
```bash
cargo test
```

---

## 3. 端到端測試 (E2E Tests)

使用 Playwright 驅動無頭瀏覽器（Headless Chromium），驗證真實瀏覽器環境下的 DOM 操作、事件綁定與非同步 API 串接。

### 前置準備（首次執行）
```bash
# 1. 安裝 JavaScript 測試依賴
npm install

# 2. 下載 Playwright 專用 Chromium 瀏覽器核心
npx playwright install chromium
```

### 手動啟動伺服器並測試
```bash
# 終端機 A：編譯並啟動後端伺服器 (Port 3000)
cargo run

# 終端機 B：執行 E2E 測試
npx playwright test
```

### Playwright 進階除錯指令
```bash
# 1. 無頭模式執行 (預設，適用於 CI/CD)
npx playwright test

# 2. 開啟實體瀏覽器視窗 (視覺化觀察測試動作)
npx playwright test --headed

# 3. 開啟互動式 UI 介面 (具備時間軸快照與 DOM 檢查工具)
npx playwright test --ui

# 4. 單步除錯模式 (Playwright Inspector，可逐行中斷除錯)
npx playwright test --debug

# 5. 檢視測試產生的 HTML 報告
npx playwright show-report
```

---

## 4. 一鍵自動化配置 (整合 webServer)

若希望在執行 `npx playwright test` 時自動啟動 Rust 伺服器並在測試結束後關閉，可在 `playwright.config.js` 加入 `webServer` 設定：

```javascript
// playwright.config.js
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    viewport: { width: 1280, height: 720 },
  },
  webServer: {
    command: 'cargo run',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000, // Rust 初次編譯時間較長，設定 120 秒超時緩衝
  },
});
```

設定完成後，僅需一行指令即可完成編譯、啟動服務與端到端測試：
```bash
npx playwright test
```

---

## 5. 常用指令快速速查表

| 測試類型 | 執行指令 | 說明 |
| :--- | :--- | :--- |
| **單元測試** | `cargo test --lib unit_tests` | 驗證 Rust 核心業務邏輯 |
| **單元測試 (含輸出)** | `cargo test --lib unit_tests -- --nocapture` | 印出 `println!` 除錯內容 |
| **系統 API 測試** | `cargo test --test api_test` | 驗證 Web API 路由與 HTTP 狀態 |
| **全 Rust 測試** | `cargo test` | 執行全部單元測試與整合測試 |
| **E2E 測試 (Headless)** | `npx playwright test` | 於背景無頭模式執行瀏覽器測試 |
| **E2E 測試 (Headed)** | `npx playwright test --headed` | 顯示瀏覽器畫面進行測試 |
| **E2E 互動介面** | `npx playwright test --ui` | 開啟 UI 介面進行時間軸除錯 |
| **檢視 E2E 報告** | `npx playwright show-report` | 開啟 HTML 測試報表 |