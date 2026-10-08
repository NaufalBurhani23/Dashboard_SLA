import axios from 'axios';

export const API_SLA4 = 'http://localhost:8000/api/sla4';

export interface SLA4Summary {
  total: number;
  yes: number;
  no: number;
  na: number;
  denominator: number;
  percentage: number;
}

export interface SLA4RecordRow {
  id: number;
  nomor_registrasi: string | null;
  unit: string | null;
  unit_type: string | null;
  kawasan: string | null;
  sumber: string | null;
  status_registrasi: string | null;
  format_arsip: string | null;
  document_type: string | null;
  tanggal_registrasi: string | null;
  tanggal_jadwal_penjemputan: string | null;
  tanggal_penjemputan_dokumen: string | null;
  sla4a_result: string;
  sla4a_working_days: number | null;
  sla4a_reason: string | null;
  sla4b_result: string;
  sla4b_working_days: number | null;
  sla4b_reason: string | null;
  sla4_final_result: string;
  sla4_decision_source: string | null;
  sla4_reason: string | null;
  sla4_target_days: number | null;
  sla4_anomaly: string | null;
  holiday_calendar_versions: Record<string, string>;
}

export interface SLA4UnitSummary {
  unit: string;
  total: number;
  denominator: number;
  on_time: number;
  out_of_date: number;
  late: number;
  incomplete: number;
  percentage: number;
  tindak_lanjut: string;
}

export interface SLA4DashboardPayload {
  selected_sla: 'SLA 4';
  available_units: string[];
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
  unit_table: SLA4UnitSummary[];
  ranking: { top5: SLA4UnitSummary[]; bottom5: SLA4UnitSummary[] };
  trend: { tanggal: string; jumlah_arsip: number; jumlah_berhasil: number; persentase: number | null }[];
}

export interface UnitAreaItem {
  id: number;
  unit_name: string;
  unit_type: 'Pusat' | 'Pendukung';
  kawasan: 'Dalam Kawasan' | 'Luar Kawasan';
  target_days: number | null;
  active: boolean;
  valid_from: string | null;
  valid_to: string | null;
}

export interface HolidayItemSLA4 {
  id: number;
  date: string;
  description: string;
  version: string;
}

export async function importSLA4(file: File) {
  const form = new FormData();
  form.append('file', file);
  return (await axios.post(`${API_SLA4}/import`, form, { timeout: 300000 })).data as {
    message: string;
    records: number;
    period: string;
    file_name: string;
    final: Record<'Yes' | 'No' | 'N/A', number>;
    sla4a: Record<'Yes' | 'No' | 'N/A', number>;
    sla4b: Record<'Yes' | 'No' | 'N/A', number>;
    unit_mapping_missing: number;
  };
}

export async function fetchSLA4Dashboard(params: { startDate?: string; endDate?: string; tableUnit?: string; trendUnit?: string } = {}) {
  return (await axios.get(`${API_SLA4}/dashboard`, {
    params: {
      start_date: params.startDate || undefined,
      end_date: params.endDate || undefined,
      table_unit: params.tableUnit || undefined,
      trend_unit: params.trendUnit || undefined,
    },
  })).data as SLA4DashboardPayload;
}

export async function fetchSLA4Summary() {
  return (await axios.get(`${API_SLA4}/summary`)).data as SLA4Summary;
}

export async function fetchSLA4Records(params: { limit?: number; offset?: number; result?: string; unit?: string } = {}) {
  return (await axios.get(`${API_SLA4}/records`, { params })).data as {
    total: number;
    offset: number;
    limit: number;
    data: SLA4RecordRow[];
  };
}

export async function fetchUnits(activeOnly = true) {
  return (await axios.get(`${API_SLA4}/units`, { params: { active_only: activeOnly } })).data as {
    count: number;
    items: UnitAreaItem[];
  };
}

export async function addUnit(payload: {
  unit_name: string;
  unit_type: 'Pusat' | 'Pendukung';
  kawasan: 'Dalam Kawasan' | 'Luar Kawasan';
  active?: boolean;
  valid_from?: string;
  valid_to?: string;
}) {
  return (await axios.post(`${API_SLA4}/units`, payload)).data;
}

export async function updateUnit(id: number, payload: Partial<Parameters<typeof addUnit>[0]>) {
  return (await axios.put(`${API_SLA4}/units/${id}`, payload)).data;
}

export async function deleteUnit(id: number) {
  return (await axios.delete(`${API_SLA4}/units/${id}`)).data;
}

export async function fetchHolidaysSLA4(year = 2026) {
  return (await axios.get(`${API_SLA4}/holidays`, { params: { year } })).data as {
    year: number;
    version: string | null;
    count: number;
    items: HolidayItemSLA4[];
  };
}

export async function addHolidaySLA4(date: string, description: string) {
  return (await axios.post(`${API_SLA4}/holidays`, { date, description })).data;
}

export async function updateHolidaySLA4(id: number, date: string, description: string) {
  return (await axios.put(`${API_SLA4}/holidays/${id}`, { date, description })).data;
}

export async function deleteHolidaySLA4(id: number) {
  return (await axios.delete(`${API_SLA4}/holidays/${id}`)).data;
}

export async function importHolidaysSLA4(file: File, year = 2026) {
  const form = new FormData();
  form.append('file', file);
  return (await axios.post(`${API_SLA4}/holidays/import`, form, { params: { year } })).data;
}

export async function previewHolidaysSLA4(startDate: string, endDate: string) {
  return (await axios.get(`${API_SLA4}/holidays/preview`, {
    params: { start_date: startDate, end_date: endDate },
  })).data;
}
