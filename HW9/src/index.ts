import { Hono } from 'hono';

type Bindings = {
  NOTES_KV: KVNamespace;
};

interface Note {
  id: string;
  text: string;
  createdAt: string;
}

const app = new Hono<{ Bindings: Bindings }>();

// API: 取得所有便條
app.get('/api/notes', async (c) => {
  const data = await c.env.NOTES_KV.get('notes_data');
  const notes: Note[] = data ? JSON.parse(data) : [
    {
      id: '1',
      text: '歡迎使用運行在 Cloudflare 邊緣節點的 Web 應用！',
      createdAt: new Date().toLocaleTimeString('zh-TW', { hour12: false }),
    },
  ];
  return c.json(notes);
});

// API: 新增便條
app.post('/api/notes', async (c) => {
  const body = await c.req.json<{ text: string }>();
  if (!body.text || body.text.trim() === '') {
    return c.json({ error: '內容不能為空' }, 400);
  }

  const data = await c.env.NOTES_KV.get('notes_data');
  const notes: Note[] = data ? JSON.parse(data) : [];

  const newNote: Note = {
    id: crypto.randomUUID(),
    text: body.text.trim(),
    createdAt: new Date().toLocaleTimeString('zh-TW', { hour12: false }),
  };

  notes.unshift(newNote);

  // 永久寫入 Cloudflare KV
  await c.env.NOTES_KV.put('notes_data', JSON.stringify(notes));

  return c.json(newNote, 201);
});

// 前端頁面
app.get('/', (c) => {
  const html = `<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cloudflare Edge Notes</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen py-10 px-4">
  <div class="max-w-xl mx-auto space-y-6">
    <header class="border-b border-slate-700 pb-4">
      <h1 class="text-3xl font-bold text-amber-400">⚡ Edge Notes</h1>
      <p class="text-sm text-slate-400 mt-1">已連接 Cloudflare KV 永久儲存</p>
    </header>

    <div class="flex gap-2">
      <input id="noteInput" type="text" placeholder="輸入記事內容..." 
        class="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-amber-400 text-slate-100">
      <button onclick="addNote()" 
        class="bg-amber-500 hover:bg-amber-600 text-slate-900 font-semibold px-5 py-2 rounded-lg transition">
        新增
      </button>
    </div>

    <div id="notesContainer" class="space-y-3"></div>
  </div>

  <script>
    async function loadNotes() {
      const res = await fetch('/api/notes');
      const data = await res.json();
      const container = document.getElementById('notesContainer');
      container.innerHTML = data.map(item => \`
        <div class="p-4 bg-slate-800 border border-slate-700 rounded-lg flex justify-between items-start">
          <p class="text-slate-200 break-all">\${item.text}</p>
          <span class="text-xs text-slate-500 ml-4 whitespace-nowrap">\${item.createdAt}</span>
        </div>
      \`).join('');
    }

    async function addNote() {
      const input = document.getElementById('noteInput');
      const text = input.value;
      if (!text.trim()) return;

      const res = await fetch('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });

      if (res.ok) {
        input.value = '';
        loadNotes();
      }
    }

    loadNotes();
  </script>
</body>
</html>`;

  return c.html(html);
});

export default app;
