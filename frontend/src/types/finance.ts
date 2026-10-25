export type ObligationType = 'INSTALLMENT' | 'SUBSCRIPTION' | 'FREE_TRIAL' | 'DEBT'
export type ObligationSubtype = 'STANDARD' | 'HIRE_PURCHASE' | 'BNPL_ACCOUNT' | 'BNPL_ORDER' | 'FORMAL_LOAN' | 'INFORMAL_BORROW'
export type ObligationStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'CANCELLED'
export type AttachmentType = 'CONTRACT' | 'SLIP' | 'STATEMENT' | 'SCREENSHOT' | 'OTHER'

export interface ObligationAttachmentItem {
  id: string
  obligation: string
  payment_history?: string | null
  file?: string
  file_url?: string
  drive_file_id?: string
  drive_view_link?: string
  drive_download_link?: string
  file_name: string
  file_type: AttachmentType
  file_size: number
  uploaded_at: string
}

export interface PaymentHistoryItem {
  id: string
  paid_amount: string
  paid_at: string
  term_number: number | null
  note: string
  attachments?: ObligationAttachmentItem[]
}

export interface InstallmentSummary {
  total_terms: number
  current_term: number
  remaining_terms: number
  remaining_balance: string | number
  progress_pct: number
  is_finished: boolean
  lender: string
}

export interface DebtSummary {
  counterparty: string
  is_flexible: boolean
  initial_amount: string | number
  remaining_balance: string | number
  total_paid: string | number
  progress_pct: number
  is_settled: boolean
}

export interface FreeTrialSummary {
  account_email: string
  linked_card: string
  cancel_url: string
  auto_renew_cost: string | number
  days_remaining: number | null
  urgency: 'CRITICAL' | 'WARNING' | 'SAFE' | 'EXPIRED'
  is_cancelled: boolean
}

export interface SubscriptionSummary {
  billing_cycle: 'MONTHLY' | 'YEARLY'
  is_yearly: boolean
  account_email: string
  payment_method: string
  category: string
  amount_per_period: string | number
}

export type ObligationSummary = Record<string, any>

export interface FinancialObligation {
  id: string
  parent?: string | null
  project?: string | null
  project_name?: string | null
  project_color?: string | null
  title: string
  type: ObligationType
  subtype?: ObligationSubtype
  direction: 'OUTFLOW' | 'INFLOW'
  amount: string
  currency: string
  status: ObligationStatus
  due_date: string | null
  billing_day: number | null
  metadata: Record<string, any>
  summary: Record<string, any>
  sub_orders?: any[]
  payment_histories?: PaymentHistoryItem[]
  attachments?: ObligationAttachmentItem[]
  created_at: string
  updated_at: string
}

export interface UpcomingBill {
  id: string
  title: string
  type: ObligationType
  direction?: 'OUTFLOW' | 'INFLOW'
  amount: string
  amount_thb?: string | number
  currency?: string
  due_date: string
  days_left: number
  is_trial: boolean
  summary: ObligationSummary
}

export interface FinancialOverview {
  target_month: string
  confirmed_burn_rate: string | number
  potential_risk_amount: string | number
  expected_inflow_amount?: string | number
  active_trials_count: number
  critical_trials_count: number
  upcoming_7_days_count: number
  upcoming_7_days: UpcomingBill[]
  items_by_type: {
    INSTALLMENT: FinancialObligation[]
    SUBSCRIPTION: FinancialObligation[]
    FREE_TRIAL: FinancialObligation[]
    DEBT: FinancialObligation[]
  }
}
