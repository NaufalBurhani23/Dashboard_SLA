import type {UnitSummary} from '../types';

function List({title,items,tone}:{title:string;items:UnitSummary[];tone:'good'|'bad'}){
  const bar=tone==='good'?'bg-status-good':'bg-status-bad';
  const text=tone==='good'?'text-status-good':'text-status-bad';
  return <div className="border border-rule rounded-sm bg-surface p-5 flex-1 min-w-[320px]">
    <h3 className="text-sm font-semibold text-ink mb-4">{title}</h3>
    <div className="space-y-4">
      {items.map(u=><div key={u.unit}>
        <div className="flex justify-between text-sm"><span className="font-semibold">{u.unit}</span><span className={`font-bold ${text}`}>{u.percentage}% <span className="text-xs text-slate-muted">({u.on_time}/{u.denominator})</span></span></div>
        <div className="h-2 bg-rule rounded-full mt-1 overflow-hidden"><div className={`h-full ${bar}`} style={{width:`${Math.min(u.percentage,100)}%`}} /></div>
        <p className="text-[11px] text-slate-muted mt-1">{u.tindak_lanjut}</p>
      </div>)}
      {!items.length&&<p className="text-xs text-slate-muted">Belum ada data.</p>}
    </div>
  </div>
}

export default function RankingPanels({top5,bottom5,title="SLA 1"}:{top5:UnitSummary[];bottom5:UnitSummary[];title?:string}){
  return <div className="flex flex-wrap gap-4"><List title={`Top 5 Capaian ${title}`} items={top5} tone="good"/><List title={`Bottom 5 Capaian ${title}`} items={bottom5} tone="bad"/></div>
}
