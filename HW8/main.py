import sqlite3
import os
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

app = FastAPI(
    title="GreenLedger - 中小企業碳盤查與成本核算系統",
    description="符合 ISO 14064-1 概念之範疇一、範疇二碳排放核算與碳費暴險模擬引擎",
    version="1.0.0"
)

DB_PATH = "greenledger.db"

# -------------------------------------------------------------
# 官方排碳係數庫 (單位換算至公噸 CO2e / 原始單位)
# 數值參考：台灣環境部氣候變遷署排放係數與經濟部能源署最新公布係數
# -------------------------------------------------------------
EMISSION_FACTORS = {
    # 範疇二：外購電力 (kg CO2e / 度 -> 換算為 tCO2e)
    "electricity": {
        "name": "外購電力 (台電)",
        "scope": 2,
        "factor_tco2e_per_unit": 0.000495,  # 0.495 kg CO2e / kWh
        "unit": "度 (kWh)",
        "category": "範疇二：能源間接"
    },
    # 範疇一：移動源燃燒 (kg CO2e / 公升 -> 換算為 tCO2e)
    "gasoline": {
        "name": "車用汽油 (公務車/運輸)",
        "scope": 1,
        "factor_tco2e_per_unit": 0.002263,  # 2.263 kg CO2e / L
        "unit": "公升 (L)",
        "category": "範疇一：移動燃燒"
    },
    "diesel": {
        "name": "車用柴油 (貨車/堆高機)",
        "scope": 1,
        "factor_tco2e_per_unit": 0.002606,  # 2.606 kg CO2e / L
        "unit": "公升 (L)",
        "category": "範疇一：移動燃燒"
    },
    # 範疇一：固定源燃燒 (kg CO2e / m3 -> 換算為 tCO2e)
    "natural_gas": {
        "name": "天然氣 (廠區鍋爐/加熱)",
        "scope": 1,
        "factor_tco2e_per_unit": 0.002090,  # 2.090 kg CO2e / m³
        "unit": "立方公尺 (m³)",
        "category": "範疇一：固定燃燒"
    },
    "lpg": {
        "name": "液化石油氣/桶裝瓦斯",
        "scope": 1,
        "factor_tco2e_per_unit": 0.003010,  # 3.010 kg CO2e / kg
        "unit": "公斤 (kg)",
        "category": "範疇一：固定燃燒"
    }
}

# -------------------------------------------------------------
# 資料庫初始化
# -------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT NOT NULL,
            source_type TEXT NOT NULL,
            activity_value REAL NOT NULL,
            co2e_ton REAL NOT NULL,
            record_date TEXT NOT NULL,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------
# 資料傳輸物件 (DTO)
# -------------------------------------------------------------
class ActivityCreate(BaseModel):
    department: str = Field(..., example="金門廠區-加工部")
    source_type: str = Field(..., example="electricity")
    activity_value: float = Field(..., gt=0, example=12500.0)
    record_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    notes: Optional[str] = Field(default="", example="8月份電費單度數")

# -------------------------------------------------------------
# 後端 API 端點
# -------------------------------------------------------------
@app.get("/api/factors")
def get_factors():
    """取得系統支援的排碳源與排放係數"""
    return EMISSION_FACTORS

@app.post("/api/records", status_code=status.HTTP_201_CREATED)
def add_record(entry: ActivityCreate):
    """新增一筆活動數據，自動匹配係數並寫入排放量"""
    if entry.source_type not in EMISSION_FACTORS:
        raise HTTPException(status_code=400, detail="不支援的排碳源類型")

    factor_info = EMISSION_FACTORS[entry.source_type]
    co2e_ton = round(entry.activity_value * factor_info["factor_tco2e_per_unit"], 4)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activity_records (department, source_type, activity_value, co2e_ton, record_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (entry.department, entry.source_type, entry.activity_value, co2e_ton, entry.record_date, entry.notes))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": record_id,
        "co2e_ton": co2e_ton,
        "message": "活動數據建立並完成排放量核算"
    }

