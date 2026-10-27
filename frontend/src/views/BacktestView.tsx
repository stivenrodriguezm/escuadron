import { useEffect, useState } from "react";
import { Check, FlaskConical } from "lucide-react";
import { EquityChart } from "../components/EquityChart";
import { PageHeader } from "../components/Layout";
import { fmtPct, fmtUsd, tone } from "../components/format";
import { api } from "../hooks/api";
import type { BacktestJob, BacktestRequest, BacktestResult } from "../types";

const parseList = (s: string) => s.split(",").map((x) => Number(x.trim())).filter((x) => Number.isFinite(x) && x > 0);
const isoDaysAgo = (d: number) => new Date(Date.now() - d * 86_400_000).toISOString().slice(0, 10);

export function BacktestView() {
  const [form, setForm] = useState({
    symbol: "DOGEUSDT", interval: "4h", start: isoDaysAgo(365), end: isoDaysAgo(0), capital: "10000",
    thresholds: "60, 75, 85", sl: "1.0, 2.0", tp: "5.0, 8.0",
  });
  const [job, setJob] = useState<BacktestJob | null>(null);
  const [selected, setSelected] = useState<BacktestResult | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!job || job.status !== "RUNNING") return;
    const id = setInterval(async () => {
      const next = await api.get<BacktestJob>(`/api/backtest/${job.job_id}`);
      setJob(next);
      if (next.status !== "RUNNING") setSelected(next.results[0] ?? null);
    }, 1500);
    return () => clearInterval(id);
  }, [job]);

  const run = async () => {
    setNotice(null);
    const body: BacktestRequest = {
      symbol: form.symbol, interval: form.interval, start: form.start, end: form.end,
      initial_capital: Number(form.capital), score_thresholds: parseList(form.thresholds),
      sl_atr_mults: parseList(form.sl), tp_atr_mults: parseList(form.tp),
    };
    setSelected(null);
    setJob(await api.post<BacktestJob>("/api/backtest/run", body));
  };

  const apply = async (r: BacktestResult) => {
    await api.post("/api/backtest/apply", {
      symbol: r.symbol, interval: r.interval, setup_score_threshold: r.score_threshold,
      sl_atr_mult: r.sl_atr_mult, tp_atr_mult: r.tp_atr_mult,
    });
    setNotice(`${r.symbol} ${r.interval} aplicado en vivo: umbral ${r.score_threshold}, SL ${r.sl_atr_mult}×ATR, TP ${r.tp_atr_mult}×ATR`);
  };

  const field = (key: keyof typeof form, label: string, type = "text") => (
    <label className="block">
      <span className="label">{label}</span>
      <input type={type} className="input num mt-1.5" value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
    </label>
  );

  return (
    <>
      <PageHeader title="Calibración (Backtest)" subtitle="Motor headless sin sesgo de futuro · misma lógica Quant + Guardián + fricción real" />
      <div className="space-y-5 px-8 py-6">
        <section className="panel p-5">
          <div className="grid grid-cols-8 items-end gap-3">
            <label className="block">
              <span className="label">Par</span>
              <select className="input mt-1.5" value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })}>
                {["DOGEUSDT", "XRPUSDT", "SOLUSDT", "BTCUSDT", "ETHUSDT", "BNBUSDT"].map((s) => <option key={s}>{s}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="label">Intervalo</span>
              <select className="input mt-1.5" value={form.interval} onChange={(e) => setForm({ ...form, interval: e.target.value })}>
                {["5m", "15m", "1h", "4h"].map((s) => <option key={s}>{s}</option>)}
              </select>
            </label>
            {field("start", "Desde", "date")}
            {field("end", "Hasta", "date")}
            {field("capital", "Capital")}
            {field("thresholds", "Umbrales score")}
            {field("sl", "SL × ATR")}
            {field("tp", "TP × ATR")}
          </div>
          <div className="mt-4 flex items-center gap-3">
            <button className="btn btn-primary" onClick={run} disabled={job?.status === "RUNNING"}>
              <FlaskConical size={13} /> {job?.status === "RUNNING" ? "Calibrando…" : "Lanzar calibración"}
            </button>
            {job && <span className={`text-[12px] ${job.status === "ERROR" ? "text-loss" : "text-ink-faint"}`}>
              {job.status === "RUNNING" ? "Descargando datos y simulando en segundo plano…" : `${job.message} · ${job.candles.toLocaleString("en-US")} velas`}
            </span>}
            {notice && <span className="flex items-center gap-1 text-[12px] text-gain"><Check size={13} />{notice}</span>}
          </div>
        </section>

        {job && job.results.length > 0 && (
          <div className="grid gap-5" style={{ gridTemplateColumns: "58fr 42fr" }}>
            <section className="panel">
              <div className="border-b border-line px-5 py-3.5 text-[13px] font-medium">Resultados (ordenados por Sharpe)</div>
              <div className="max-h-[440px] overflow-auto">
                <table className="data">
                  <thead><tr><th>Umbral</th><th>SL</th><th>TP</th><th>Rend.</th><th>Trades</th><th>Win</th><th>Sharpe</th><th>Max DD</th><th>Comisiones</th><th /></tr></thead>
                  <tbody>
                    {job.results.map((r, i) => (
                      <tr key={i} onClick={() => setSelected(r)} className={`cursor-pointer ${selected === r ? "bg-panel2" : "hover:bg-panel2/60"}`}>
                        <td className="num">{r.score_threshold}</td>
                        <td className="num">{r.sl_atr_mult}</td>
                        <td className="num">{r.tp_atr_mult}</td>
                        <td className={`num ${tone(r.compound_return_pct)}`}>{fmtPct(r.compound_return_pct)}</td>
                        <td className="num">{r.trades}</td>
                        <td className="num">{r.win_rate_pct.toFixed(1)}%</td>
                        <td className="num">{r.sharpe_ratio.toFixed(2)}</td>
                        <td className="num">{r.max_drawdown_pct.toFixed(2)}%</td>
                        <td className="num">{fmtUsd(r.total_fees)}</td>
                        <td><button className="btn px-2 py-0.5 text-[11px]" onClick={(e) => { e.stopPropagation(); void apply(r); }}>Aplicar</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            <section className="panel">
              <div className="border-b border-line px-5 py-3.5 text-[13px] font-medium">Curva de capital simulada</div>
              {selected && (
                <div className="px-3 py-4">
                  <EquityChart points={selected.equity_curve.map(([ts, equity]) => ({ ts, equity }))} baseline={selected.initial_capital} height={300} />
                  <div className="num mt-3 grid grid-cols-3 gap-2 px-3 text-[12px] text-ink-dim">
                    <div>Final <span className="text-ink">{fmtUsd(selected.final_equity)}</span></div>
                    <div>Slippage <span className="text-ink">{fmtUsd(selected.total_slippage)}</span></div>
                    <div>Funding <span className="text-ink">{fmtUsd(selected.total_funding)}</span></div>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </>
  );
}
