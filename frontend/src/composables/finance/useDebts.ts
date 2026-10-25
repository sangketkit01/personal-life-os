import { ref } from 'vue'
import apiClient from '../../api/client'
import { useToastStore } from '../../stores/toast'
import type { FinancialObligation } from '../../types/finance'

export interface CreateDebtPayload {
  title: string
  direction: 'INFLOW' | 'OUTFLOW'
  subtype: 'INFORMAL_BORROW' | 'FORMAL_LOAN'
  amount: number
  currency?: string
  due_date?: string | null
  counterparty: string
  contact?: string
  promptpay?: string
  reason?: string
  is_flexible?: boolean
  interest_rate_pa?: number
  min_monthly_payment?: number
  creditor_bank?: string
  contract_no?: string
}

export interface DebtorEntry {
  debtor_name: string
  direction: 'INFLOW' | 'OUTFLOW'
  total_principal: number
  total_repaid: number
  outstanding_balance: number
  active_count: number
  obligations: Array<{
    id: string
    title: string
    amount: number
    status: string
    due_date?: string
    remaining_balance: number
    repaid_amount: number
  }>
}

export function useDebts() {
  const debts = ref<FinancialObligation[]>([])
  const currentDebt = ref<FinancialObligation | null>(null)
  const debtors = ref<DebtorEntry[]>([])
  const isLoading = ref(false)
  const isActionLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchDebts(params?: {
    direction?: 'INFLOW' | 'OUTFLOW' | 'ALL'
    status?: string
    search?: string
  }) {
    isLoading.value = true
    error.value = null
    try {
      const qParams: Record<string, string> = {
        type: 'DEBT',
        ordering: '-created_at'
      }
      if (params?.direction && params.direction !== 'ALL') {
        qParams.direction = params.direction
      }
      if (params?.status) {
        qParams.status = params.status
      }
      if (params?.search) {
        qParams.search = params.search
      }

      const res = await apiClient.get('/finance/obligations/', { params: qParams })
      const data = res.data
      debts.value = Array.isArray(data) ? data : (data.results || [])
      return debts.value
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to fetch debt records'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchDebtById(id: string) {
    isLoading.value = true
    error.value = null
    try {
      const res = await apiClient.get<FinancialObligation>(`/finance/obligations/${id}/`)
      currentDebt.value = res.data
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to fetch debt details'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchDebtorsDirectory() {
    isLoading.value = true
    try {
      const res = await apiClient.get('/finance/obligations/debtors/')
      debtors.value = res.data
      return debtors.value
    } finally {
      isLoading.value = false
    }
  }

  async function createDebt(payload: CreateDebtPayload) {
    isActionLoading.value = true
    error.value = null
    try {
      const metadata: Record<string, any> = {
        subtype: payload.subtype,
        counterparty: payload.counterparty,
        contact: payload.contact || '',
        promptpay: payload.promptpay || '',
        reason: payload.reason || '',
        is_flexible: !!payload.is_flexible,
        remaining_balance: payload.amount
      }

      if (payload.subtype === 'FORMAL_LOAN') {
        metadata.interest_rate_pa = payload.interest_rate_pa || 0
        metadata.min_monthly_payment = payload.min_monthly_payment || 0
        metadata.creditor_bank = payload.creditor_bank || ''
        metadata.contract_no = payload.contract_no || ''
      }

      const res = await apiClient.post<FinancialObligation>('/finance/obligations/', {
        title: payload.title || `${payload.direction === 'INFLOW' ? 'Debtor' : 'Loan'}: ${payload.counterparty}`,
        type: 'DEBT',
        subtype: payload.subtype,
        direction: payload.direction,
        amount: payload.amount,
        currency: payload.currency || 'THB',
        due_date: payload.is_flexible ? null : (payload.due_date || null),
        metadata
      })

      debts.value.unshift(res.data)
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to create debt record'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function updateDebt(id: string, payload: Partial<CreateDebtPayload>) {
    isActionLoading.value = true
    error.value = null
    try {
      const currentMeta = currentDebt.value?.metadata || {}
      const res = await apiClient.patch<FinancialObligation>(`/finance/obligations/${id}/`, {
        title: payload.title,
        amount: payload.amount,
        due_date: payload.due_date,
        metadata: {
          ...currentMeta,
          ...(payload.counterparty !== undefined ? { counterparty: payload.counterparty } : {}),
          ...(payload.contact !== undefined ? { contact: payload.contact } : {}),
          ...(payload.promptpay !== undefined ? { promptpay: payload.promptpay } : {}),
          ...(payload.reason !== undefined ? { reason: payload.reason } : {}),
          ...(payload.is_flexible !== undefined ? { is_flexible: payload.is_flexible } : {})
        }
      })
      currentDebt.value = res.data
      const idx = debts.value.findIndex(d => d.id === id)
      if (idx !== -1) debts.value[idx] = res.data
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to update debt record'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function payDebt(id: string, payload: {
    paid_amount?: number
    note?: string
    slip_file?: File
  }) {
    isActionLoading.value = true
    try {
      const formData = new FormData()
      if (payload.paid_amount !== undefined) formData.append('paid_amount', payload.paid_amount.toString())
      if (payload.note) formData.append('note', payload.note)
      if (payload.slip_file) formData.append('slip_file', payload.slip_file)

      const res = await apiClient.post(`/finance/obligations/${id}/pay/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (currentDebt.value && currentDebt.value.id === id) {
        try {
          await fetchDebtById(id)
        } catch (refreshErr) {
          console.warn('Debt refresh failed after payment:', refreshErr)
          const toast = useToastStore()
          toast.error('Payment recorded, but failed to refresh debt details.', 6000, {
            label: 'Retry refresh',
            onClick: () => fetchDebtById(id)
          })
        }
      }
      return res.data
    } finally {
      isActionLoading.value = false
    }
  }

  async function deleteDebt(id: string) {
    isActionLoading.value = true
    try {
      await apiClient.delete(`/finance/obligations/${id}/`)
      debts.value = debts.value.filter(d => d.id !== id)
      if (currentDebt.value?.id === id) {
        currentDebt.value = null
      }
    } finally {
      isActionLoading.value = false
    }
  }

  async function uploadAttachment(obligationId: string, file: File, type: string = 'OTHER') {
    isActionLoading.value = true
    try {
      const formData = new FormData()
      formData.append('obligation', obligationId)
      formData.append('file', file)
      formData.append('file_type', type)

      const res = await apiClient.post(`/finance/attachments/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (currentDebt.value && currentDebt.value.id === obligationId) {
        await fetchDebtById(obligationId)
      }
      return res.data
    } finally {
      isActionLoading.value = false
    }
  }

  async function deleteAttachment(attachmentId: string, obligationId?: string) {
    isActionLoading.value = true
    try {
      await apiClient.delete(`/finance/attachments/${attachmentId}/`)
      if (obligationId && currentDebt.value && currentDebt.value.id === obligationId) {
        await fetchDebtById(obligationId)
      }
    } finally {
      isActionLoading.value = false
    }
  }

  return {
    debts,
    currentDebt,
    debtors,
    isLoading,
    isActionLoading,
    error,
    fetchDebts,
    fetchDebtById,
    fetchDebtorsDirectory,
    createDebt,
    updateDebt,
    payDebt,
    deleteDebt,
    uploadAttachment,
    deleteAttachment
  }
}
