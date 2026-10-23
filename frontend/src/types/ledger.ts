export type AccountType = 'BANK' | 'CREDIT_CARD' | 'BROKERAGE_CASH' | 'E_WALLET' | 'CASH'
export type CategoryType = 'INCOME' | 'EXPENSE'
export type TransactionType = 'INFLOW' | 'OUTFLOW' | 'TRANSFER'

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
  created_at: string
  updated_at: string
}

export interface CategoryBudgetItem {
  id: string
  category: string
  category_name?: string
  category_icon?: string
  period_month: string
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
