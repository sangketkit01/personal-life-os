export type AccountType = 'BANK' | 'CREDIT_CARD' | 'BROKERAGE_CASH' | 'E_WALLET' | 'CASH'
export type CategoryType = 'INCOME' | 'EXPENSE'
export type TransactionType = 'INFLOW' | 'OUTFLOW' | 'TRANSFER'
export type ReportingKind = 'AUTO' | 'INCOME' | 'EXPENSE' | 'REIMBURSEMENT' | 'LOAN' | 'INVESTMENT' | 'CARD_PAYMENT'

export interface LedgerAccount {
  id: string
  name: string
  account_type: AccountType
  currency: string
  initial_balance: string | number
  current_balance: string | number
  credit_limit?: string | number | null
  account_number: string
  institution_name: string
  color: string
  is_default: boolean
  is_archived: boolean
  transaction_count?: number
  created_at: string
  updated_at: string
}

export interface LedgerCategory {
  id: string
  name: string
  category_type: CategoryType
  parent?: string | null
  icon: string
  color: string
  is_system: boolean
  subcategories?: LedgerCategory[]
  created_at?: string
}

export interface TransactionSplitItem {
  id: string
  transaction?: string
  transaction_title?: string
  transaction_date?: string
  transaction_account_name?: string
  counterparty_name: string
  counterparty_contact: string
  amount: string | number
  is_settled: boolean
  settled_at?: string | null
  settlement_transaction?: string | null
  debtor_obligation?: string | null
  debtor_id?: string | null
  debtor_status?: string | null
  notes: string
  items_detail?: Array<{ name: string; price: number; quantity?: number; consumer_count?: number; share: number }>
}

export interface TransactionAttachmentItem {
  id: string
  transaction: string
  file?: string
  file_url?: string
  drive_file_id?: string
  drive_view_link?: string
  drive_download_link?: string
  file_name: string
  file_type: string
  file_size: number
  slip_reference: string
  uploaded_at: string
}

export interface LedgerTransaction {
  id: string
  account: string
  account_name?: string
  account_currency?: string
  reporting_kind?: ReportingKind
  account_type?: AccountType
  transaction_type: TransactionType
  category?: string | null
  category_name?: string | null
  category_icon?: string | null
  gross_amount: string | number
  net_amount: string | number
  title: string
  notes: string
  transaction_date: string
  is_split: boolean
  split_metadata?: Record<string, any>
  splits?: TransactionSplitItem[]
  attachments?: TransactionAttachmentItem[]
  obligation?: string | null
  portfolio?: string | null
  workspace_project?: string | null
  transfer_destination?: string | null
  transfer_peer?: string | null
  is_amount_locked?: boolean
  amount_lock_reason?: string
  created_at: string
  updated_at: string
}

export interface CategoryBudgetItem {
  id: string
  category: string
  category_name?: string
  category_parent?: string | null
  category_icon?: string
  period_month: string
  currency: string
  limit_amount: string | number
  spent_amount: string | number
  remaining_amount: string | number
  usage_pct: number
  created_at: string
}

export interface CashFlowSummary {
  period_month: string
  total_inflow: string | number
  total_gross_outflow: string | number
  total_net_outflow: string | number
  net_cash_flow: string | number
  total_liquid_balance: string | number
  total_credit_debt: string | number
  pending_splits_amount: string | number
  pending_splits_count: number
}

export interface CreateAccountPayload {
  name: string
  account_type: AccountType
  currency?: string
  initial_balance: number
  credit_limit?: number | null
  account_number?: string
  institution_name?: string
  color?: string
  is_default?: boolean
}

export interface CreateTransactionPayload {
  account: string
  transaction_type: TransactionType
  reporting_kind?: ReportingKind
  category?: string | null
  gross_amount: number
  net_amount?: number
  title: string
  notes?: string
  transaction_date: string
  splits_payload?: Array<{
    counterparty_name: string
    counterparty_contact?: string
    amount: number
    notes?: string
  }>
  auto_create_radar_debtors?: boolean
  obligation?: string | null
  portfolio?: string | null
  workspace_project?: string | null
}

export interface UpdateTransactionPayload {
  reporting_kind?: ReportingKind
  title?: string
  notes?: string
  category?: string | null
  transaction_date?: string
  gross_amount?: number
  net_amount?: number
}

export interface TransferPayload {
  source_account_id: string
  target_account_id: string
  amount: number
  transaction_date: string
  title?: string
  notes?: string
}

export interface SettleSplitPayload {
  deposit_account_id: string
  settlement_date?: string
  settlement_title?: string
}

export interface DashboardMetrics { income: string; expense: string; surplus: string; cash_in: string; cash_out: string; cash_flow: string }
export interface DashboardCategory { id: string | null; name: string; amount: string; count: number; share: number; children: Array<{ id: string; name: string; amount: string; count: number }> }
export interface DashboardTransaction { id: string; title: string; date: string; account: string; account_name: string; currency: string; category_name: string; kind: string; amount: string; gross_amount: string; net_amount: string; transaction_type: TransactionType }
export interface LedgerDashboard {
  period: { month: string; start: string; end: string; is_partial: boolean; previous_start: string; previous_end: string }
  currency: string; currencies: string[]; as_of: string; metrics: DashboardMetrics; comparison: DashboardMetrics
  liquid_balance: string; credit_debt: string; pending_split_amount: string; uncategorized_count: number
  accounts: Array<{ id: string; name: string; type: AccountType; balance: string }>
  daily: Array<DashboardMetrics & { date: string }>; history: Array<DashboardMetrics & { month: string }>
  income_sources: DashboardCategory[]; expense_categories: DashboardCategory[]
  budgets: Array<{ id: string; category: string; name: string; currency: string; limit: string; spent: string; remaining: string; usage_pct: number }>
  forecast: { as_of: string; bills: Array<{ id: string; title: string; due_date: string; known_amount: string; pending_dynamic_count: number; projected: boolean; conditional: boolean; path: string }>; windows: Record<string, { known_due: string; remaining: string; pending_dynamic_count: number; conditional_amount: string; count: number }> }
  recent: DashboardTransaction[]; largest_expenses: DashboardTransaction[]
}
