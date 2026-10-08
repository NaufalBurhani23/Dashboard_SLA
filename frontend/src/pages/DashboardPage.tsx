import { useCallback, useEffect, useState } from 'react';
import Header from '../components/Header';
import RankingPanels from '../components/RankingPanels';
import TrendChart from '../components/TrendChart';
import UnitAchievementChart from '../components/UnitAchievementChart';
import { exportUrl, fetchDashboard, importExcel } from '../api/client';
import type { DashboardPayload, DashboardSlaSummary, DashboardUnitRow } from '../api/client';

const ZERO_SUMMARY: DashboardSlaSummary = {
  total_records: 0,
  denominator: 0,
  on_time: 0,
  out_of_date: 0,
  incomplete: 0,
  percentage: 0,
  ontime_pct: 0,
  ood_pct: 0,
  inc_pct: 0,
};

const EMPTY: DashboardPayload = {
  selected_sla: 'ALL',
  available_units: [],
  summaries: { 'SLA 1': ZERO_SUMMARY, 'SLA 2': ZERO_SUMMARY },
  unit_table: [],
  ranking: { top5: [], bottom5: [] },
  rankings: { 'SLA 1': { top5: [], bottom5: [] }, 'SLA 2': { top5: [], bottom5: [] } },
  trend: [],
  trends: { 'SLA 1': [], 'SLA 2': [] },
  trend_sla: 'SLA 1',
};

const fmt = (n: number) => new Intl.NumberFormat('id-ID').format(n || 0);

type SelectedSla = 'ALL' | 'SLA 1' | 'SLA 2';

type SummaryCardProps = {
  label: string;
  value: string;
  sub?: string;
  dark?: boolean;
  tone?: 'good' | 'bad' | 'warn';
};

function SummaryCard({ label, value, sub, dark = false, tone }: SummaryCardProps) {
  const toneClass = tone === 'good'
    ? 'text-status-good'
    : tone === 'bad'
      ? 'text-status-bad'
      : tone === 'warn'
        ? 'text-status-warn'
        : '';

  return (
    <div className={dark ? 'bg-ink text-white rounded-sm p-5' : 'bg-surface border border-rule rounded-sm p-5'}>
      <p className={dark ? 'text-xs text-white/60' : 'text-xs text-slate-muted'}>{label}</p>
      <p className={`text-3xl font-bold mt-2 ${dark ? '' : toneClass}`}>{value}</p>
      {sub && <p className={dark ? 'text-xs text-white/60 mt-2' : 'text-xs text-slate-muted mt-2'}>{sub}</p>}
    </div>
  );
}

function StatusSync({ sla, summary }: { sla: 'SLA 1' | 'SLA 2'; summary: DashboardSlaSummary }) {
  return (
    <section className="bg-surface border border-rule rounded-sm p-5">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h3 className="font-serif text-lg font-semibold">Status Sinkronisasi Perhitungan {sla}</h3>
        <span className="text-xs text-slate-muted">Total: {fmt(summary.total_records)} arsip</span>
      </div>
      <p className="text-xs text-slate-muted mb-4">
        Keterangan: <b>ON TIME</b> = Yes (memenuhi SLA) • <b>OUT OF DATE</b> = No (tidak memenuhi SLA) • <b>INCOMPLETE</b> = N/A (data belum lengkap / belum dapat dihitung).
      </p>
      <div className="grid md:grid-cols-4 gap-3">
        <div className="border border-rule rounded-sm p-4">
          <p className="text-[11px] text-slate-muted">TOTAL ARSIP</p>
          <p className="text-2xl font-bold mt-1">{fmt(summary.total_records)}</p>
        </div>
        <div className="border border-status-good/30 bg-status-goodbg rounded-sm p-4">
          <p className="text-[11px] text-status-good">ON TIME</p>
          <p className="text-2xl font-bold mt-1 text-status-good">{fmt(summary.on_time)}</p>
          <p className="text-[11px] text-status-good">{summary.ontime_pct}%</p>
        </div>
        <div className="border border-status-bad/30 bg-status-badbg rounded-sm p-4">
          <p className="text-[11px] text-status-bad">OUT OF DATE</p>
          <p className="text-2xl font-bold mt-1 text-status-bad">{fmt(summary.out_of_date)}</p>
          <p className="text-[11px] text-status-bad">{summary.ood_pct}%</p>
        </div>
        <div className="border border-status-warn/30 bg-status-warnbg rounded-sm p-4">
          <p className="text-[11px] text-status-warn">INCOMPLETE</p>
          <p className="text-2xl font-bold mt-1 text-status-warn">{fmt(summary.incomplete)}</p>
          <p className="text-[11px] text-status-warn">{summary.inc_pct}%</p>
        </div>
      </div>
    </section>
  );
}

