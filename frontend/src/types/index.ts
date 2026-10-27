export type Side = "LONG" | "SHORT";
export type ExecutionMode = "PAPER_LIVE" | "TESTNET" | "LIVE";

export interface PortfolioState {
  initial_capital: number;
  current_compound_equity: number;
  available_balance: number;
  allocated_margin: number;
  total_fees_paid: number;
  total_slippage_cost: number;
  total_funding_paid: number;
  high_water_mark: number;
  max_drawdown_pct: number;
  is_running: boolean;
  started_at: string;
  updated_at: string;
}

export interface PortfolioMetrics {
  equity: number;
  equity_with_unrealized: number;
  unrealized_pnl: number;
  total_return_pct: number;
  daily_pnl: number;
  daily_return_pct: number;
  daily_friction: number;
  sharpe_ratio: number;
  win_rate_pct: number;
  trades_count: number;
  exposure_pct: number;
  risk_committed_pct: number;
  max_drawdown_pct: number;
}

export interface Position {
  id: number;
  symbol: string;
  side: Side;
  entry_price: number;
  current_price: number;
  quantity: number;
  stop_loss: number;
  take_profit: number;
  initial_stop_loss: number;
  unrealized_pnl: number;
  accumulated_funding: number;
  entry_fee: number;
  entry_slippage: number;
  margin: number;
  notional: number;
  breakeven_moved: boolean;
  opened_at: string;
}

export interface PendingOrder {
  order_id: string;
  symbol: string;
  side: Side;
  quantity: number;
  price: number;
}

export interface SymbolStrategy {
  interval: string;
  setup_score_threshold: number;
  sl_atr_mult: number;
  tp_atr_mult: number;
}

export interface PortfolioPayload {
  state: PortfolioState;
  metrics: PortfolioMetrics;
  positions: Position[];
  pending_orders: PendingOrder[];
  running: boolean;
  mode: ExecutionMode;
  strategy: Record<string, SymbolStrategy>;
  limits: { max_risk_per_trade: number; max_portfolio_risk: number; max_daily_drawdown: number };
}

export interface AgentStatus {
  id: string;
  name: string;
  status: string;
  metric: string;
  tokens_used: number;
  last_update: string | null;
  deterministic: boolean;
  model: string | null;
}

export interface ConsensusLog {
  id: number;
  timestamp: string;
  agent_id: string;
  status: string;
  message: string;
  token_cost: number;
}

export interface MarketInfo {
  price: number;
  funding_rate: number;
  spread_pct: number | null;
  imbalance: number | null;
}

export interface TelemetryMessage extends PortfolioPayload {
  type: "telemetry";
  agents: AgentStatus[];
  logs: ConsensusLog[];
  stream: { connected: boolean; markets: Record<string, MarketInfo> };
  llm_enabled: boolean;
}

export interface EquityPoint {
  t: string;
  equity: number;
}

export interface Trade {
  id: number;
  symbol: string;
  side: Side;
  quantity: number;
  entry_price: number;
  exit_price: number;
  gross_pnl: number;
  entry_fee: number;
  exit_fee: number;
  funding_paid: number;
  slippage_cost: number;
  net_pnl: number;
  equity_after: number;
  exit_reason: string;
  opened_at: string;
  closed_at: string;
}

export interface BacktestRequest {
  symbol: string;
  interval: string;
  start: string;
  end: string;
  initial_capital: number;
  score_thresholds: number[];
  sl_atr_mults: number[];
  tp_atr_mults: number[];
}

export interface BacktestResult {
  sl_atr_mult: number;
  tp_atr_mult: number;
  symbol: string;
  interval: string;
  score_threshold: number;
  initial_capital: number;
  final_equity: number;
  compound_return_pct: number;
  trades: number;
  win_rate_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  total_fees: number;
  total_slippage: number;
  total_funding: number;
  equity_curve: [number, number][];
}

export interface BacktestJob {
  job_id: string;
  status: "RUNNING" | "DONE" | "ERROR";
  request: BacktestRequest;
  message: string;
  started_at: string;
  finished_at: string | null;
  candles: number;
  results: BacktestResult[];
}

export interface SettingsView {
  execution_mode: ExecutionMode;
  symbols: string[];
  llm_provider: string;
  llm_enabled: boolean;
  agent_models: Record<string, string>;
  strategist_fallbacks: string[];
  binance_keys: boolean;
  taker_fee: number;
  maker_fee: number;
  latency_ms: number;
  max_risk_per_trade: number;
  max_daily_drawdown: number;
  max_portfolio_risk: number;
  max_leverage: number;
  min_reward_risk: number;
  breakeven_r: number;
  strategy: Record<string, SymbolStrategy>;
}

export type ViewKey = "dashboard" | "agents" | "ledger" | "backtest" | "settings";
