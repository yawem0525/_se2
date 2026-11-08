const { test, expect } = require('@playwright/test');

test.describe('E2E: 任務管理系統端到端測試', () => {

  test('使用者能夠進入首頁、新增任務並顯示在清單中', async ({ page }) => {
    // 1. 造訪頁面
    await page.goto('/');
    await expect(page.locator('h2')).toHaveText('任務管理儀表板');

    // 2. 在輸入框填入新任務
    const input = page.locator('[data-testid="task-input"]');
    await input.fill('Playwright 自動化測試項目');

    // 3. 點擊新增按鈕
    await page.locator('[data-testid="add-btn"]').click();

    // 4. 驗證清單中出現該任務項目
    const taskItem = page.locator('[data-testid="task-item"]');
    await expect(taskItem).toContainText('Playwright 自動化測試項目');
  });

  test('輸入空白標題時應顯示驗證錯誤訊息', async ({ page }) => {
    await page.goto('/');

    // 留空直接點擊新增
    await page.locator('[data-testid="add-btn"]').click();

    // 驗證錯誤訊息出現
    const errorMsg = page.locator('[data-testid="error-msg"]');
    await expect(errorMsg).toHaveText('標題不能為空');
  });

  test('使用者可成功刪除已存在的任務', async ({ page }) => {
    await page.goto('/');

    // 新增待刪除項目
    await page.locator('[data-testid="task-input"]').fill('即將被刪除的任務');
    await page.locator('[data-testid="add-btn"]').click();

    const taskItem = page.locator('[data-testid="task-item"]', { hasText: '即將被刪除的任務' });
    await expect(taskItem).toBeVisible();

    // 點擊該項目的刪除按鈕
    await taskItem.locator('[data-testid="delete-btn"]').click();

    // 驗證項目從 DOM 消失
    await expect(taskItem).not.toBeVisible();
  });

});