function UnitTable({
  rows,
  sla,
  unit,
  setUnit,
  all,
}: {
  rows: DashboardUnitRow[];
  sla: SelectedSla;
  unit: string;
  setUnit: (value: string) => void;
  all: boolean;
}) {
  const options = [...new Set(rows.map((row) => row.unit))].sort((a, b) => a.localeCompare(b));

  return (
    <section className="bg-surface border border-rule rounded-sm p-5">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-4">
        <div>
          <h3 className="font-serif text-lg font-semibold">Capaian SLA per Unit</h3>
          <p className="text-xs text-slate-muted mt-1">
            {all ? 'Menampilkan capaian SLA 1 dan SLA 2 per unit.' : `Menampilkan capaian ${sla} per unit.`}
          </p>
        </div>
        <div>
          <label className="block text-[11px] font-medium text-slate-muted mb-1">Unit yang ditampilkan</label>
          <select
            value={unit}
            onChange={(event) => setUnit(event.target.value)}
            className="border border-rule rounded-sm px-3 py-2 text-sm min-w-56"
          >
            <option value="">Semua Unit</option>
            {options.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </div>
      </div>

      {all ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-y border-rule">
                <th className="text-left px-4 py-3">UNIT</th>
                <th className="text-center px-4 py-3">SLA 1</th>
                <th className="text-center px-4 py-3">SLA 2</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.unit} className="border-b border-rule">
                  <td className="px-4 py-3 font-semibold">{row.unit}</td>
                  <td className="px-4 py-3 text-center">
                    <b>{row.sla1?.percentage ?? 0}%</b>
                    <div className="text-xs text-slate-muted">({fmt(row.sla1?.on_time ?? 0)}/{fmt(row.sla1?.total ?? 0)})</div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <b>{row.sla2?.percentage ?? 0}%</b>
                    <div className="text-xs text-slate-muted">({fmt(row.sla2?.on_time ?? 0)}/{fmt(row.sla2?.total ?? 0)})</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-y border-rule">
                <th className="text-left px-4 py-3">UNIT</th>
                <th className="text-center px-4 py-3">{sla}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.unit} className="border-b border-rule">
                  <td className="px-4 py-3 font-semibold">{row.unit}</td>
                  <td className="px-4 py-3 text-center">
                    <b>{row.percentage ?? 0}%</b>
                    <div className="text-xs text-slate-muted">({fmt(row.on_time ?? 0)}/{fmt(row.total ?? 0)})</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rows.length === 0 && <p className="text-sm text-slate-muted py-5">Belum ada data unit untuk filter yang dipilih.</p>}
    </section>
  );
}

