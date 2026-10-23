import apiClient from './client'
import type {
  LedgerAccount,
  LedgerCategory,
  LedgerTransaction,
  TransactionSplitItem,
  CategoryBudgetItem,
  CashFlowSummary,
  CreateAccountPayload,
  CreateTransactionPayload,
  TransferPayload,
  SettleSplitPayload
} from '../types/ledger'

export const ledgerApi = {
  // Accounts
  async getAccounts(): Promise<LedgerAccount[]> {
    const res = await apiClient.get<LedgerAccount[]>('/ledger/accounts/')
    return res.data
  },

  async createAccount(payload: CreateAccountPayload): Promise<LedgerAccount> {
    const res = await apiClient.post<LedgerAccount>('/ledger/accounts/', payload)
    return res.data
  },

  async updateAccount(id: string, payload: Partial<CreateAccountPayload>): Promise<LedgerAccount> {
    const res = await apiClient.patch<LedgerAccount>(`/ledger/accounts/${id}/`, payload)
    return res.data
  },

  async deleteAccount(id: string): Promise<void> {
    await apiClient.delete(`/ledger/accounts/${id}/`)
  },

  async recalculateAccountBalance(id: string): Promise<{ new_balance: string }> {
    const res = await apiClient.post<{ new_balance: string }>(`/ledger/accounts/${id}/recalculate_balance/`)
    return res.data
  },

  async transfer(payload: TransferPayload): Promise<{
    outflow_transaction: LedgerTransaction
    inflow_transaction: LedgerTransaction
    source_new_balance: string
    target_new_balance: string
  }> {
    const res = await apiClient.post('/ledger/accounts/transfer/', payload)
    return res.data
  },

  // Categories
  async getCategories(type?: 'INCOME' | 'EXPENSE'): Promise<LedgerCategory[]> {
    const res = await apiClient.get<LedgerCategory[]>('/ledger/categories/', {
      params: type ? { type } : undefined
    })
    return res.data
  },

  async createCategory(payload: {
    name: string
    category_type: 'INCOME' | 'EXPENSE'
    parent?: string | null
    icon?: string
    color?: string
  }): Promise<LedgerCategory> {
    const res = await apiClient.post<LedgerCategory>('/ledger/categories/', payload)
    return res.data
  },

  // Transactions
  async getTransactions(params?: {
    account?: string
    category?: string
    type?: string
    start_date?: string
    end_date?: string
    is_split?: boolean
    search?: string
    page?: number
  }): Promise<{
    count: number
    next: string | null
    previous: string | null
    results: LedgerTransaction[]
  }> {
    const res = await apiClient.get('/ledger/transactions/', { params })
    return res.data
  },

  async createTransaction(payload: CreateTransactionPayload): Promise<LedgerTransaction> {
    const res = await apiClient.post<LedgerTransaction>('/ledger/transactions/', payload)
    return res.data
  },

  async deleteTransaction(id: string): Promise<void> {
    await apiClient.delete(`/ledger/transactions/${id}/`)
  },

  async getCashFlowSummary(month?: string, currency?: string): Promise<CashFlowSummary> {
    const params: Record<string, string> = {}
    if (month) params.month = month
    if (currency) params.currency = currency
    const res = await apiClient.get<CashFlowSummary>('/ledger/transactions/summary/', {
      params: Object.keys(params).length > 0 ? params : undefined
    })
    return res.data
  },

  // Splits
  async getSplits(status?: 'PENDING' | 'SETTLED'): Promise<{
    count: number
    results: TransactionSplitItem[]
  }> {
    const res = await apiClient.get('/ledger/splits/', {
      params: status ? { status } : undefined
    })
    return res.data
  },

  async settleSplit(splitId: string, payload: SettleSplitPayload): Promise<{
    split_id: string
    inflow_transaction_id: string
    account_new_balance: string
  }> {
    const res = await apiClient.post(`/ledger/splits/${splitId}/settle/`, payload)
    return res.data
  },

  // Budgets
  async getBudgets(month?: string): Promise<CategoryBudgetItem[]> {
    const res = await apiClient.get<CategoryBudgetItem[]>('/ledger/budgets/', {
      params: month ? { month } : undefined
    })
    return res.data
  },

  async createBudget(payload: {
    category: string
    period_month: string
    limit_amount: number
  }): Promise<CategoryBudgetItem> {
    const res = await apiClient.post<CategoryBudgetItem>('/ledger/budgets/', payload)
    return res.data
  },

  async deleteBudget(id: string): Promise<void> {
    await apiClient.delete(`/ledger/budgets/${id}/`)
  }
}
