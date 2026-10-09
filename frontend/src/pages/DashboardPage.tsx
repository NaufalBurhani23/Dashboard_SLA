import { useCallback, useEffect, useState } from 'react';
import Header from '../components/Header';
import RankingPanels from '../components/RankingPanels';
import TrendChart from '../components/TrendChart';
import UnitAchievementChart from '../components/UnitAchievementChart';
import { exportUrl, fetchDashboard, importExcel } from '../api/client';
import type { DashboardPayload, DashboardSlaSummary, DashboardUnitRow, DashboardUnitStat } from '../api/client';
import { fetchSLA4Dashboard, importSLA4 } from '../api/sla4';
import type { SLA4DashboardPayload, SLA4UnitSummary } from '../api/sla4';
import type { Ranking, TrendPoint } from '../types';

const ZERO_SUMMARY: DashboardSlaSummary = {
  total_records: 0, denominator: 0, on_time: 0, out_of_date: 0, incomplete: 0,
  percentage: 0, ontime_pct: 0, ood_pct: 0, inc_pct: 0,
};

const ZERO_RANKING: Ranking = { top5: [], bottom5: [] };

const EMPTY: DashboardPayload = {
  selected_sla: 'ALL', available_units: [],
  summaries: { 'SLA 1': ZERO_SUMMARY, 'SLA 2': ZERO_SUMMARY, 'SLA 3': ZERO_SUMMARY },
  unit_table: [], ranking: ZERO_RANKING,
  rankings: { 'SLA 1': ZERO_RANKING, 'SLA 2': ZERO_RANKING, 'SLA 3': ZERO_RANKING },
  trend: [], trends: { 'SLA 1': [], 'SLA 2': [], 'SLA 3': [] }, trend_sla: 'SLA 1',
};

const SLA_CODES = ['SLA 1', 'SLA 2', 'SLA 3', 'SLA 4'] as const;
type SelectedSla = 'ALL' | typeof SLA_CODES[number];

const fmt = (n: number) => new Intl.NumberFormat('id-ID').format(n || 0);

function toSummary(s: SLA4DashboardPayload['summary']): DashboardSlaSummary {
  return {
    total_records: s.total_records,
    denominator: s.denominator,
    on_time: s.on_time,
    out_of_date: s.out_of_date,
    incomplete: s.incomplete,
    percentage: s.percentage,
    ontime_pct: s.ontime_pct,
    ood_pct: s.ood_pct,
    inc_pct: s.inc_pct,
  };
}

function toUnitStat(row: SLA4UnitSummary): DashboardUnitStat {
  return {
    total: row.total,
    denominator: row.denominator,
    on_time: row.on_time,
    out_of_date: row.out_of_date,
    incomplete: row.incomplete,
    percentage: row.percentage,
  };
}

function toTrend(points: SLA4DashboardPayload['trend']): TrendPoint[] {
  return points.map((p) => ({
    tanggal: p.tanggal,
    jumlah_arsip: p.jumlah_arsip,
    jumlah_berhasil: p.jumlah_berhasil,
    persentase: p.persentase,
  }));
}

function rankingFrom4(data: SLA4DashboardPayload): Ranking {
  return {
    top5: data.ranking.top5,
    bottom5: data.ranking.bottom5,
  };
}

type SummaryCardProps = { label: string; value: string; sub?: string; dark?: boolean; tone?: 'good' | 'bad' | 'warn' };
function SummaryCard({ label, value, sub, dark = false, tone }: SummaryCardProps) {
  const toneClass = tone === 'good' ? 'text-status-good' : tone === 'bad' ? 'text-status-bad' : tone === 'warn' ? 'text-status-warn' : '';
  return (
    <div className={dark ? 'bg-ink text-white rounded-sm p-5' : 'bg-surface border border-rule rounded-sm p-5'}>
      <p className={dark ? 'text-xs text-white/60' : 'text-xs text-slate-muted'}>{label}</p>
      <p className={`text-3xl font-bold mt-2 ${dark ? '' : toneClass}`}>{value}</p>
      {sub && <p className={dark ? 'text-xs text-white/60 mt-2' : 'text-xs text-slate-muted mt-2'}>{sub}</p>}
    </div>
  );
}

