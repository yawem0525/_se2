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
    createdAt: '12:00',
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
            <button onclick="toggleSelectAll()" type="button" class="text-xs text-pink-500 hover:text-pink-600 underline font-bold">
              全選 / 取消全選
            </button>
          </div>
          <div id="memberChips" class="flex flex-wrap gap-2"></div>
        </div>

        <!-- 管理常用好友區塊（含刪除標籤與新增輸入框） -->
        <div class="pt-3 border-t border-pink-100 space-y-2">
          <div class="flex justify-between items-center">
            <label class="block text-xs font-bold text-slate-500">
              ⚙️ 管理常用名單（點擊 ✕ 可刪除）
            </label>
            <span id="friendCount" class="text-[10px] text-pink-400 font-bold">4 位好友</span>
          </div>
          
          <div id="manageChips" class="flex flex-wrap gap-1.5"></div>

          <div class="flex items-center gap-2 pt-1">
            <input id="newFriendInput" type="text" placeholder="輸入好友名字..." 
              onkeydown="if(event.key==='Enter'){event.preventDefault();addCustomFriend();}"
              class="flex-1 bg-pink-50/40 border border-pink-200 rounded-xl px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-pink-300">
            <button onclick="addCustomFriend()" type="button" 
              class="bg-pink-100 hover:bg-pink-200 text-pink-600 text-xs font-bold px-3.5 py-1.5 rounded-xl transition">
              ＋ 新增
            </button>
          </div>
        </div>

        <button onclick="addExpense()" 
          class="w-full bg-gradient-to-r from-pink-400 to-rose-400 hover:from-pink-500 hover:to-rose-500 text-white font-bold py-2.5 rounded-2xl shadow-sm hover:shadow active:scale-[0.99] transition">
          加入小帳本 🍰
        </button>
      </div>
    </section>

    <!-- 歷史紀錄列表 -->
    <section class="space-y-3">
      <h3 class="font-bold text-pink-600 text-sm px-1 flex items-center gap-1">
        <span>📜</span> 消費紀錄明細
      </h3>
      <div id="expenseList" class="space-y-2.5"></div>
    </section>

  </div>

  <script>
    var friends = JSON.parse(localStorage.getItem('my_friends') || '["小雅", "小雯", "阿明", "小林"]');
    var selectedPayer = friends[0] || '';
    var selectedMembers = new Set(friends);
    var expenses = [];

    function saveFriends() {
      localStorage.setItem('my_friends', JSON.stringify(friends));
    }

    function renderChips() {
      var payerContainer = document.getElementById('payerChips');
      var memberContainer = document.getElementById('memberChips');
      var manageContainer = document.getElementById('manageChips');
      var countEl = document.getElementById('friendCount');

      countEl.textContent = friends.length + ' 位好友';

      if (friends.length === 0) {
        payerContainer.innerHTML = '<span class="text-xs text-slate-400">名單是空的，請在下方新增好友喔！🐰</span>';
        memberContainer.innerHTML = '<span class="text-xs text-slate-400">名單是空的～</span>';
        manageContainer.innerHTML = '<span class="text-xs text-slate-400">目前沒有常用好友</span>';
        return;
      }

      payerContainer.innerHTML = friends.map(function(f) {
        var isSelected = (selectedPayer === f);
        var btnClass = isSelected 
          ? 'bg-rose-500 text-white ring-2 ring-rose-300 scale-105' 
          : 'bg-white border border-pink-200 text-slate-600 hover:bg-pink-50';
        var icon = isSelected ? '👑 ' : '⚪ ';
        return '<button type="button" onclick="selectPayer(\'' + f + '\')" class="px-3.5 py-1.5 rounded-full text-xs font-bold transition flex items-center gap-1.5 shadow-sm ' + btnClass + '"><span>' + icon + '</span>' + f + '</button>';
      }).join('');

      memberContainer.innerHTML = friends.map(function(f) {
        var isChecked = selectedMembers.has(f);
        var btnClass = isChecked 
          ? 'bg-pink-500 text-white ring-2 ring-pink-300' 
          : 'bg-slate-100 text-slate-400 hover:bg-slate-200';
        var icon = isChecked ? '✓ ' : '+ ';
        return '<button type="button" onclick="toggleMember(\'' + f + '\')" class="px-
