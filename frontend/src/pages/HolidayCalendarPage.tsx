import { useCallback, useEffect, useState } from 'react';
import Header from '../components/Header';
import {
  addHolidaySLA4,
  deleteHolidaySLA4,
  fetchHolidaysSLA4,
  importHolidaysSLA4,
  previewHolidaysSLA4,
  updateHolidaySLA4,
} from '../api/sla4';
import type { HolidayItemSLA4 } from '../api/sla4';

export default function HolidayCalendarPage() {
  const [year, setYear] = useState(2026);
  const [items, setItems] = useState<HolidayItemSLA4[]>([]);
  const [version, setVersion] = useState<string | null>(null);
  const [date, setDate] = useState('');
  const [desc, setDesc] = useState('');
  const [editing, setEditing] = useState<number | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [pStart, setPStart] = useState('');
  const [pEnd, setPEnd] = useState('');
  const [importFile, setImportFile] = useState<File | null>(null);

  const load = useCallback(async () => {
    const r = await fetchHolidaysSLA4(year);
    setItems(r.items);
    setVersion(r.version);
  }, [year]);

  useEffect(() => { void load(); }, [load]);

  function resetForm() {
    setEditing(null);
    setDate('');
    setDesc('');
  }

  async function save() {
    if (!date) return alert('Tanggal wajib diisi.');
    try {
      if (editing === null) await addHolidaySLA4(date, desc);
      else await updateHolidaySLA4(editing, date, desc);
      resetForm();
      await load();
    } catch (error: any) {
      alert(error.response?.data?.detail || error.message);
    }
  }

  function edit(row: HolidayItemSLA4) {
    setEditing(row.id);
    setDate(row.date);
    setDesc(row.description);
  }

  async function remove(id: number) {
    if (!window.confirm('Hapus tanggal hari libur ini dari kalender aktif?')) return;
    try {
      await deleteHolidaySLA4(id);
      await load();
    } catch (error: any) {
      alert(error.response?.data?.detail || error.message);
    }
  }

  async function runPreview() {
    if (!pStart || !pEnd) return;
    setPreview(await previewHolidaysSLA4(pStart, pEnd));
  }

  return (
    <div className="min-h-screen bg-paper text-ink pb-12">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-7 space-y-6">
        <section className="bg-surface border border-rule rounded-sm p-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="font-serif text-xl font-semibold">Kalender Hari Libur</h2>
              <p className="text-xs text-slate-muted mt-1">Satu sumber kalender untuk SLA 4A dan SLA 4B. Setiap perubahan membuat version baru.</p>
            </div>
            <div className="flex items-end gap-3">
              <div><label className="block text-[11px] text-slate-muted mb-1">Tahun</label><select value={year} onChange={e => setYear(Number(e.target.value))} className="border border-rule rounded-sm px-3 py-2 text-sm"><option>2026</option><option>2027</option></select></div>
              <div className="text-xs text-slate-muted pb-2">Version: <b className="text-ink">{version || 'Belum ada'}</b></div>
            </div>
          </div>
        </section>

        <section className="bg-surface border border-rule rounded-sm p-5">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-72"><label className="block text-[11px] text-slate-muted mb-1">Import kalender vendor</label><label className="block border border-rule rounded-sm px-3 py-2 text-sm cursor-pointer">{importFile?.name || 'Pilih Excel'}<input type="file" accept=".xlsx,.xls" className="hidden" onChange={e => setImportFile(e.target.files?.[0] || null)} /></label></div>
            <button onClick={async () => { if (!importFile) return alert('Pilih file terlebih dahulu.'); try { const r = await importHolidaysSLA4(importFile, year); alert(`${r.message} Version ${r.version}`); setImportFile(null); await load(); } catch (error: any) { alert(error.response?.data?.detail || error.message); } }} className="border border-brass text-brass px-4 py-2 text-xs rounded-sm">Import</button>
          </div>
          <p className="text-[11px] text-slate-muted mt-2">Fallback vendor membaca Reference List C3:C20 agar SLA 4 menggunakan kalender lengkap.</p>
        </section>

        <section className="bg-surface border border-rule rounded-sm p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">{editing === null ? 'Tambah Hari Libur' : `Edit Hari Libur #${editing}`}</h3>
            {editing !== null && <button onClick={resetForm} className="text-xs text-brass">Batal Edit</button>}
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            <input type="date" value={date} onChange={e => setDate(e.target.value)} className="border border-rule rounded-sm px-3 py-2 text-sm" />
            <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="Keterangan" className="border border-rule rounded-sm px-3 py-2 text-sm flex-1 min-w-56" />
            <button onClick={save} className="bg-ink text-white px-4 py-2 text-xs rounded-sm">{editing === null ? 'Tambah' : 'Simpan Perubahan'}</button>
          </div>
        </section>

        <section className="bg-surface border border-rule rounded-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-rule flex justify-between"><h3 className="font-semibold text-sm">Kalender Aktif {year}</h3><span className="text-xs text-slate-muted">{items.length} tanggal</span></div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-paper text-xs"><tr><th className="text-left px-5 py-3">Tanggal</th><th className="text-left px-5 py-3">Keterangan</th><th className="text-left px-5 py-3">Version</th><th className="px-5 py-3" /></tr></thead>
              <tbody className="divide-y divide-rule">
                {items.map(row => <tr key={row.id}><td className="px-5 py-3">{row.date}</td><td className="px-5 py-3">{row.description || '-'}</td><td className="px-5 py-3 text-xs text-slate-muted">{row.version}</td><td className="px-5 py-3 text-right whitespace-nowrap"><button onClick={() => edit(row)} className="text-brass text-xs mr-3">Edit</button><button onClick={() => remove(row.id)} className="text-status-bad text-xs">Hapus</button></td></tr>)}
              </tbody>
            </table>
            {!items.length && <p className="p-6 text-xs text-slate-muted">Belum ada hari libur di kalender aktif.</p>}
          </div>
        </section>

        <section className="bg-surface border border-rule rounded-sm p-5">
          <h3 className="font-semibold text-sm">Preview Hari Kerja</h3>
          <p className="text-xs text-slate-muted mt-1">Preview selalu menggunakan latest calendar version untuk seluruh tahun yang dilalui range.</p>
          <div className="flex flex-wrap gap-2 mt-3"><input type="date" value={pStart} onChange={e => setPStart(e.target.value)} className="border border-rule rounded-sm px-3 py-2 text-sm" /><input type="date" value={pEnd} onChange={e => setPEnd(e.target.value)} className="border border-rule rounded-sm px-3 py-2 text-sm" /><button onClick={runPreview} className="bg-ink text-white px-4 py-2 text-xs rounded-sm">Preview</button></div>
          {preview && <div className="mt-4"><div className="grid sm:grid-cols-2 gap-3 mb-4"><div className="bg-paper p-4 rounded-sm"><p className="text-xs text-slate-muted">NETWORKDAYS</p><p className="text-2xl font-bold">{preview.networkdays}</p></div><div className="bg-paper p-4 rounded-sm"><p className="text-xs text-slate-muted">NETWORKDAYS - 1</p><p className="text-2xl font-bold">{preview.networkdays_minus_one}</p></div></div><p className="text-xs text-slate-muted mb-3">Version yang digunakan: {Object.entries(preview.calendar_versions || {}).map(([y, v]) => `${y}: ${v}`).join(' • ') || 'Belum ada kalender'}</p><div className="max-h-72 overflow-auto border border-rule rounded-sm">{preview.days.map((d: any) => <div key={d.date} className="flex justify-between px-4 py-2 text-xs border-b border-rule"><span>{d.date}</span><span>{d.reason}</span></div>)}</div></div>}
        </section>
      </main>
    </div>
  );
}
