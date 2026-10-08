import axios from 'axios';
import type { SLARecord, UnitSummary, Accumulation, Ranking, TrendPoint, MonitoringFilters, HolidayItem } from '../types';
export const API_BASE = 'http://localhost:8000/api';
function params(filters:MonitoringFilters={}, extra:Record<string,unknown>={}) { return { start_date:filters.startDate||undefined,end_date:filters.endDate||undefined,unit:filters.unit||undefined,status:filters.status||undefined,...extra }; }
export async function fetchSummary(filters:MonitoringFilters={}) { const r=await axios.get(`${API_BASE}/monitoring/summary`,{params:params(filters)}); return r.data as {sla:string;accumulation:Accumulation;unit_summary:UnitSummary[];ranking:Ranking}; }
export async function fetchTrend(filters:MonitoringFilters={}) { const r=await axios.get(`${API_BASE}/monitoring/trend`,{params:params(filters)}); return r.data as {points:TrendPoint[]}; }
export async function fetchDashboard(filters:{sla:string;startDate?:string;endDate?:string;tableUnit?:string;trendUnit?:string}) { const r=await axios.get(`${API_BASE}/monitoring/dashboard`,{params:{sla:filters.sla,start_date:filters.startDate||undefined,end_date:filters.endDate||undefined,table_unit:filters.tableUnit||undefined,trend_unit:filters.trendUnit||undefined}}); return r.data as DashboardPayload; }
export async function importExcel(file:File){const f=new FormData();f.append('file',file);return (await axios.post(`${API_BASE}/import`,f,{timeout:300000})).data;}
export async function fetchTraceability(filters:MonitoringFilters={},page=1,limit=150){return (await axios.get(`${API_BASE}/monitoring/traceability`,{params:params(filters,{page,limit})})).data as {total:number;page:number;limit:number;units:string[];data:SLARecord[]};}
export async function deleteRecord(id:number){await axios.delete(`${API_BASE}/monitoring/${id}`);}
export function exportUrl(filters:MonitoringFilters={}){const p=new URLSearchParams();if(filters.startDate)p.set('start_date',filters.startDate);if(filters.endDate)p.set('end_date',filters.endDate);if(filters.unit)p.set('unit',filters.unit);if(filters.status)p.set('status',filters.status);return `${API_BASE}/export${p.toString()?`?${p}`:''}`;}
export async function fetchHolidays(year=2026){return (await axios.get(`${API_BASE}/holidays`,{params:{year}})).data as {year:number;version:string|null;count:number;items:HolidayItem[]};}
export async function addHoliday(date:string,description:string,version?:string){return (await axios.post(`${API_BASE}/holidays`,{date,description,version})).data;}
export async function deleteHoliday(id:number){await axios.delete(`${API_BASE}/holidays/${id}`);}
export async function importHolidays(file:File,year=2026){const f=new FormData();f.append('file',file);return (await axios.post(`${API_BASE}/holidays/import`,f,{params:{year}})).data;}
export async function previewWorkdays(startDate:string,endDate:string){return (await axios.get(`${API_BASE}/holidays/preview`,{params:{start_date:startDate,end_date:endDate}})).data;}

export interface DashboardSlaSummary extends Accumulation { }
export interface DashboardUnitStat { total:number; denominator:number; on_time:number; out_of_date:number; incomplete:number; percentage:number; }
export interface DashboardUnitRow { unit:string; sla1?:DashboardUnitStat; sla2?:DashboardUnitStat; sla4?:DashboardUnitStat; total?:number; denominator?:number; on_time?:number; out_of_date?:number; incomplete?:number; percentage?:number; }
export interface DashboardPayload { selected_sla:'ALL'|'SLA 1'|'SLA 2'|'SLA 4'; available_units:string[]; summaries:Record<'SLA 1'|'SLA 2',DashboardSlaSummary>; unit_table:DashboardUnitRow[]; ranking:Ranking; rankings:Record<'SLA 1'|'SLA 2',Ranking>; trend:TrendPoint[]; trends:Record<'SLA 1'|'SLA 2',TrendPoint[]>; trend_sla:'SLA 1'|'SLA 2'; }

export interface UnifiedDashboardPayload extends DashboardPayload { summaries: Record<'SLA 1'|'SLA 2'|'SLA 4', DashboardSlaSummary>; rankings: Record<'SLA 1'|'SLA 2'|'SLA 4', Ranking>; trends: Record<'SLA 1'|'SLA 2'|'SLA 4', TrendPoint[]>; trend_sla:'SLA 1'|'SLA 2'|'SLA 4'; }