@app.get("/api/summary")
def get_summary():
    """匯總計算 Scope 1、Scope 2、總排碳量與台灣碳費試算"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM activity_records ORDER BY id DESC")
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()

    scope1_total = 0.0
    scope2_total = 0.0

    for r in records:
        source_meta = EMISSION_FACTORS.get(r["source_type"], {})
        if source_meta.get("scope") == 1:
            scope1_total += r["co2e_ton"]
        elif source_meta.get("scope") == 2:
            scope2_total += r["co2e_ton"]

    total_emissions = round(scope1_total + scope2_total, 4)
    scope1_total = round(scope1_total, 4)
    scope2_total = round(scope2_total, 4)

    # 碳費暴險模擬 (依據台灣法定與研議之每噸費率)
    carbon_fee_tier1 = round(total_emissions * 300, 2)  # NT$300 / 噸
    carbon_fee_tier2 = round(total_emissions * 500, 2)  # NT$500 / 噸

    return {
        "total_emissions_tco2e": total_emissions,
        "scope1_tco2e": scope1_total,
        "scope2_tco2e": scope2_total,
        "carbon_tax_simulation": {
            "tier_300_ntd": carbon_fee_tier1,
            "tier_500_ntd": carbon_fee_tier2
        },
        "records": records
    }

@app.delete("/api/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM activity_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/api/export-csv")
def export_csv():
    """匯出合規審查 CSV 格式清冊"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, record_date, department, source_type, activity_value, co2e_ton, notes FROM activity_records")
    rows = cursor.fetchall()
    conn.close()

    csv_data = "\ufeff編號,盤查日期,所屬部門,排放源項目,活動數據量,單位,溫室氣體排放當量(tCO2e),備註\n"
    for r in rows:
        meta = EMISSION_FACTORS.get(r[3], {"name": r[3], "unit": "-"})
        csv_data += f"{r[0]},{r[1]},{r[2]},{meta['name']},{r[4]},{meta['unit']},{r[5]},{r[6]}\n"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=carbon_inventory_report.csv"}
    )

