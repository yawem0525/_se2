const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:3000',
    headless: true, // 使用無頭瀏覽器執行
    viewport: { width: 1280, height: 720 },
  },
});
