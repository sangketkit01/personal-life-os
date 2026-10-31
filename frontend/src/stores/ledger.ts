import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ledgerApi } from '../api/ledger'
import { useToastStore } from './toast'
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

export const useLedgerStore = defineStore('ledger', () => {
  const accounts = ref<LedgerAccount[]>([])
  const selectedAccountId = ref<string | null>(null)
  const categories = ref<LedgerCategory[]>([])
  const transactions = ref<LedgerTransaction[]>([])
  const totalTransactionsCount = ref<number>(0)
  const pendingSplits = ref<TransactionSplitItem[]>([])
  const budgets = ref<CategoryBudgetItem[]>([])
  const summary = ref<CashFlowSummary | null>(null)

  const now = new Date()
  const activeMonth = ref<string>(
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  )

  const isLoading = ref<boolean>(false)
  const isSummaryLoading = ref<boolean>(false)

  // Computed
  const activeAccounts = computed(() => accounts.value.filter((a) => !a.is_archived))

  const activeAccount = computed(() =>
    accounts.value.find((a) => a.id === selectedAccountId.value) || null
  )

  const totalLiquidCash = computed(() => {
    return accounts.value
      .filter((a) => a.account_type !== 'CREDIT_CARD' && !a.is_archived)
      .reduce((sum, a) => sum + Number(a.current_balance || 0), 0)
  })

  const totalCreditDebt = computed(() => {
    return accounts.value
      .filter((a) => a.account_type === 'CREDIT_CARD' && !a.is_archived)
      .reduce((sum, a) => sum + Math.abs(Number(a.current_balance || 0)), 0)
  })

  const pendingSplitsTotal = computed(() => {
    return pendingSplits.value.reduce((sum, s) => sum + Number(s.amount || 0), 0)
  })

  // Actions
  async function fetchAccounts() {
    try {
      const data = await ledgerApi.getAccounts()
      accounts.value = data
      if (!selectedAccountId.value && data.length > 0) {
        const defaultAcc = data.find((a) => a.is_default) || data[0]
        selectedAccountId.value = defaultAcc.id
      }
      return data
    } catch (err) {
      console.error('Failed to fetch ledger accounts', err)
      return []
    }
  }

  async function fetchCategories(type?: 'INCOME' | 'EXPENSE') {
    try {
      const data = await ledgerApi.getCategories(type)
      categories.value = data
      return data
    } catch (err) {
      console.error('Failed to fetch ledger categories', err)
      return []
    }
  }

  async function fetchSummary(month?: string, currency?: string) {
    isSummaryLoading.value = true
    try {
      const targetMonth = month || activeMonth.value
      const data = await ledgerApi.getCashFlowSummary(targetMonth, currency)
      summary.value = data
      return data
    } finally {
      isSummaryLoading.value = false
    }
  }

  let transactionRequest = 0
  async function fetchTransactions(params?: {
    account?: string
    category?: string
    type?: string
    start_date?: string
    end_date?: string
    is_split?: boolean
    search?: string
    page?: number
    currency?: string
    report_kind?: string
    uncategorized?: string
  }) {
    const request = ++transactionRequest
    isLoading.value = true
    try {
      const res = await ledgerApi.getTransactions(params)
      if (request === transactionRequest) {
        transactions.value = res.results || []
        totalTransactionsCount.value = res.count || 0
      }
      return res
    } finally {
      if (request === transactionRequest) isLoading.value = false
    }
  }

  async function fetchPendingSplits() {
    try {
      const res = await ledgerApi.getSplits('PENDING')
      pendingSplits.value = Array.isArray(res) ? res : res.results || []
      return pendingSplits.value
    } catch (err) {
      console.error('Failed to fetch pending splits', err)
      return []
    }
  }

  let budgetRequest = 0
  async function fetchBudgets(month?: string) {
    const request = ++budgetRequest
    try {
      const targetMonth = month || activeMonth.value
      const data = await ledgerApi.getBudgets(targetMonth)
      if (request === budgetRequest) budgets.value = data
      return data
    } catch (err) {
      console.error('Failed to fetch budgets', err)
      throw err
    }
  }

  async function createTransaction(payload: CreateTransactionPayload) {
    const tx = await ledgerApi.createTransaction(payload)
    // Refresh account balances and summary
    try {
      await Promise.all([fetchAccounts(), fetchSummary(), fetchPendingSplits()])
    } catch (refreshErr) {
      console.warn('Post-transaction refresh failed:', refreshErr)
      const toast = useToastStore()
      toast.error('Transaction recorded, but failed to refresh accounts.', 6000, {
        label: 'Retry refresh',
        onClick: () => { Promise.all([fetchAccounts(), fetchSummary(), fetchPendingSplits()]) }
      })
    }
    return tx
  }

  async function updateTransaction(id: string, payload: Partial<CreateTransactionPayload>) {
    const tx = await ledgerApi.updateTransaction(id, payload as any)
    const idx = transactions.value.findIndex(t => t.id === id)
    if (idx !== -1) {
      transactions.value[idx] = tx
    }
    try {
      await Promise.all([fetchAccounts(), fetchSummary(), fetchPendingSplits()])
    } catch (refreshErr) {
      console.warn('Post-update refresh failed:', refreshErr)
    }
    try {
      const { useFinanceStore } = await import('./finance')
      await useFinanceStore().fetchOverview()
    } catch (e) {
      // Ignored if finance store not mounted
    }
    return tx
  }

  async function deleteTransaction(id: string) {
    await ledgerApi.deleteTransaction(id)
    try {
      await Promise.all([fetchAccounts(), fetchSummary(), fetchPendingSplits()])
    } catch (refreshErr) {
      console.warn('Post-delete refresh failed:', refreshErr)
      const toast = useToastStore()
      toast.error('Transaction deleted, but failed to refresh accounts.', 6000, {
        label: 'Retry refresh',
        onClick: () => { Promise.all([fetchAccounts(), fetchSummary(), fetchPendingSplits()]) }
      })
    }
    try {
      const { useFinanceStore } = await import('./finance')
      await useFinanceStore().fetchOverview()
    } catch (e) {
      // Ignored if finance store not mounted
    }
  }

  async function createAccount(payload: CreateAccountPayload) {
    const acc = await ledgerApi.createAccount(payload)
    try {
      await fetchAccounts()
    } catch (refreshErr) {
      console.warn('Post-account create refresh failed:', refreshErr)
    }
    return acc
  }

  async function updateAccount(id: string, payload: Partial<CreateAccountPayload>) {
    const acc = await ledgerApi.updateAccount(id, payload)
    try {
      await fetchAccounts()
    } catch (refreshErr) {
      console.warn('Post-account update refresh failed:', refreshErr)
    }
    return acc
  }

  async function deleteAccount(id: string) {
    await ledgerApi.deleteAccount(id)
    try {
      await fetchAccounts()
    } catch (refreshErr) {
      console.warn('Post-account delete refresh failed:', refreshErr)
    }
  }

  async function transfer(payload: TransferPayload) {
    const res = await ledgerApi.transfer(payload)
    try {
      await Promise.all([fetchAccounts(), fetchSummary()])
    } catch (refreshErr) {
      console.warn('Post-transfer refresh failed:', refreshErr)
      const toast = useToastStore()
      toast.error('Transfer recorded, but failed to refresh accounts.', 6000, {
        label: 'Retry refresh',
        onClick: () => { Promise.all([fetchAccounts(), fetchSummary()]) }
      })
    }
    return res
  }

  async function settleSplit(splitId: string, payload: SettleSplitPayload) {
    const res = await ledgerApi.settleSplit(splitId, payload)
    try {
      await Promise.all([fetchAccounts(), fetchSummary(), fetchPendingSplits()])
    } catch (refreshErr) {
      console.warn('Post-settle refresh failed:', refreshErr)
      const toast = useToastStore()
      toast.error('Split settled, but failed to refresh accounts.', 6000, {
        label: 'Retry refresh',
        onClick: () => { Promise.all([fetchAccounts(), fetchSummary(), fetchPendingSplits()]) }
      })
    }
    try {
      const { useFinanceStore } = await import('./finance')
      await useFinanceStore().fetchOverview()
    } catch (e) {
      // Ignored if finance store not mounted
    }
    return res
  }

  async function recalculateBalance(accountId: string) {
    const res = await ledgerApi.recalculateAccountBalance(accountId)
    await fetchAccounts()
    return res
  }

  return {
    accounts,
    activeAccounts,
    selectedAccountId,
    activeAccount,
    categories,
    transactions,
    totalTransactionsCount,
    pendingSplits,
    budgets,
    summary,
    activeMonth,
    isLoading,
    isSummaryLoading,
    totalLiquidCash,
    totalCreditDebt,
    pendingSplitsTotal,
    fetchAccounts,
    fetchCategories,
    fetchSummary,
    fetchTransactions,
    fetchPendingSplits,
    fetchBudgets,
    createTransaction,
    updateTransaction,
    deleteTransaction,
    createAccount,
    updateAccount,
    deleteAccount,
    transfer,
    settleSplit,
    recalculateBalance
  }
})