function TrendFilter({
  sla,
  unit,
  setUnit,
  units,
}: {
  sla: 'SLA 1' | 'SLA 2';
  unit: string;
  setUnit: (value: string) => void;
  units: string[];
}) {
  return (
    <section className="bg-surface border border-rule rounded-sm p-5">
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-[11px] font-medium text-slate-muted mb-1">Unit Trend {sla}</label>
          <select
            value={unit}
            onChange={(event) => setUnit(event.target.value)}
            className="border border-rule rounded-sm px-3 py-2 text-sm min-w-56"
          >
            <option value="">Semua Unit</option>
            {units.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </div>
        <span className="text-[11px] text-slate-muted pb-2">
          Tren harian hanya ditampilkan untuk {sla}; pilih unit untuk memfilter kedua grafik.
        </span>
      </div>
    </section>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload>(EMPTY);
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
      const result = await fetchDashboard({
        sla,
        startDate: start,
        endDate: end,
        tableUnit,
        trendUnit,
      });
      setData(result);
    } catch (err) {
      console.error(err);
      setError('Gagal mengambil data dashboard. Pastikan backend berjalan.');
    }
  }, [sla, start, end, tableUnit, trendUnit]);

  useEffect(() => {
    void load();
  }, [load]);

  async function upload() {
    if (!file) {
      alert('Pilih raw Excel terlebih dahulu.');
      return;
    }
    setLoading(true);
    try {
      const result = await importExcel(file);
      alert(
        `${result.message}\nHoliday Calendar: ${result.holiday_calendar_version} (${result.holidays_used} hari)\n` +
        `SLA 1 — Yes: ${result.sla1?.Yes ?? '-'}, No: ${result.sla1?.No ?? '-'}, N/A: ${result.sla1?.['N/A'] ?? '-'}\n` +
        `SLA 2 Final — Yes: ${result.sla2?.final?.Yes ?? '-'}, No: ${result.sla2?.final?.No ?? '-'}, N/A: ${result.sla2?.final?.['N/A'] ?? '-'}`,
      );
      await load();
    } catch (err: any) {
      alert('Gagal import: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }

  function resetFilters() {
    setSla('ALL');
    setStart('');
    setEnd('');
    setTableUnit('');
    setTrendUnit('');
  }

  const selected = data.selected_sla;
  const summary = selected === 'ALL' ? null : data.summaries[selected];

  return (
    <div className="min-h-screen bg-paper text-ink pb-12">
      <Header />

      <main className="max-w-7xl mx-auto px-6 py-7 space-y-6">
        <section className="bg-surface border border-rule rounded-sm p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="font-serif text-xl font-semibold">Dashboard Monitoring SLA</h2>
              <p className="text-xs text-slate-muted mt-1">SLA 1 dan SLA 2 • Raw Excel dipetakan berdasarkan nama header.</p>
            </div>
            <div className="flex gap-2">
              <label className="cursor-pointer border border-rule px-4 py-2 text-xs font-medium rounded-sm hover:bg-paper">
                {file ? file.name : 'Pilih Raw Excel'}
                <input type="file" accept=".xlsx,.xls" className="hidden" onChange={(event) => setFile(event.target.files?.[0] || null)} />
              </label>
              <button onClick={upload} disabled={loading} className="bg-ink text-white px-4 py-2 text-xs rounded-sm disabled:opacity-50">
                {loading ? 'Memproses...' : 'Import Raw Excel'}
              </button>
              <button onClick={() => window.open(exportUrl({ startDate: start, endDate: end }), '_blank')} className="border border-brass text-brass px-4 py-2 text-xs rounded-sm">
                Export
              </button>
            </div>
          </div>
        </section>

        {error && <div className="bg-status-badbg border border-status-bad/30 text-status-bad text-sm px-4 py-3 rounded-sm">{error}</div>}

        <section className="bg-surface border border-rule rounded-sm p-5">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-[11px] font-medium text-slate-muted mb-1">Pilih SLA</label>
              <select
                value={sla}
                onChange={(event) => {
                  setSla(event.target.value as SelectedSla);
                  setTableUnit('');
                  setTrendUnit('');
                }}
                className="border border-rule rounded-sm px-3 py-2 text-sm min-w-48"
              >
                <option value="ALL">Semua SLA</option>
                <option value="SLA 1">SLA 1</option>
                <option value="SLA 2">SLA 2</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-muted mb-1">Dari Tgl Registrasi</label>
              <input type="date" value={start} onChange={(event) => setStart(event.target.value)} className="border border-rule rounded-sm px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-muted mb-1">Sampai Tgl Registrasi</label>
              <input type="date" value={end} onChange={(event) => setEnd(event.target.value)} className="border border-rule rounded-sm px-3 py-2 text-sm" />
            </div>
            <button onClick={resetFilters} className="text-xs text-brass font-medium pb-2">Reset Filter</button>
            <span className="text-[11px] text-slate-muted pb-2">
              {selected === 'ALL' ? 'Menampilkan capaian SLA 1 dan SLA 2 per unit.' : `Menampilkan dashboard khusus ${selected}.`}
            </span>
          </div>
        </section>

        {selected === 'ALL' ? (
          <>
            <section>
              <h3 className="font-serif text-lg font-semibold mb-3">Akumulasi Capaian SLA</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <SummaryCard
                  label="Capaian SLA 1"
                  value={`${data.summaries['SLA 1'].percentage}%`}
                  sub={`On Time / Total: ${fmt(data.summaries['SLA 1'].on_time)} / ${fmt(data.summaries['SLA 1'].total_records)}`}
                  dark
                />
                <SummaryCard
                  label="Capaian SLA 2"
                  value={`${data.summaries['SLA 2'].percentage}%`}
                  sub={`On Time / Total: ${fmt(data.summaries['SLA 2'].on_time)} / ${fmt(data.summaries['SLA 2'].total_records)}`}
                  dark
                />
              </div>
            </section>
            <UnitTable rows={data.unit_table} sla="ALL" unit={tableUnit} setUnit={setTableUnit} all />
          </>
        ) : (
          <>
            <section className="grid md:grid-cols-4 gap-4">
              <SummaryCard
                label={`Capaian ${selected}`}
                value={`${summary?.percentage ?? 0}%`}
                sub={`On Time / Total: ${fmt(summary?.on_time ?? 0)} / ${fmt(summary?.total_records ?? 0)}`}
                dark
              />
              <SummaryCard label="Total Arsip" value={fmt(summary?.total_records ?? 0)} />
              <SummaryCard label="On Time" value={fmt(summary?.on_time ?? 0)} tone="good" />
              <SummaryCard label="Out of Date" value={fmt(summary?.out_of_date ?? 0)} tone="bad" />
            </section>

            <StatusSync sla={selected} summary={summary || ZERO_SUMMARY} />
            <UnitTable rows={data.unit_table} sla={selected} unit={tableUnit} setUnit={setTableUnit} all={false} />
            <UnitAchievementChart rows={data.unit_table} />
            <RankingPanels top5={data.ranking.top5} bottom5={data.ranking.bottom5} title={selected} />
            <TrendFilter sla={selected} unit={trendUnit} setUnit={setTrendUnit} units={data.available_units} />
            <TrendChart points={data.trend} title={selected} />
          </>
        )}
      </main>
    </div>
  );
}
