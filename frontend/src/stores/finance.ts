import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import type { FinancialObligation, FinancialOverview } from '../types/finance'
import { useToastStore } from './toast'

export const useFinanceStore = defineStore('finance', () => {
  const overview = ref<FinancialOverview | null>(null)
  const obligations = ref<FinancialObligation[]>([])
  const isLoading = ref<boolean>(false)
  const isOverviewLoading = ref<boolean>(false)

  async function fetchOverview() {
    isOverviewLoading.value = true
    try {
      const res = await apiClient.get<FinancialOverview>('/finance/overview/')
      overview.value = res.data
      return res.data
    } finally {
      isOverviewLoading.value = false
    }
  }

  async function fetchObligations(type?: string, status?: string, subtype?: string, parent?: string) {
    isLoading.value = true
    try {
      const params: Record<string, string> = {}
      if (type) params.type = type
      if (status) params.status = status
      if (subtype) params.subtype = subtype
      if (parent) params.parent = parent

      const res = await apiClient.get<{ results: FinancialObligation[] } | FinancialObligation[]>('/finance/obligations/', { params })
      const list = Array.isArray(res.data) ? res.data : res.data.results || []
      obligations.value = list
      return list
    } finally {
      isLoading.value = false
    }
  }

  async function createObligation(payload: Record<string, any>) {
    const res = await apiClient.post<FinancialObligation>('/finance/obligations/', payload)
    obligations.value.unshift(res.data)
    try {
      await fetchOverview()
    } catch (refreshErr) {
      console.warn('Overview refresh failed after obligation creation:', refreshErr)
      const toast = useToastStore()
      toast.error('Record created, but failed to refresh overview.', 6000, {
        label: 'Retry refresh',
        onClick: () => fetchOverview()
      })
    }
    return res.data
  }

  async function updateObligation(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<FinancialObligation>(`/finance/obligations/${id}/`, payload)
    const idx = obligations.value.findIndex(o => o.id === id)
    if (idx !== -1) {
      obligations.value[idx] = res.data
    }
    try {
      await fetchOverview()
    } catch (refreshErr) {
      console.warn('Overview refresh failed after obligation update:', refreshErr)
      const toast = useToastStore()
      toast.error('Record updated, but failed to refresh overview.', 6000, {
        label: 'Retry refresh',
        onClick: () => fetchOverview()
      })
    }
    return res.data
  }

  async function payObligation(id: string, data: {
    paid_amount?: number
    term_number?: number
    statement_month?: string
    note?: string
    slip_file?: File
    account_id?: string
    drive_file_id?: string
    drive_view_link?: string
    drive_download_link?: string
    file_name?: string
    file_size?: number
  } = {}) {
    let requestData: any = data
    let headers: Record<string, string> = {}

    // If slip file is attached, send via multipart FormData
    if (data.slip_file) {
      const formData = new FormData()
      if (data.paid_amount !== undefined) formData.append('paid_amount', String(data.paid_amount))
      if (data.term_number !== undefined) formData.append('term_number', String(data.term_number))
      if (data.statement_month) formData.append('statement_month', data.statement_month)
      if (data.note) formData.append('note', data.note)
      if (data.account_id) formData.append('account_id', data.account_id)
      formData.append('slip_file', data.slip_file)
      requestData = formData
      headers = { 'Content-Type': 'multipart/form-data' }
    }

    const res = await apiClient.post<{ message: string; obligation: FinancialObligation }>(
      `/finance/obligations/${id}/pay/`,
      requestData,
      { headers }
    )
    // Update store state
    const idx = obligations.value.findIndex(o => o.id === id)
    if (idx !== -1) {
      obligations.value[idx] = res.data.obligation
    }

    // Decouple overview refetch from payment mutation
    try {
      await fetchOverview()
    } catch (refreshErr) {
      console.warn('Overview refresh failed after payment:', refreshErr)
      const toast = useToastStore()
      toast.error('Payment recorded, but failed to refresh overview.', 6000, {
        label: 'Retry refresh',
        onClick: () => fetchOverview()
      })
    }

    // Cross-sync: refresh ledger accounts and cash flow if payment was linked to an account
    if (data.account_id) {
      try {
        const { useLedgerStore } = await import('./ledger')
        const ledgerStore = useLedgerStore()
        await Promise.all([ledgerStore.fetchAccounts(), ledgerStore.fetchSummary(), ledgerStore.fetchPendingSplits()])
      } catch (err) {
        console.warn('Could not sync ledger store after obligation payment:', err)
      }
    }

    return res.data
  }

  async function uploadAttachment(
    params: { obligation_id: string; file: File; file_type?: string; payment_history?: string } | string,
    file?: File,
    fileType = 'OTHER',
    paymentHistoryId?: string
  ) {
    let obligationId = ''
    let fileObj: File
    let fType = 'OTHER'
    let phId: string | undefined

    if (typeof params === 'object') {
      obligationId = params.obligation_id
      fileObj = params.file
      fType = params.file_type || 'OTHER'
      phId = params.payment_history
    } else {
      obligationId = params
      fileObj = file!
      fType = fileType
      phId = paymentHistoryId
    }

    const formData = new FormData()
    formData.append('file', fileObj)
    formData.append('file_type', fType)
    if (phId) {
      formData.append('payment_history', phId)
    }

    const res = await apiClient.post(
      `/finance/obligations/${obligationId}/upload-attachment/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    try {
      await fetchObligations()
    } catch (refreshErr) {
      console.warn('Obligations refresh failed after attachment upload:', refreshErr)
    }
    return res.data
  }

  async function deleteAttachment(attachmentId: string) {
    await apiClient.delete(`/finance/attachments/${attachmentId}/`)
    try {
      await fetchObligations()
    } catch (refreshErr) {
      console.warn('Obligations refresh failed after attachment delete:', refreshErr)
    }
  }

  async function cancelTrial(id: string) {
    const res = await apiClient.post<{ message: string; obligation: FinancialObligation }>(`/finance/obligations/${id}/cancel-trial/`)
    const idx = obligations.value.findIndex(o => o.id === id)
    if (idx !== -1) {
      obligations.value[idx] = res.data.obligation
    }
    try {
      await fetchOverview()
    } catch (refreshErr) {
      console.warn('Overview refresh failed after trial cancellation:', refreshErr)
      const toast = useToastStore()
      toast.error('Trial cancelled, but failed to refresh overview.', 6000, {
        label: 'Retry refresh',
        onClick: () => fetchOverview()
      })
    }
    return res.data
  }

  async function deleteObligation(id: string) {
    await apiClient.delete(`/finance/obligations/${id}/`)
    obligations.value = obligations.value.filter(o => o.id !== id)
    try {
      await fetchOverview()
    } catch (refreshErr) {
      console.warn('Overview refresh failed after obligation deletion:', refreshErr)
      const toast = useToastStore()
      toast.error('Record deleted, but failed to refresh overview.', 6000, {
        label: 'Retry refresh',
        onClick: () => { fetchOverview() }
      })
    }
  }

  return {
    overview,
    obligations,
    isLoading,
    isOverviewLoading,
    fetchOverview,
    fetchObligations,
    createObligation,
    updateObligation,
    payObligation,
    uploadAttachment,
    deleteAttachment,
    cancelTrial,
    deleteObligation,
  }
})
