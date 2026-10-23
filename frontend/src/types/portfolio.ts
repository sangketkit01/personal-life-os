export type AssetType = 'STOCK' | 'CRYPTO' | 'FUND' | 'OTHER'
export type TransactionType = 'BUY' | 'SELL' | 'DIVIDEND'

export interface PositionSummary {
  shares: number
  avg_cost: number
  total_invested: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  total_realized_pnl: number
  total_dividends: number
  is_active: boolean
  currency?: string
  market_session?: 'REGULAR' | 'PRE' | 'POST' | 'POSTPOST' | 'NIGHT'
  regular_price?: number
  extended_price?: number
  extended_change?: number
  extended_change_pct?: number
  market_value_thb?: number
  market_value_usd?: number
  total_invested_thb?: number
  total_invested_usd?: number
  unrealized_pnl_thb?: number
  unrealized_pnl_usd?: number
  current_price_thb?: number
  current_price_usd?: number
  avg_cost_thb?: number
  avg_cost_usd?: number
  total_realized_pnl_thb?: number
  total_realized_pnl_usd?: number
  total_dividends_thb?: number
  total_dividends_usd?: number
}

export interface StockTransaction {
  id: string
  holding?: string
  holding_ticker?: string
  holding_currency?: string
  portfolio?: string
  portfolio_name?: string
  ticker?: string
  transaction_type: TransactionType
  shares: number
  price_per_share: number
  fee: number
  currency?: string
  executed_at: string
  notes?: string
  created_at?: string
}

export interface InvestmentPortfolio {
  id: string
  name: string
  description: string
  currency: 'THB' | 'USD'
  color: string
  is_default: boolean
  holdings_count: number
  created_at: string
  updated_at: string
}

export interface CreatePortfolioPayload {
  name: string
  description?: string
  currency?: 'THB' | 'USD'
  color?: string
}

export interface MarketAssetSearchResult {
  ticker: string
  name: string
  asset_type: AssetType
  currency: 'THB' | 'USD'
  exchange: string
  price?: number | null
  change_amount?: number | null
  change_pct?: number | null
}

export interface StockHolding {
  id: string
  portfolio?: string
  portfolio_name?: string
  ticker: string
  name: string
  asset_type: AssetType
  currency: string
  notes: string
  is_held?: boolean
  is_watchlisted?: boolean
  all_holdings?: Array<{
    id: string
    portfolio_id: string
    portfolio_name: string
  }>
  position: PositionSummary
  recent_transactions: StockTransaction[]
  created_at: string
  updated_at: string
}

export interface StockWatchlistItem {
  id: string
  ticker: string
  name: string
  asset_type: AssetType
  currency: string
  notes?: string
  current_price?: number
  change_amount?: number
  change_pct?: number
  created_at: string
}

export interface AssetAllocationItem {
  type: string
  label: string
  value: number
  percentage: number
  count: number
}

export interface StockNewsArticle {
  id: string
  ticker: string
  title: string
  title_th: string
  summary: string
  summary_th: string
  content?: string
  content_th?: string
  source: string
  url: string
  published_at: string
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  thumbnail_url?: string
  created_at: string
}

export interface StockChartPoint {
  time: string
  price: number
  volume?: number
}

export interface StockChartData {
  ticker: string
  period: '1D' | '5D' | '1M' | '6M' | '1Y' | 'ALL'
  currency: string
  current_price: number
  previous_close: number
  base_price: number
  change_amount: number
  change_pct: number
  market_session?: 'REGULAR' | 'PRE' | 'POST' | 'POSTPOST' | 'NIGHT'
  regular_price?: number
  extended_price?: number
  extended_change?: number
  extended_change_pct?: number
  points: StockChartPoint[]
}

export interface PortfolioSummaryCurrency {
  total_market_value: number
  total_cost_basis: number
  total_unrealized_pnl: number
  total_unrealized_pnl_pct: number
  total_realized_pnl: number
  total_dividends: number
  asset_allocation: AssetAllocationItem[]
}

export interface PortfolioOverview {
  base_currency?: 'THB' | 'USD'
  usd_to_thb_rate?: number
  selected_portfolio_id?: string
  selected_asset_type?: string
  available_portfolios?: InvestmentPortfolio[]
  total_market_value: number
  total_cost_basis: number
  total_unrealized_pnl: number
  total_unrealized_pnl_pct: number
  total_realized_pnl: number
  total_dividends: number
  active_assets_count: number
  asset_allocation?: AssetAllocationItem[]
  summary_thb?: PortfolioSummaryCurrency
  summary_usd?: PortfolioSummaryCurrency
  holdings: StockHolding[]
  updated_prices?: Record<string, number>
}

export interface CreateTransactionPayload {
  ticker?: string
  holding?: string
  portfolio?: string
  transaction_type: TransactionType
  shares: number
  price_per_share: number
  fee: number
  currency?: string
  executed_at: string
  notes?: string
}

export interface UpdateTransactionPayload {
  transaction_type?: TransactionType
  shares?: number
  price_per_share?: number
  fee?: number
  currency?: string
  executed_at?: string
  notes?: string
}

export interface UpdateHoldingPayload {
  name?: string
  currency?: string
  asset_type?: AssetType
  notes?: string
  portfolio?: string
}

export interface MarketDetail {
  market: string
  name: string
  is_open: boolean
  session: string
  opens_at: string
  current_time_local: string
  hours_description: string
}

export interface HoldingMarketStatus {
  ticker: string
  name: string
  asset_type: AssetType
  is_open: boolean
}

export interface MarketStatusResponse {
  is_any_market_open: boolean
  markets: {
    SET: MarketDetail
    US: MarketDetail
    CRYPTO: MarketDetail
  }
  user_open_holdings_count: number
  user_total_holdings_count: number
  should_poll_realtime: boolean
  holdings_status: HoldingMarketStatus[]
}

export const PORTFOLIO_COLORS = [
  '#3B82F6', // Blue
  '#10B981', // Emerald
  '#8B5CF6', // Purple
  '#F59E0B', // Amber
  '#EC4899', // Pink
  '#06B6D4', // Cyan
  '#F97316', // Orange
  '#6366F1'  // Indigo
] as const

const COLOR_NAME_MAP: Record<string, string> = {
  blue: '#3B82F6',
  emerald: '#10B981',
  green: '#10B981',
  purple: '#8B5CF6',
  violet: '#8B5CF6',
  amber: '#F59E0B',
  yellow: '#F59E0B',
  orange: '#F97316',
  pink: '#EC4899',
  rose: '#F43F5E',
  red: '#EF4444',
  cyan: '#06B6D4',
  sky: '#0EA5E9',
  teal: '#14B8A6',
  indigo: '#6366F1',
  zinc: '#71717A',
  gray: '#71717A'
}

export function getPortfolioColor(color?: string | null): string {
  if (!color) return '#3B82F6'
  const trimmed = color.trim()
  if (trimmed.startsWith('#') || trimmed.startsWith('rgb')) {
    return trimmed
  }
  return COLOR_NAME_MAP[trimmed.toLowerCase()] || trimmed || '#3B82F6'
}