function StatusSync({ sla, summary }: { sla: typeof SLA_CODES[number]; summary: DashboardSlaSummary }) {
  return (
    <section className="bg-surface border border-rule rounded-sm p-5">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h3 className="font-serif text-lg font-semibold">Status Sinkronisasi Perhitungan {sla}</h3>
        <span className="text-xs text-slate-muted">Total: {fmt(summary.total_records)} arsip</span>
      </div>
      <p className="text-xs text-slate-muted mb-4">Keterangan: <b>ON TIME</b> = Yes (memenuhi SLA) • <b>OUT OF DATE</b> = No (tidak memenuhi SLA) • <b>INCOMPLETE</b> = N/A (data belum lengkap / belum dapat dihitung).</p>
      <div className="grid md:grid-cols-4 gap-3">
        <div className="border border-rule rounded-sm p-4"><p className="text-[11px] text-slate-muted">TOTAL ARSIP</p><p className="text-2xl font-bold mt-1">{fmt(summary.total_records)}</p></div>
        <div className="border border-status-good/30 bg-status-goodbg rounded-sm p-4"><p className="text-[11px] text-status-good">ON TIME</p><p className="text-2xl font-bold mt-1 text-status-good">{fmt(summary.on_time)}</p><p className="text-[11px] text-status-good">{summary.ontime_pct}%</p></div>
        <div className="border border-status-bad/30 bg-status-badbg rounded-sm p-4"><p className="text-[11px] text-status-bad">OUT OF DATE</p><p className="text-2xl font-bold mt-1 text-status-bad">{fmt(summary.out_of_date)}</p><p className="text-[11px] text-status-bad">{summary.ood_pct}%</p></div>
        <div className="border border-status-warn/30 bg-status-warnbg rounded-sm p-4"><p className="text-[11px] text-status-warn">INCOMPLETE</p><p className="text-2xl font-bold mt-1 text-status-warn">{fmt(summary.incomplete)}</p><p className="text-[11px] text-status-warn">{summary.inc_pct}%</p></div>
      </div>
    </section>
  );
}

function UnitTable({ rows, sla, unit, setUnit, all, availableUnits }: { rows: DashboardUnitRow[]; sla: SelectedSla; unit: string; setUnit: (v: string) => void; all: boolean; availableUnits: string[] }) {
  // Keep every unit in the selector even when the table is currently filtered
  // to a single unit, so users can switch directly from one unit to another.
  const options = [...new Set(availableUnits)].sort((a, b) => a.localeCompare(b));
  const stat = (row: DashboardUnitRow, code: string) => {
    const key = code === 'SLA 1' ? 'sla1' : code === 'SLA 2' ? 'sla2' : code === 'SLA 3' ? 'sla3' : 'sla4';
    // SLA 4 rows can arrive either in the unified shape (row.sla4) or in the
    // dedicated SLA 4 shape (total/denominator/on_time/...). Support both so
    // the shared Capaian SLA per Unit table renders the real SLA 4 values.
    // When a single SLA is selected, backend returns the unit statistics
    // as a flat row ({ total, on_time, out_of_date, ... }). When ALL is
    // selected, the same statistics are nested under sla1/sla2/sla4.
    // Normalize both shapes so the shared unit table always renders the
    // actual numbers instead of falling back to 0/0.
    if (!row[key]) {
      return {
        total: row.total ?? 0,
        denominator: row.denominator ?? row.total ?? 0,
        on_time: row.on_time ?? 0,
        out_of_date: row.out_of_date ?? 0,
        incomplete: row.incomplete ?? 0,
        percentage: row.percentage ?? 0,
      };
    }
    return row[key];
  };
  return (
    <section className="bg-surface border border-rule rounded-sm p-5">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-4">
        <div><h3 className="font-serif text-lg font-semibold">Capaian SLA per Unit</h3><p className="text-xs text-slate-muted mt-1">{all ? 'Menampilkan capaian seluruh SLA yang tersedia per unit.' : `Menampilkan capaian ${sla} per unit.`}</p></div>
        <div><label className="block text-[11px] font-medium text-slate-muted mb-1">Unit yang ditampilkan</label><select value={unit} onChange={(e) => setUnit(e.target.value)} className="border border-rule rounded-sm px-3 py-2 text-sm min-w-56"><option value="">Semua Unit</option>{options.map((o) => <option key={o} value={o}>{o}</option>)}</select></div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="bg-slate-50 border-y border-rule"><th className="text-left px-4 py-3">UNIT</th>{(all ? SLA_CODES : [sla]).map((code) => <th key={code} className="text-center px-4 py-3">{code}</th>)}</tr></thead>
          <tbody>{rows.map((row) => <tr key={row.unit} className="border-b border-rule"><td className="px-4 py-3 font-semibold">{row.unit}</td>{(all ? SLA_CODES : [sla]).map((code) => { const s = stat(row, code); return <td key={code} className="px-4 py-3 text-center"><b>{s?.percentage ?? 0}%</b><div className="text-xs text-slate-muted">({fmt(s?.on_time ?? 0)}/{fmt(s?.total ?? 0)})</div></td>; })}</tr>)}</tbody>
        </table>
      </div>
      {!rows.length && <p className="text-sm text-slate-muted py-5">Belum ada data unit untuk filter yang dipilih.</p>}
    </section>
  );
}

