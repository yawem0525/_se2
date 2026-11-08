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

// 預設範例資料（在 KV 連線異常或初次載入時呈現）
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
      if (data) {
        return c.json(JSON.parse(data));
      }
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
    members: string;
  }>();

  if (!body.title || !body.amount || !body.payer) {
    return c.json({ error: '請完整填寫項目、金額與付款人' }, 400);
  }

  // 整理參與成員陣列
  const memberList = body.members
    ? body.members.split(',').map((m) => m.trim()).filter(Boolean)
    : [body.payer];

  if (!memberList.includes(body.payer)) {
    memberList.push(body.payer);
  }

  const newExpense: Expense = {
    id: crypto.randomUUID(),
    title: body.title.trim(),
    amount: Number(body.amount),
    payer: body.payer.trim(),
    members: memberList,
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

// 前端介面（可愛馬卡龍粉嫩主題）
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

    <!-- 可愛頁首 -->
    <header class="text-center space-y-2">
      <div class="inline-flex items-center justify-center w-14 h-14 bg-pink-200/80 rounded-full shadow-inner text-2xl">
        🐰
      </div>
      <h1 class="text-3xl font-extrabold text-pink-600 tracking-wide">萌萌小帳本 ✨</h1>
      <p class="text-xs text-pink-400 font-bold bg-pink-100/60 inline-block px-3 py-1 rounded-full">
        Cloudflare Edge ☁️ 算帳不傷感情 💕
      </p>
    </header>

    <!-- 結算概覽卡片 -->
    <section class="bg-white/80 backdrop-blur-md border border-pink-200/80 rounded-3xl p-5 shadow-sm space-y-3">
      <div class="flex justify-between items-center border-b border-pink-100 pb-2">
        <h2 class="font-bold text-pink-700 flex items-center gap-1">📊 結算試算</h2>
        <span id="totalAmount" class="text-sm font-bold text-rose-500 bg-rose-50 px-2.5 py-0.5 rounded-full">總計: $0</span>
      </div>
      <div id="balanceList" class="grid grid-cols-2 gap-2 text-xs text-slate-600">
        <!-- 即時計算收支 -->
      </div>
    </section>

    <!-- 輸入表單卡片 -->
    <section class="bg-white rounded-3xl p-6 shadow-md border-2 border-pink-100 space-y-4">
      <h3 class="font-bold text-pink-600 text-sm flex items-center gap-1.5">
        <span>✏️</span> 記下一筆新消費
      </h3>
      
      <div class="space-y-3 text-sm">
        <div>
          <label class="block text-xs font-bold text-slate-500 mb-1">消費項目</label>
          <input id="title" type="text" placeholder="例：好吃拉麵 🍜" 
            class="w-full bg-pink-50/50 border border-pink-200 rounded-2xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-pink-300 transition">
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-bold text-slate-500 mb-1">總金額 ($)</label>
            <input id="amount" type="number" placeholder="360" 
              class="w-full bg-pink-50/50 border border-pink-200 rounded-2xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-pink-300 transition">
          </div>
          <div>
            <label class="block text-xs font-bold text-slate-500 mb-1">誰先墊錢？</label>
            <input id="payer" type="text" placeholder="例：小雅" 
              class="w-full bg-pink-50/50 border border-pink-200 rounded-2xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-pink-300 transition">
          </div>
        </div>

        <div>
          <label class="block text-xs font-bold text-slate-500 mb-1">分攤成員 (用逗號隔開)</label>
          <input id="members" type="text" placeholder="例：小雅, 小雯, 阿明" 
            class="w-full bg-pink-50/50 border border-pink-200 rounded-2xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-pink-300 transition">
        </div>

        <button onclick="addExpense()" 
          class="w-full mt-2 bg-gradient-to-r from-pink-400 to-rose-400 hover:from-pink-500 hover:to-rose-500 text-white font-bold py-2.5 rounded-2xl shadow-sm hover:shadow active:scale-[0.99] transition">
          加入小帳本 🍰
        </button>
      </div>
    </section>

    <!-- 歷史紀錄列表 -->
    <section class="space-y-3">
      <h3 class="font-bold text-pink-600 text-sm px-1 flex items-center gap-1">
        <span>📜</span> 消費紀錄明細
      </h3>
      <div id="expenseList" class="space-y-2.5">
        <!-- 動態渲染項目 -->
      </div>
    </section>

  </div>

  <script>
    let expenses = [];

    async function loadExpenses() {
      const res = await fetch('/api/expenses');
      expenses = await res.json();
      renderUI();
    }

    function renderUI() {
      const container = document.getElementById('expenseList');
      const totalAmountEl = document.getElementById('totalAmount');
      const balanceEl = document.getElementById('balanceList');

      // 1. 計算總花費與每人應收付
      let total = 0;
      const balances = {}; // 正數代表應收，負數代表應付

      expenses.forEach(item => {
        total += item.amount;
        const splitCount = item.members.length;
        const perPerson = item.amount / splitCount;

        // 先墊錢的人增加應收
        balances[item.payer] = (balances[item.payer] || 0) + item.amount;

        // 所有人扣除應付
        item.members.forEach(member => {
          balances[member] = (balances[member] || 0) - perPerson;
        });
      });

      totalAmountEl.textContent = '總計: $' + Math.round(total);

      // 渲染結算摘要
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

      // 渲染紀錄清單
      container.innerHTML = expenses.map(item => \`
        <div class="bg-white border border-pink-100 rounded-2xl p-4 shadow-sm hover:shadow transition space-y-2">
          <div class="flex justify-between items-start">
            <div>
              <h4 class="font-bold text-slate-800 text-sm">\${item.title}</h4>
              <div class="text-xs text-pink-500 mt-0.5">
                墊付人：<span class="font-bold bg-pink-50 px-1.5 py-0.5 rounded-md">\${item.payer}</span>
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
      const payer = document.getElementById('payer').value;
      const members = document.getElementById('members').value;

      if (!title || !amount || !payer) {
        alert('請填寫完整項目、金額與墊付人喔！🐰');
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
      if (res.ok) {
        loadExpenses();
      }
    }

    loadExpenses();
  </script>
</body>
</html>`;

  return c.html(html);
});

export default app;
