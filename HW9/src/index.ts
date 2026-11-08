import { Hono } from 'hono';

type Bindings = {
  NOTES_KV?: KVNamespace;
};

interface Expense {
  id: string;
  title: string;
  amount: number;
  payer: string;
  members: string[];
  createdAt: string;
}

let fallbackExpenses: Expense[] = [
  {
    id: 'demo-1',
    title: '🧋 珍珠奶茶下午茶',
    amount: 180,
    payer: '小雅',
    members: ['小雅', '小雯', '阿明'],
    createdAt: new Date().toLocaleTimeString('zh-TW', { hour12: false, hour: '2-digit', minute: '2-digit' }),
  },
];

const app = new Hono<{ Bindings: Bindings }>();

// API: 取得所有分帳紀錄
app.get('/api/expenses', async (c) => {
  try {
    if (c.env?.NOTES_KV) {
      const data = await c.env.NOTES_KV.get('split_expenses_data');
      if (data) return c.json(JSON.parse(data));
    }
  } catch (err) {
    console.error('KV 讀取錯誤：', err);
  }
  return c.json(fallbackExpenses);
});

// API: 新增分帳紀錄
app.post('/api/expenses', async (c) => {
  const body = await c.req.json<{
    title: string;
    amount: number;
    payer: string;
    members: string[];
  }>();

  if (!body.title || !body.amount || !body.payer || !body.members || body.members.length === 0) {
    return c.json({ error: '請完整填寫項目、金額、墊付人與分攤成員' }, 400);
  }

  const newExpense: Expense = {
    id: crypto.randomUUID(),
    title: body.title.trim(),
    amount: Number(body.amount),
    payer: body.payer.trim(),
    members: body.members,
    createdAt: new Date().toLocaleTimeString('zh-TW', { hour12: false, hour: '2-digit', minute: '2-digit' }),
  };

  try {
    if (c.env?.NOTES_KV) {
      const data = await c.env.NOTES_KV.get('split_expenses_data');
      const expenses: Expense[] = data ? JSON.parse(data) : [];
      expenses.unshift(newExpense);
      await c.env.NOTES_KV.put('split_expenses_data', JSON.stringify(expenses));
      return c.json(newExpense, 201);
    }
  } catch (err) {
    console.error('KV 寫入錯誤：', err);
  }

  fallbackExpenses.unshift(newExpense);
  return c.json(newExpense, 201);
});

// API: 刪除單筆紀錄
app.delete('/api/expenses/:id', async (c) => {
  const id = c.req.param('id');
  try {
    if (c.env?.NOTES_KV) {
      const data = await c.env.NOTES_KV.get('split_expenses_data');
      if (data) {
        let expenses: Expense[] = JSON.parse(data);
        expenses = expenses.filter((e) => e.id !== id);
        await c.env.NOTES_KV.put('split_expenses_data', JSON.stringify(expenses));
        return c.json({ success: true });
      }
    }
  } catch (err) {
    console.error('KV 刪除錯誤：', err);
  }

  fallbackExpenses = fallbackExpenses.filter((e) => e.id !== id);
  return c.json({ success: true });
});

// 前端介面
app.get('/', (c) => {
  const html = `<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🐾 萌萌小帳本 - 朋友分帳幫手</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Zen Maru Gothic', sans-serif, system-ui; }
  </style>
</head>
<body class="bg-gradient-to-br from-pink-50 via-rose-50 to-amber-50 text-slate-700 min-h-screen py-8 px-4">
  <div class="max-w-xl mx-auto space-y-6">

    <!-- 頁首 -->
    <header class="text-center space-y-2">
      <div class="inline-flex items-center justify-center w-14 h-14 bg-pink-200/80 rounded-full shadow-inner text-2xl">
        🐰
      </div>
      <h1 class="text-3xl font-extrabold text-pink-600 tracking-wide">萌萌小帳本 ✨</h1>
      <p class="text-xs text-pink-400 font-bold bg-pink-100/60 inline-block px-3 py-1 rounded-full">
        Cloudflare Edge ☁️ 支援自訂與刪除好友名單 🍓
      </p>
    </header>

    <!-- 結算概覽卡片 -->
    <section class="bg-white/80 backdrop-blur-md border border-pink-200/80 rounded-3xl p-5 shadow-sm space-y-3">
      <div class="flex justify-between items-center border-b border-pink-100 pb-2">
        <h2 class="font-bold text-pink-700 flex items-center gap-1">📊 結算試算</h2>
        <span id="totalAmount" class="text-sm font-bold text-rose-500 bg-rose-50 px-2.5 py-0.5 rounded-full">總計: \$0</span>
      </div>
      <div id="balanceList" class="grid grid-cols-2 gap-2 text-xs text-slate-600"></div>
    </section>

    <!-- 輸入表單卡片 -->
    <section class="bg-white rounded-3xl p-6 shadow-md border-2 border-pink-100 space-y-5">
      <h3 class="font-bold text-pink-600 text-sm flex items-center gap-1.5">
        <span>✏️</span> 記下一筆新消費
      </h3>

      <div class="space-y-4 text-sm">
        <!-- 項目與金額 -->
        <div class="grid grid-cols-5 gap-3">
          <div class="col-span-3">
            <label class="block text-xs font-bold text-slate-500 mb-1">消費項目</label>
            <input id="title" type="text" placeholder="例：好吃拉麵 🍜" 
              class="w-full bg-pink-50/50 border border-pink-200 rounded-2xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-pink-300">
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-bold text-slate-500 mb-1">金額 (\$)</label>
            <input id="amount" type="number" placeholder="360" 
              class="w-full bg-pink-50/50 border border-pink-200 rounded-2xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-pink-300">
          </div>
        </div>

        <!-- 誰先墊錢（單選泡泡） -->
        <div>
          <label class="block text-xs font-bold text-slate-500 mb-1.5">
            💳 誰先墊錢？<span class="text-pink-400 font-normal ml-1">（點選單一好友）</span>
          </label>
          <div id="payerChips" class="flex flex-wrap gap-2"></div>
        </div>

        <!-- 分攤成員（多選泡泡） -->
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="block text-xs font-bold text-slate-500">
              👥 分攤成員<span class="text-pink-400 font-normal ml-1">（點擊切換勾選）</span>
            </label>
            <button onclick="toggleSelectAll()" type="button" class="text-xs text-pink-500 hover:text-pink-600 underline
