# Git & GitHub 協作流程教學 (Forking Workflow)

本專案示範了如何透過 Git 與 GitHub 進行跨專案的協作。這裡使用的主要流程為 **Forking Workflow（分叉工作流）**，這也是 GitHub 上開源專案最標準且最常見的協作方式。

在 Forking Workflow 中，開發者沒有母專案的直接推播 (Push) 權限。因此必須先將專案「Fork（複製）」到自己的帳號下成為「子專案」，在子專案進行開發與「分支 (Branch)」，接著再透過「拉取請求 (Pull Request)」將程式碼貢獻回「母專案」，並由母專案的維護者進行「合併 (Merge)」。

---

## 專案關聯說明

*   **母專案 (Upstream)**：[se-test-examples/git-examples](https://github.com/se-test-examples/git-examples/commits/main/)
*   **子專案 (Origin/Fork)**：[ccckmit/git-examples](https://github.com/ccckmit/git-examples/commits/main/)

以下是創造出「分支、合併、Fork、Pull Request」的具體指令與操作步驟：

---

### 1. Fork (建立分叉 / 子專案)
**目標**：從母專案複製一份獨立的子專案到自己的 GitHub 帳號下。

**操作方式（GitHub 介面）**：
1. 前往母專案頁面：`https://github.com/se-test-examples/git-examples`
2. 點擊頁面右上角的 **「Fork」** 按鈕。
3. 依照指示，在自己的帳號 (`ccckmit`) 底下建立新的 Repository。
4. 完成後，就會產生您的子專案：`https://github.com/ccckmit/git-examples`。

---

### 2. 分支 (Branch)
**目標**：在不影響 `main` 主線的情況下，建立一個獨立的開發環境（例如母專案中出現的 `developGitBranch`）。

**操作方式（Git 終端機指令）**：
首先，將剛剛 Fork 的子專案 clone 到本地端電腦：
```bash
# 1. 複製子專案到本地端
git clone [https://github.com/ccckmit/git-examples.git](https://github.com/ccckmit/git-examples.git)
cd git-examples

# 2. 建立並切換到新的分支 developGitBranch
git checkout -b developGitBranch

# 3. 在這個分支上進行修改並提交 (Commit)
git add .
git commit -m "Add new features in developGitBranch"

# 4. 將本地端的新分支推播到 GitHub 上的子專案
git push origin developGitBranch
```
問AI:https://share.gemini.google/iQGokMpquGLA
