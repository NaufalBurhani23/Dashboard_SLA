export type SLAStatus = 'ON TIME' | 'OUT OF DATE' | 'INCOMPLETE';
export interface SLARecord {
  id: number; nomor_registrasi: string|null; nama_dokumen:string|null; unit:string|null; sumber:string|null;
  status_registrasi:string|null; status_inisiasi:string|null; posisi_data:string|null; format_arsip:string|null; document_type:string|null;
  sla1a_result:string|null; sla1b_result:string|null; sla1_decision_source:string|null; sla1_manual_rule:string|null; sla1_working_days:number|null;
  sla2a_result:string|null; sla2b_result:string|null; sla2_final_result:string|null; sla2_manual_result:string|null;
  sla2_decision_source:string|null; sla2_manual_rule:string|null; sla2_working_days:number|null; sla2a_working_days:number|null; sla2b_working_days:number|null;
  sla2_flow_stage:string|null; sla2_reason:string|null;
  registration_timestamp:string|null; verification_uf_timestamp:string|null; verification_uu_timestamp:string|null; verification_timestamp:string|null;
  registration_2_timestamp:string|null; verification_2_timestamp:string|null; status:SLAStatus; incomplete_reason:string|null;
  holiday_calendar_version:string|null; reporting_period:string|null;
}
export interface UnitSummary { unit:string; denominator:number; on_time:number; late:number; percentage:number; tindak_lanjut:string; }
export interface Ranking { top5:UnitSummary[]; bottom5:UnitSummary[]; }
export interface Accumulation { total_records:number; denominator:number; on_time:number; out_of_date:number; incomplete:number; percentage:number; ontime_pct:number; ood_pct:number; inc_pct:number; }
export interface TrendPoint { tanggal:string; jumlah_arsip:number; jumlah_berhasil:number; persentase:number|null; }
export interface MonitoringFilters { startDate?:string; endDate?:string; unit?:string; status?:string; }
export interface HolidayItem { id:number; date:string; description:string; version:string; }
