import { useCallback, useEffect, useState } from 'react';
import Header from '../components/Header';
import { addUnit, deleteUnit, fetchUnits, updateUnit } from '../api/sla4';
import type { UnitAreaItem } from '../api/sla4';

const EMPTY_FORM = {
  unit_name: '',
  unit_type: 'Pendukung' as 'Pusat' | 'Pendukung',
  kawasan: 'Dalam Kawasan' as 'Dalam Kawasan' | 'Luar Kawasan',
  active: true,
  valid_from: '',
  valid_to: '',
};

export default function UnitAreaPage() {
  const [items, setItems] = useState<UnitAreaItem[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editing, setEditing] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setItems((await fetchUnits(false)).items);
  }, []);

  useEffect(() => { void load(); }, [load]);

  function reset() {
    setEditing(null);
    setForm(EMPTY_FORM);
  }

  async function save() {
    if (!form.unit_name.trim()) return alert('Nama unit wajib diisi.');
    setLoading(true);
    try {
      const payload = {
        ...form,
        valid_from: form.valid_from || undefined,
        valid_to: form.valid_to || undefined,
      };
      if (editing === null) await addUnit(payload);
      else await updateUnit(editing, payload);
      reset();
      await load();
    } catch (error: any) {
      alert(error.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  }

  function startEdit(row: UnitAreaItem) {
    setEditing(row.id);
    setForm({
      unit_name: row.unit_name,
      unit_type: row.unit_type,
      kawasan: row.kawasan,
      active: row.active,
      valid_from: row.valid_from || '',
      valid_to: row.valid_to || '',
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function remove(id: number) {
    if (!window.confirm('Hapus mapping unit ini?')) return;
    try {
      await deleteUnit(id);
      await load();
    } catch (error: any) {
      alert(error.response?.data?.detail || error.message);
    }
  }

  return (
    <div className="min-h-screen bg-paper text-ink pb-12">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-7 space-y-5">
        <section className="bg-surface border border-rule rounded-sm p-5">
          <h2 className="font-serif text-xl font-semibold">Master Unit</h2>
          <p className="text-xs text-slate-muted mt-1">
            Raw data tidak memiliki atribut kawasan. Mapping ini menentukan jenis unit, kawasan, dan target H+1 / H+2 yang digunakan dashboard.
          </p>
        </section>

        <section className="bg-surface border border-rule rounded-sm p-5">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-semibold text-sm">{editing === null ? 'Tambah Unit' : `Edit Unit #${editing}`}</h3>
            {editing !== null && <button onClick={reset} className="text-xs text-brass">Batal Edit</button>}
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-3 mt-4">
            <input value={form.unit_name} onChange={e => setForm({ ...form, unit_name: e.target.value })} placeholder="Nama Unit" className="border border-rule rounded-sm px-3 py-2 text-sm lg:col-span-2" />
            <select value={form.unit_type} onChange={e => setForm({ ...form, unit_type: e.target.value as any })} className="border border-rule rounded-sm px-3 py-2 text-sm">
              <option>Pusat</option><option>Pendukung</option>
            </select>
            <select value={form.kawasan} onChange={e => setForm({ ...form, kawasan: e.target.value as any })} className="border border-rule rounded-sm px-3 py-2 text-sm">
              <option>Dalam Kawasan</option><option>Luar Kawasan</option>
            </select>
            <select value={form.active ? 'Aktif' : 'Nonaktif'} onChange={e => setForm({ ...form, active: e.target.value === 'Aktif' })} className="border border-rule rounded-sm px-3 py-2 text-sm">
              <option>Aktif</option><option>Nonaktif</option>
            </select>
            <input type="date" value={form.valid_from} onChange={e => setForm({ ...form, valid_from: e.target.value })} className="border border-rule rounded-sm px-3 py-2 text-sm" title="Berlaku mulai" />
            <input type="date" value={form.valid_to} onChange={e => setForm({ ...form, valid_to: e.target.value })} className="border border-rule rounded-sm px-3 py-2 text-sm" title="Berlaku sampai" />
            <button disabled={loading} onClick={save} className="bg-ink text-white px-4 py-2 text-xs rounded-sm">{loading ? 'Menyimpan...' : editing === null ? 'Tambah' : 'Simpan Perubahan'}</button>
          </div>
        </section>

        <section className="bg-surface border border-rule rounded-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-rule flex justify-between">
            <h3 className="font-semibold text-sm">Daftar Unit</h3>
            <span className="text-xs text-slate-muted">{items.length} mapping</span>
          </div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-paper text-xs">
                <tr>
                  <th className="text-left px-5 py-3">Unit</th>
                  <th className="text-left px-5 py-3">Jenis</th>
                  <th className="text-left px-5 py-3">Kawasan</th>
                  <th className="text-center px-5 py-3">Target</th>
                  <th className="text-left px-5 py-3">Berlaku</th>
                  <th className="text-left px-5 py-3">Status</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {items.map(row => (
                  <tr key={row.id}>
                    <td className="px-5 py-3 font-semibold">{row.unit_name}</td>
                    <td className="px-5 py-3">{row.unit_type}</td>
                    <td className="px-5 py-3">{row.kawasan}</td>
                    <td className="px-5 py-3 text-center">H+{row.target_days ?? '-'}</td>
                    <td className="px-5 py-3 text-xs">{row.valid_from || '—'} s/d {row.valid_to || '—'}</td>
                    <td className="px-5 py-3">{row.active ? 'Aktif' : 'Nonaktif'}</td>
                    <td className="px-5 py-3 text-right whitespace-nowrap">
                      <button onClick={() => startEdit(row)} className="text-brass text-xs mr-3">Edit</button>
                      <button onClick={() => remove(row.id)} className="text-status-bad text-xs">Hapus</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!items.length && <p className="p-6 text-xs text-slate-muted">Belum ada master unit.</p>}
          </div>
        </section>
      </main>
    </div>
  );
}
