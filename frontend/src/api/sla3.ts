import axios from 'axios';

export interface SLA3UnitSummary {
  unit: string;
  total: number;
  denominator: number;
  on_time: number;
  out_of_date: number;
  incomplete: number;
  percentage: number;
}

export interface SLA3DashboardPayload {
  summary: {
    total_records: number;
    denominator: number;
    on_time: number;
    out_of_date: number;
    incomplete: number;
    percentage: number;
    ontime_pct: number;
    ood_pct: number;
    inc_pct: number;
  };
  unit_table: SLA3UnitSummary[];
  ranking: {
    top5: any[];
    bottom5: any[];
  };
  trend: Array<{
    tanggal: string;
    jumlah_arsip: number;
    jumlah_berhasil: number;
    persentase: number;
  }>;
  available_units: string[];
}

const api = axios.create({
  baseURL: '/api',
});

export async function fetchSLA3Dashboard(params?: { startDate?: string; endDate?: string; trendUnit?: string }): Promise<SLA3DashboardPayload> {
  // Arahkan ke endpoint monitoring dashboard utama yang menangani SLA 3 dengan benar
  const res = await api.get<any>('/monitoring/dashboard', { 
    params: { 
      sla: 'SLA 3', 
      start_date: params?.startDate, 
      end_date: params?.endDate, 
      trend_unit: params?.trendUnit 
    } 
  });
  
  // Mapping struktur respons agar sesuai dengan interface SLA3DashboardPayload
  const data = res.data;
  const summary = data.summaries?.['SLA 3'] || {
    total_records: 0, denominator: 0, on_time: 0, out_of_date: 0, incomplete: 0,
    percentage: 0, ontime_pct: 0, ood_pct: 0, inc_pct: 0
  };
  const unitTable = data.unit_table || [];
  const ranking = data.ranking || { top5: [], bottom5: [] };
  const trend = data.trend || [];

  return {
    summary: summary,
    unit_table: unitTable,
    ranking: ranking,
    trend: trend,
    available_units: data.available_units || [],
  };
}

export async function importSLA3(file: File) {
  const form = new FormData();
  form.append('file', file);
  // Menggunakan rute import utama yang memproses SLA 1, 2, dan 3 sekaligus
  const res = await api.post('/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}