function TrendFilter({ sla, unit, setUnit, units }: { sla: typeof SLA_CODES[number]; unit: string; setUnit: (v: string) => void; units: string[] }) {
  return (
    <section className="bg-surface border border-rule rounded-sm p-5"><div className="flex flex-wrap items-end gap-4"><div><label className="block text-[11px] font-medium text-slate-muted mb-1">Unit Trend {sla}</label><select value={unit} onChange={(e) => setUnit(e.target.value)} className="border border-rule rounded-sm px-3 py-2 text-sm min-w-56"><option value="">Semua Unit</option>{units.map((u) => <option key={u}>{u}</option>)}</select></div><span className="text-[11px] text-slate-muted pb-2">Tren harian mengikuti hasil {sla} final.</span></div></section>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload>(EMPTY);
  const [sla4, setSla4] = useState<SLA4DashboardPayload | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [sla, setSla] = useState<SelectedSla>('ALL');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [tableUnit, setTableUnit] = useState('');
  const [trendUnit, setTrendUnit] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setError('');
      const base = await fetchDashboard({ sla: sla === 'SLA 4' ? 'ALL' : sla, startDate: start, endDate: end, tableUnit, trendUnit });
      setData(base);
      try {
        const s4 = await fetchSLA4Dashboard({ startDate: start, endDate: end, tableUnit, trendUnit });
        setSla4(s4);
      } catch (err) {
        console.warn('SLA 4 dashboard belum tersedia:', err);
        setSla4(null);
      }
    } catch (err) {
      console.error(err);
      setError('Gagal mengambil data dashboard. Pastikan backend berjalan.');
    }
  }, [sla, start, end, tableUnit, trendUnit]);

  useEffect(() => { void load(); }, [load]);

  async function upload() {
    if (!file) { alert('Pilih raw Excel terlebih dahulu.'); return; }
    setLoading(true);
    try {
      const [r12, r4] = await Promise.allSettled([importExcel(file), importSLA4(file)]);
      const messages: string[] = [];
      if (r12.status === 'fulfilled') {
        messages.push(`SLA 1 Yes/No/N/A: ${r12.value.sla1?.Yes ?? '-'} / ${r12.value.sla1?.No ?? '-'} / ${r12.value.sla1?.['N/A'] ?? '-'}`);
        messages.push(`SLA 2 Final Yes/No/N/A: ${r12.value.sla2?.final?.Yes ?? '-'} / ${r12.value.sla2?.final?.No ?? '-'} / ${r12.value.sla2?.final?.['N/A'] ?? '-'}`);
        messages.push(`SLA 3 Final Yes/No/N/A: ${r12.value.sla3?.final?.Yes ?? '-'} / ${r12.value.sla3?.final?.No ?? '-'} / ${r12.value.sla3?.final?.['N/A'] ?? '-'}`);
      } else messages.push('SLA 1/2: gagal diproses.');
      if (r4.status === 'fulfilled') messages.push(`SLA 4 Final Yes/No/N/A: ${r4.value.final.Yes} / ${r4.value.final.No} / ${r4.value.final['N/A']}`);
      else messages.push('SLA 4: gagal diproses.');
      alert(`Import selesai.\n${messages.join('\n')}`);
      await load();
    } catch (err: any) { alert('Gagal import: ' + (err.response?.data?.detail || err.message)); }
    finally { setLoading(false); }
  }

  function resetFilters() { setSla('ALL'); setStart(''); setEnd(''); setTableUnit(''); setTrendUnit(''); }

  const selected = sla;
  const activeCode: typeof SLA_CODES[number] = selected === 'ALL' ? 'SLA 1' : selected;
  const summaries: Record<typeof SLA_CODES[number], DashboardSlaSummary> = {
    'SLA 1': data.summaries['SLA 1'] ?? ZERO_SUMMARY,
    'SLA 2': data.summaries['SLA 2'] ?? ZERO_SUMMARY,
    'SLA 3': data.summaries['SLA 3'] ?? ZERO_SUMMARY,
    'SLA 4': sla4 ? toSummary(sla4.summary) : ZERO_SUMMARY,
  };
  const rankings: Record<typeof SLA_CODES[number], Ranking> = {
    'SLA 1': data.rankings['SLA 1'] ?? ZERO_RANKING,
    'SLA 2': data.rankings['SLA 2'] ?? ZERO_RANKING,
    'SLA 3': data.rankings['SLA 3'] ?? ZERO_RANKING,
    'SLA 4': sla4 ? rankingFrom4(sla4) : ZERO_RANKING,
  };
  const trends: Record<typeof SLA_CODES[number], TrendPoint[]> = {
    'SLA 1': data.trends['SLA 1'] ?? [],
    'SLA 2': data.trends['SLA 2'] ?? [],
    'SLA 3': data.trends['SLA 3'] ?? [],
    'SLA 4': sla4 ? toTrend(sla4.trend) : [],
  };

  const combinedUnits = (() => {
    if (!sla4) return data.unit_table;
    const map = new Map<string, DashboardUnitRow>();
    for (const row of data.unit_table) map.set(row.unit, { ...row });
    for (const row of sla4.unit_table) {
      const existing = map.get(row.unit) || { unit: row.unit };
      existing.sla4 = toUnitStat(row);
      map.set(row.unit, existing);
    }
    return [...map.values()].filter((row) => !tableUnit || row.unit === tableUnit);
  })();

  const selectedRows = selected === 'SLA 4' ? (sla4?.unit_table.filter((r) => !tableUnit || r.unit === tableUnit).map((r) => ({ unit: r.unit, total: r.total, denominator: r.denominator, on_time: r.on_time, out_of_date: r.out_of_date, incomplete: r.incomplete, percentage: r.percentage })) ?? []) : selected === 'SLA 1' || selected === 'SLA 2' || selected === 'SLA 3' ? (data.unit_table.filter((r) => !tableUnit || r.unit === tableUnit)) : combinedUnits;
  const selectedTrend = trends[activeCode];
  const selectedRanking = rankings[activeCode];

  return (
    <div className="min-h-screen bg-paper text-ink pb-12">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-7 space-y-6">
        <section className="bg-surface border border-rule rounded-sm p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div><h2 className="font-serif text-xl font-semibold">Dashboard Monitoring SLA</h2><p className="text-xs text-slate-muted mt-1">SLA 1 • SLA 2 • SLA 3 • SLA 4 • Raw Excel dipetakan berdasarkan nama header.</p></div>
            <div className="flex gap-2"><label className="cursor-pointer border border-rule px-4 py-2 text-xs font-medium rounded-sm hover:bg-paper">{file ? file.name : 'Pilih Raw Excel'}<input type="file" accept=".xlsx,.xls" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label><button onClick={upload} disabled={loading} className="bg-ink text-white px-4 py-2 text-xs rounded-sm disabled:opacity-50">{loading ? 'Memproses...' : 'Import Raw Excel'}</button><button onClick={() => window.open(exportUrl({ startDate: start, endDate: end }), '_blank')} className="border border-brass text-brass px-4 py-2 text-xs rounded-sm">Export</button></div>
          </div>
        </section>

        {error && <div className="bg-status-badbg border border-status-bad/30 text-status-bad text-sm px-4 py-3 rounded-sm">{error}</div>}

        <section className="bg-surface border border-rule rounded-sm p-5">
          <div className="flex flex-wrap items-end gap-4">
            <div><label className="block text-[11px] font-medium text-slate-muted mb-1">Pilih SLA</label><select value={sla} onChange={(e) => { setSla(e.target.value as SelectedSla); setTableUnit(''); setTrendUnit(''); }} className="border border-rule rounded-sm px-3 py-2 text-sm min-w-48"><option value="ALL">Semua SLA</option><option value="SLA 1">SLA 1</option><option value="SLA 2">SLA 2</option><option value="SLA 3">SLA 3</option><option value="SLA 4">SLA 4</option></select></div>
            <div><label className="block text-[11px] font-medium text-slate-muted mb-1">Dari Tgl Registrasi</label><input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="border border-rule rounded-sm px-3 py-2 text-sm" /></div>
            <div><label className="block text-[11px] font-medium text-slate-muted mb-1">Sampai Tgl Registrasi</label><input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="border border-rule rounded-sm px-3 py-2 text-sm" /></div>
            <button onClick={resetFilters} className="text-xs text-brass font-medium pb-2">Reset Filter</button>
            <span className="text-[11px] text-slate-muted pb-2">{sla === 'ALL' ? 'Dashboard menampilkan seluruh SLA yang tersedia.' : `Menampilkan dashboard ${sla}.`}</span>
          </div>
          {sla4 && <p className="text-[11px] text-slate-muted mt-3">SLA 4 • Kalender terbaru dipakai dari database saat perhitungan. SLA 3 dihitung pada import yang sama.</p>}
        </section>

        {sla === 'ALL' ? (
          <>
            <section><h3 className="font-serif text-lg font-semibold mb-3">Akumulasi Capaian SLA</h3><div className="grid md:grid-cols-3 gap-4">{SLA_CODES.map((code) => <SummaryCard key={code} label={`Capaian ${code}`} value={`${summaries[code].percentage}%`} sub={`On Time / Denominator: ${fmt(summaries[code].on_time)} / ${fmt(summaries[code].denominator)}`} dark />)}</div></section>
            <UnitTable rows={combinedUnits} sla="ALL" unit={tableUnit} setUnit={setTableUnit} all availableUnits={[...new Set([...(data.available_units ?? []), ...(sla4?.available_units ?? [])])]} />
          </>
        ) : (
          <>
            <section className="grid md:grid-cols-4 gap-4"><SummaryCard label={`Capaian ${selected}`} value={`${summaries[activeCode].percentage}%`} sub={`On Time / Denominator: ${fmt(summaries[activeCode].on_time)} / ${fmt(summaries[activeCode].denominator)}`} dark /><SummaryCard label="Total Arsip" value={fmt(summaries[activeCode].total_records)} /><SummaryCard label="On Time" value={fmt(summaries[activeCode].on_time)} tone="good" /><SummaryCard label="Out of Date" value={fmt(summaries[activeCode].out_of_date)} tone="bad" /></section>
            <StatusSync sla={activeCode} summary={summaries[activeCode]} />
            <UnitTable rows={selectedRows} sla={activeCode} unit={tableUnit} setUnit={setTableUnit} all={false} availableUnits={activeCode === 'SLA 4' ? (sla4?.available_units ?? []) : (data.available_units ?? [])} />
            <UnitAchievementChart rows={selectedRows} />
            <RankingPanels top5={selectedRanking.top5} bottom5={selectedRanking.bottom5} title={activeCode} />
            <TrendFilter sla={activeCode} unit={trendUnit} setUnit={setTrendUnit} units={selected === 'SLA 4' ? (sla4?.available_units ?? []) : data.available_units} />
            <TrendChart points={selectedTrend} title={activeCode} />
          </>
        )}
      </main>
    </div>
  );
}
