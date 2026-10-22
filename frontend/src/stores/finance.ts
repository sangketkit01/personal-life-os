import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import type { FinancialObligation, FinancialOverview } from '../types/finance'

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
    await fetchOverview()
    return res.data
  }

  async function updateObligation(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<FinancialObligation>(`/finance/obligations/${id}/`, payload)
    const idx = obligations.value.findIndex(o => o.id === id)
    if (idx !== -1) {
      obligations.value[idx] = res.data
    }
    await fetchOverview()
    return res.data
  }

  async function payObligation(id: string, data: { paid_amount?: number; term_number?: number; note?: string; slip_file?: File; account_id?: string } = {}) {
    let requestData: any = data
    let headers: Record<string, string> = {}

    // If slip file is attached, send via multipart FormData
    if (data.slip_file) {
      const formData = new FormData()
      if (data.paid_amount !== undefined) formData.append('paid_amount', String(data.paid_amount))
      if (data.term_number !== undefined) formData.append('term_number', String(data.term_number))
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
    await fetchOverview()
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
    await fetchObligations()
    return res.data
  }

  async function deleteAttachment(attachmentId: string) {
    await apiClient.delete(`/finance/attachments/${attachmentId}/`)
    await fetchObligations()
  }

  async function cancelTrial(id: string) {
    const res = await apiClient.post<{ message: string; obligation: FinancialObligation }>(`/finance/obligations/${id}/cancel-trial/`)
    const idx = obligations.value.findIndex(o => o.id === id)
    if (idx !== -1) {
      obligations.value[idx] = res.data.obligation
    }
    await fetchOverview()
    return res.data
  }

  async function deleteObligation(id: string) {
    await apiClient.delete(`/finance/obligations/${id}/`)
    obligations.value = obligations.value.filter(o => o.id !== id)
    await fetchOverview()
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