# -------------------------------------------------------------
# 前端 Web 儀表板介面 (SPA)
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GreenLedger - 企業碳排盤查與財務成本核算系統</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0b1329; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    </style>
</head>
<body class="p-6">
    <div class="max-w-6xl mx-auto">
        <!-- 標題與操作列 -->
        <header class="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-8 border-b border-slate-800 gap-4">
            <div>
                <h1 class="text-2xl font-bold text-emerald-400 tracking-wide">GreenLedger 企業淨零盤查引擎</h1>
                <p class="text-slate-400 text-sm mt-1">ISO 14064-1 範疇一、範疇二排放量自動核算與碳費衝擊試算</p>
            </div>
            <div class="flex gap-3">
                <a href="/api/export-csv" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 rounded-lg text-sm font-semibold transition">
                    匯出審查清冊 (CSV)
                </a>
            </div>
        </header>

        <!-- KPI 數據卡片 -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
                <p class="text-slate-400 text-xs font-semibold uppercase">總碳排放當量</p>
                <div class="flex items-baseline gap-2 mt-2">
                    <span id="total-co2e" class="text-3xl font-extrabold text-white">0.00</span>
                    <span class="text-slate-400 text-sm">tCO₂e</span>
                </div>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
                <p class="text-slate-400 text-xs font-semibold uppercase">範疇一 (直接排放)</p>
                <div class="flex items-baseline gap-2 mt-2">
                    <span id="scope1-co2e" class="text-3xl font-extrabold text-sky-400">0.00</span>
                    <span class="text-slate-400 text-sm">tCO₂e</span>
                </div>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
                <p class="text-slate-400 text-xs font-semibold uppercase">範疇二 (電力間接)</p>
                <div class="flex items-baseline gap-2 mt-2">
                    <span id="scope2-co2e" class="text-3xl font-extrabold text-amber-400">0.00</span>
                    <span class="text-slate-400 text-sm">tCO₂e</span>
                </div>
            </div>
            <div class="bg-slate-900 border border-emerald-500/20 rounded-xl p-5 shadow-lg bg-emerald-950/20">
                <p class="text-emerald-400 text-xs font-semibold uppercase">法定碳費暴險預估 (NT$300/噸)</p>
                <div class="flex items-baseline gap-2 mt-2">
                    <span class="text-slate-400 text-sm font-bold">NT$</span>
                    <span id="carbon-tax" class="text-3xl font-extrabold text-emerald-400">0</span>
                </div>
            </div>
        </div>

        <!-- 填報表單與活動清單 -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- 數據登錄表單 -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 h-fit">
                <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-400"></span> 登錄能源活動數據
                </h2>
                <form id="record-form" class="space-y-4">
                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">所屬廠區 / 部門</label>
                        <input type="text" id="dept" required class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500" placeholder="例：台北總部 / 彰化二廠">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">排放源種類</label>
                        <select id="source-type" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"></select>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">活動數值 (依對應單位填寫)</label>
                        <input type="number" step="0.01" id="act-val" required class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500" placeholder="例如電費單度數或油單公升數">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">憑證備註</label>
                        <input type="text" id="notes" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500" placeholder="例：2026年Q3電費單">
                    </div>
                    <button type="submit" class="w-full bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold py-2.5 rounded-lg text-sm transition mt-2">
                        即時核算並寫入帳冊
                    </button>
                </form>
            </div>

            <!-- 盤查清冊列表 -->
            <div class="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h2 class="text-lg font-bold text-white mb-4">排放活動數據明細表</h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm text-slate-300">
                        <thead class="bg-slate-950 text-xs text-slate-400 uppercase">
                            <tr>
                                <th class="py-3 px-4">部門</th>
                                <th class="py-3 px-4">項目</th>
                                <th class="py-3 px-4">活動量</th>
                                <th class="py-3 px-4">排放量 (tCO₂e)</th>
                                <th class="py-3 px-4">操作</th>
                            </tr>
                        </thead>
                        <tbody id="records-table-body" class="divide-y divide-slate-800">
                            <!-- 動態渲染 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        let factorsCache = {};

        async function fetchFactors() {
            const res = await fetch('/api/factors');
            factorsCache = await res.json();
            const select = document.getElementById('source-type');
            select.innerHTML = '';
            for (const [key, item] of Object.entries(factorsCache)) {
                const opt = document.createElement('option');
                opt.value = key;
                opt.textContent = `[${item.category}] ${item.name} (${item.unit})`;
                select.appendChild(opt);
            }
        }

        async function refreshDashboard() {
            const res = await fetch('/api/summary');
            const data = await res.json();

            document.getElementById('total-co2e').textContent = data.total_emissions_tco2e.toFixed(3);
            document.getElementById('scope1-co2e').textContent = data.scope1_tco2e.toFixed(3);
            document.getElementById('scope2-co2e').textContent = data.scope2_tco2e.toFixed(3);
            document.getElementById('carbon-tax').textContent = data.carbon_tax_simulation.tier_300_ntd.toLocaleString();

            const tbody = document.getElementById('records-table-body');
            tbody.innerHTML = '';

            if (data.records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center py-6 text-slate-500">尚無盤查數據，請於左側登錄。</td></tr>';
                return;
            }

            data.records.forEach(r => {
                const meta = factorsCache[r.source_type] || { name: r.source_type, unit: '' };
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="py-3 px-4 font-medium text-white">${r.department}</td>
                    <td class="py-3 px-4"><span class="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">${meta.name}</span></td>
                    <td class="py-3 px-4">${r.activity_value.toLocaleString()} ${meta.unit}</td>
                    <td class="py-3 px-4 font-mono font-bold text-emerald-400">${r.co2e_ton.toFixed(4)}</td>
                    <td class="py-3 px-4">
                        <button onclick="deleteRecord(${r.id})" class="text-rose-400 hover:text-rose-300 text-xs">刪除</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function deleteRecord(id) {
            if (confirm('確定刪除此筆盤查紀錄？')) {
                await fetch(`/api/records/${id}`, { method: 'DELETE' });
                refreshDashboard();
            }
        }

        document.getElementById('record-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                department: document.getElementById('dept').value,
                source_type: document.getElementById('source-type').value,
                activity_value: parseFloat(document.getElementById('act-val').value),
                notes: document.getElementById('notes').value
            };

            await fetch('/api/records', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            document.getElementById('act-val').value = '';
            document.getElementById('notes').value = '';
            refreshDashboard();
        });

        (async () => {
            await fetchFactors();
            await refreshDashboard();
        })();
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
