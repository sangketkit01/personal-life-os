import { ref } from 'vue'
import apiClient from '../../api/client'
import type { FinancialObligation } from '../../types/finance'

export interface CreateBNPLAccountPayload {
  title: string
  provider: string
  credit_limit: number
  cutoff_day: number
  due_day: number
  account_number?: string
  notes?: string
}

export interface CreateBNPLOrderPayload {
  title: string
  monthly_amount: number
  total_terms: number
  current_term?: number
  store?: string
  order_number?: string
  order_date?: string
  total_principal?: number
}

export function useBNPL() {
  const accounts = ref<FinancialObligation[]>([])
  const currentAccount = ref<FinancialObligation | null>(null)
  const subOrders = ref<FinancialObligation[]>([])
  const isLoading = ref(false)
  const isActionLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAccounts(params?: { search?: string }) {
    isLoading.value = true
    error.value = null
    try {
      const res = await apiClient.get('/finance/obligations/', {
        params: {
          subtype: 'BNPL_ACCOUNT',
          search: params?.search || undefined,
          ordering: '-created_at'
        }
      })
      const data = res.data
      accounts.value = Array.isArray(data) ? data : (data.results || [])
      return accounts.value
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to fetch BNPL accounts'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAccountById(id: string) {
    isLoading.value = true
    error.value = null
    try {
      const res = await apiClient.get<FinancialObligation>(`/finance/obligations/${id}/`)
      currentAccount.value = res.data
      // Also sync subOrders from response or fetch dedicated
      if (res.data.sub_orders) {
        subOrders.value = res.data.sub_orders as any
      } else {
        await fetchSubOrders(id)
      }
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to fetch BNPL account details'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchSubOrders(accountId: string) {
    if (!accountId) {
      subOrders.value = []
      return []
    }
    isLoading.value = true
    try {
      const res = await apiClient.get('/finance/obligations/', {
        params: {
          parent: accountId,
          ordering: '-created_at'
        }
      })
      const data = res.data
      subOrders.value = Array.isArray(data) ? data : (data.results || [])
      return subOrders.value
    } finally {
      isLoading.value = false
    }
  }

  async function createAccount(payload: CreateBNPLAccountPayload) {
    isActionLoading.value = true
    error.value = null
    try {
      const res = await apiClient.post<FinancialObligation>('/finance/obligations/', {
        title: payload.title,
        type: 'INSTALLMENT',
        subtype: 'BNPL_ACCOUNT',
        direction: 'OUTFLOW',
        amount: 0,
        currency: 'THB',
        billing_day: payload.due_day,
        metadata: {
          subtype: 'BNPL_ACCOUNT',
          provider: payload.provider,
          credit_limit: payload.credit_limit,
          cutoff_day: payload.cutoff_day,
          due_day: payload.due_day,
          account_number: payload.account_number || '',
          notes: payload.notes || ''
        }
      })
      accounts.value.unshift(res.data)
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to create BNPL account'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function updateAccount(id: string, payload: Partial<CreateBNPLAccountPayload>) {
    isActionLoading.value = true
    error.value = null
    try {
      const currentMeta = currentAccount.value?.metadata || {}
      const res = await apiClient.patch<FinancialObligation>(`/finance/obligations/${id}/`, {
        title: payload.title,
        billing_day: payload.due_day,
        metadata: {
          ...currentMeta,
          ...(payload.provider !== undefined ? { provider: payload.provider } : {}),
          ...(payload.credit_limit !== undefined ? { credit_limit: payload.credit_limit } : {}),
          ...(payload.cutoff_day !== undefined ? { cutoff_day: payload.cutoff_day } : {}),
          ...(payload.due_day !== undefined ? { due_day: payload.due_day } : {}),
          ...(payload.account_number !== undefined ? { account_number: payload.account_number } : {}),
          ...(payload.notes !== undefined ? { notes: payload.notes } : {})
        }
      })
      currentAccount.value = res.data
      const idx = accounts.value.findIndex(a => a.id === id)
      if (idx !== -1) accounts.value[idx] = res.data
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to update BNPL account'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function deleteAccount(id: string) {
    isActionLoading.value = true
    error.value = null
    try {
      await apiClient.delete(`/finance/obligations/${id}/`)
      accounts.value = accounts.value.filter(a => a.id !== id)
      if (currentAccount.value?.id === id) {
        currentAccount.value = null
      }
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to delete BNPL account'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function createSubOrder(accountId: string, payload: CreateBNPLOrderPayload) {
    isActionLoading.value = true
    error.value = null
    try {
      const res = await apiClient.post<FinancialObligation>('/finance/obligations/', {
        parent: accountId,
        title: payload.title,
        type: 'INSTALLMENT',
        subtype: 'BNPL_ORDER',
        direction: 'OUTFLOW',
        amount: payload.monthly_amount,
        currency: 'THB',
        metadata: {
          subtype: 'BNPL_ORDER',
          total_terms: payload.total_terms,
          current_term: payload.current_term ?? 0,
          store: payload.store || '',
          order_number: payload.order_number || '',
          order_date: payload.order_date || new Date().toISOString().split('T')[0],
          total_principal: payload.total_principal || (payload.monthly_amount * payload.total_terms)
        }
      })
      subOrders.value.unshift(res.data)
      // Refresh current account so limit and current bill recompute
      if (currentAccount.value && currentAccount.value.id === accountId) {
        await fetchAccountById(accountId)
      }
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to create sub-order'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function payAccountBill(accountId: string, payload: {
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

      const res = await apiClient.post(`/finance/obligations/${accountId}/pay/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      await fetchAccountById(accountId)
      await fetchAccounts()
      return res.data
    } finally {
      isActionLoading.value = false
    }
  }

  async function deleteOrder(orderId: string, accountId?: string) {
    isActionLoading.value = true
    try {
      await apiClient.delete(`/finance/obligations/${orderId}/`)
      subOrders.value = subOrders.value.filter(o => o.id !== orderId)
      if (accountId) {
        await fetchAccountById(accountId)
        await fetchAccounts()
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
      if (currentAccount.value && currentAccount.value.id === obligationId) {
        await fetchAccountById(obligationId)
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
      if (obligationId && currentAccount.value && currentAccount.value.id === obligationId) {
        await fetchAccountById(obligationId)
      }
    } finally {
      isActionLoading.value = false
    }
  }

  return {
    accounts,
    currentAccount,
    subOrders,
    isLoading,
    isActionLoading,
    error,
    fetchAccounts,
    fetchAccountById,
    fetchSubOrders,
    createAccount,
    updateAccount,
    deleteAccount,
    createSubOrder,
    payAccountBill,
    deleteOrder,
    uploadAttachment,
    deleteAttachment
  }
}
