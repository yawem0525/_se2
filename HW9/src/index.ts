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
        Cloudflare Edge ☁️ 點選泡泡免打字 🍓
      </p>
    </header>

    <!-- 結算概覽卡片 -->
    <section class="bg-white/80 backdrop-blur-md border border-pink-200/80 rounded-3xl p-5 shadow-sm space-y-3">
      <div class="flex justify-between items-center border-b border-pink-100 pb-2">
        <h2 class="font-bold text-pink-700 flex items-center gap-1">📊 結算試算</h2>
        <span id="totalAmount" class="text-sm font-bold text-rose-500 bg-rose-50 px-2.5 py-0.5 rounded-full">總計: $0</span>
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
            <input id="title" type="text" placeholder="例：拉麵、高鐵票 🍜" 
              class="w-full bg-pink-50/50 border border-pink-200 rounded-2xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-pink-300">
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-bold text-slate-500 mb-1">金額 ($)</label>
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

        <!-- 管理常用好友按鈕 -->
        <div class="pt-2 border-t border-pink-100 flex items-center gap-2">
          <input id="newFriendInput" type="text" placeholder="新增常用好友名字..." 
            class="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-xs focus:outline-none focus:border-pink-300">
          <button onclick="addCustomFriend()" type="button" 
            class="bg-pink-100 hover:bg-pink-200 text-pink-600 text-xs font-bold px-3 py-1.5 rounded-xl transition">
            ＋ 新增好友
          </button>
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
    // 預設常用好友清單（支援 localStorage 本地記憶）
    let friends = JSON.parse(localStorage.getItem('my_friends') || '["小雅", "小雯", "阿明", "小林"]');
    let selectedPayer = friends[0] || '';
    let selectedMembers = new Set(friends);
    let expenses = [];

    function saveFriends() {
      localStorage.setItem('my_friends', JSON.stringify(friends));
    }

    // 渲染泡泡按鈕
    function renderChips() {
      const payerContainer = document.getElementById('payerChips');
      const memberContainer = document.getElementById('memberChips');

      // 1. 墊付人泡泡（單選）
      payerContainer.innerHTML = friends.map(f => {
        const isSelected = selectedPayer === f;
        return \`
          <button type="button" onclick="selectPayer('\${f}')" 
            class="px-3.5 py-1.5 rounded-full text-xs font-bold transition flex items-center gap-1.5 shadow-sm
            \${isSelected 
              ? 'bg-rose-500 text-white ring-2 ring-rose-300 scale-105' 
              : 'bg-white border border-pink-200 text-slate-600 hover:bg-pink-50'}">
            <span>\${isSelected ? '👑' : '⚪'}</span> \${f}
          </button>
        \`;
      }).join('');

      // 2. 分攤人泡泡（多選）
      memberContainer.innerHTML = friends.map(f => {
        const isChecked = selectedMembers.has(f);
        return \`
          <button type="button" onclick="toggleMember('\${f}')" 
            class="px-3.5 py-1.5 rounded-full text-xs font-bold transition flex items-center gap-1.5 shadow-sm
            \${isChecked 
              ? 'bg-pink-500 text-white ring-2 ring-pink-300' 
              : 'bg-slate-100 text-slate-400 hover:bg-slate-200'}">
            <span>\${isChecked ? '✓' : '+'}</span> \${f}
          </button>
        \`;
      }).join('');
    }

    function selectPayer(name) {
      selectedPayer = name;
      renderChips();
    }

    function toggleMember(name) {
      if (selectedMembers.has(name)) {
        selectedMembers.delete(name);
      } else {
        selectedMembers.add(name);
      }
      renderChips();
    }

    function toggleSelectAll() {
      if (selectedMembers.size === friends.length) {
        selectedMembers.clear();
      } else {
        selectedMembers = new Set(friends);
      }
      renderChips();
    }

    function addCustomFriend() {
      const input = document.getElementById('newFriendInput');
      const name = input.value.trim();
      if (!name) return;
      if (friends.includes(name)) {
        alert('這位朋友已經在清單內囉！🐰');
        return;
      }
      friends.push(name);
      selectedMembers.add(name);
      saveFriends();
      input.value = '';
      renderChips();
    }

    // 載入與計算分帳
    async function loadExpenses() {
      const res = await fetch('/api/expenses');
      expenses = await res.json();
      renderUI();
    }

    function renderUI() {
      const container = document.getElementById('expenseList');
      const totalAmountEl = document.getElementById('totalAmount');
      const balanceEl = document.getElementById('balanceList');

      let total = 0;
      const balances = {};

      expenses.forEach(item => {
        total += item.amount;
        const splitCount = item.members.length || 1;
        const perPerson = item.amount / splitCount;

        balances[item.payer] = (balances[item.payer] || 0) + item.amount;
        item.members.forEach(member => {
          balances[member] = (balances[member] || 0) - perPerson;
        });
      });

      totalAmountEl.textContent = '總計: $' + Math.round(total);

      balanceEl.innerHTML = Object.entries(balances).map(([name, bal]) => {
        const rounded = Math.round(bal);
        if (rounded > 0) {
          return \`<div class="bg-emerald-50 border border-emerald-100 p-2 rounded-xl text-emerald-700">
            <span class="font-bold">\${name}</span>：應收回 <span class="font-bold">$\${rounded}</span> 💰
          </div>\`;
        } else if (rounded < 0) {
          return \`<div class="bg-rose-50 border border-rose-100 p-2 rounded-xl text-rose-600">
            <span class="font-bold">\${name}</span>：應拿出 <span class="font-bold">$\${Math.abs(rounded)}</span> 💸
          </div>\`;
        } else {
          return \`<div class="bg-slate-50 border border-slate-100 p-2 rounded-xl text-slate-500">
            <span class="font-bold">\${name}</span>：已結清 ✨
          </div>\`;
        }
      }).join('') || '<div class="text-xs text-slate-400 py-1">目前尚無分帳資料～</div>';

      container.innerHTML = expenses.map(item => \`
        <div class="bg-white border border-pink-100 rounded-2xl p-4 shadow-sm hover:shadow transition space-y-2">
          <div class="flex justify-between items-start">
            <div>
              <h4 class="font-bold text-slate-800 text-sm">\${item.title}</h4>
              <div class="text-xs text-pink-500 mt-0.5">
                墊付人：<span class="font-bold bg-pink-50 px-2 py-0.5 rounded-md">\${item.payer}</span>
              </div>
            </div>
            <div class="text-right">
              <span class="text-base font-extrabold text-rose-500">$\${item.amount}</span>
              <div class="text-[10px] text-slate-400 mt-0.5">\${item.createdAt}</div>
            </div>
          </div>
          
          <div class="flex justify-between items-center pt-2 border-t border-slate-50 text-[11px] text-slate-500">
            <div class="truncate max-w-[280px]">
              分攤人：\${item.members.join('、')} (每人約 $\${Math.round(item.amount / item.members.length)})
            </div>
            <button onclick="deleteExpense('\${item.id}')" 
              class="text-slate-300 hover:text-rose-400 transition p-1 text-xs">
              ✕
            </button>
          </div>
        </div>
      \`).join('');
    }

    async function addExpense() {
      const title = document.getElementById('title').value;
      const amount = document.getElementById('amount').value;
      const payer = selectedPayer;
      const members = Array.from(selectedMembers);

      if (!title || !amount) {
        alert('請填寫消費項目和金額喔！🐰');
        return;
      }
      if (!payer) {
        alert('請點選一位墊錢的好友 👑');
        return;
      }
      if (members.length === 0) {
        alert('至少要勾選一位分攤成員喔！👥');
        return;
      }

      const res = await fetch('/api/expenses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, amount: Number(amount), payer, members })
      });

      if (res.ok) {
        document.getElementById('title').value = '';
        document.getElementById('amount').value = '';
        loadExpenses();
      }
    }

    async function deleteExpense(id) {
      if (!confirm('確定要刪除這筆紀錄嗎？🐾')) return;
      const res = await fetch('/api/expenses/' + id, { method: 'DELETE' });
      if (res.ok) loadExpenses();
    }

    renderChips();
    loadExpenses();
  </script>
</body>
</html>`;

  return c.html(html);
});

export default app;
