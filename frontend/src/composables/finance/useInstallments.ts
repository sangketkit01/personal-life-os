import { ref } from 'vue'
import apiClient from '../../api/client'
import type { FinancialObligation } from '../../types/finance'

export interface InstallmentScheduleItem {
  term_number: number
  total_terms: number
  due_date: string
  installment_amount: number
  principal: number
  interest: number
  remaining_principal: number
  status: 'PAID' | 'DUE' | 'UPCOMING'
}

export interface InstallmentScheduleResponse {
  obligation_id: string
  title: string
  total_terms: number
  current_term: number
  monthly_installment: number
  summary: any
  schedule: InstallmentScheduleItem[]
}

export function useInstallments() {
  const installments = ref<FinancialObligation[]>([])
  const isLoading = ref(false)
  const isActionLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchInstallments(params?: {
    status?: string
    search?: string
    ordering?: string
  }) {
    isLoading.value = true
    error.value = null
    try {
      const res = await apiClient.get('/finance/obligations/', {
        params: {
          type: 'INSTALLMENT',
          parent: 'none',
          status: params?.status || undefined,
          search: params?.search || undefined,
          ordering: params?.ordering || '-created_at'
        }
      })
      const data = res.data
      installments.value = Array.isArray(data) ? data : (data.results || [])
      return installments.value
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to fetch installments'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchSchedule(id: string): Promise<InstallmentScheduleResponse> {
    isActionLoading.value = true
    try {
      const res = await apiClient.get(`/finance/obligations/${id}/schedule/`)
      return res.data
    } finally {
      isActionLoading.value = false
    }
  }

  async function payInstallment(id: string, payload: {
    paid_amount?: number
    term_number?: number
    note?: string
    slip_file?: File
    account_id?: string
  }) {
    isActionLoading.value = true
    try {
      const formData = new FormData()
      if (payload.paid_amount !== undefined) formData.append('paid_amount', payload.paid_amount.toString())
      if (payload.term_number !== undefined) formData.append('term_number', payload.term_number.toString())
      if (payload.note) formData.append('note', payload.note)
      if (payload.slip_file) formData.append('slip_file', payload.slip_file)
      if (payload.account_id) formData.append('account_id', payload.account_id)

      const res = await apiClient.post(`/finance/obligations/${id}/pay/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      await fetchInstallments()
      return res.data
    } finally {
      isActionLoading.value = false
    }
  }

  async function fetchInstallmentById(id: string): Promise<FinancialObligation> {
    isActionLoading.value = true
    try {
      const res = await apiClient.get(`/finance/obligations/${id}/`)
      return res.data
    } finally {
      isActionLoading.value = false
    }
  }

  async function createInstallment(payload: Partial<FinancialObligation>): Promise<FinancialObligation> {
    isActionLoading.value = true
    try {
      const res = await apiClient.post('/finance/obligations/', payload)
      return res.data
    } finally {
      isActionLoading.value = false
    }
  }

  async function updateInstallment(id: string, payload: Partial<FinancialObligation>): Promise<FinancialObligation> {
    isActionLoading.value = true
    try {
      const res = await apiClient.patch(`/finance/obligations/${id}/`, payload)
      return res.data
    } finally {
      isActionLoading.value = false
    }
  }

  async function uploadAttachment(obligationId: string, file: File, fileType = 'CONTRACT') {
    isActionLoading.value = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('file_type', fileType)
      const res = await apiClient.post(`/finance/obligations/${obligationId}/upload-attachment/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return res.data
    } finally {
      isActionLoading.value = false
    }
  }

  async function deleteAttachment(attachmentId: string) {
    isActionLoading.value = true
    try {
      await apiClient.delete(`/finance/attachments/${attachmentId}/`)
    } finally {
      isActionLoading.value = false
    }
  }

  async function deleteInstallment(id: string) {
    isActionLoading.value = true
    try {
      await apiClient.delete(`/finance/obligations/${id}/`)
      installments.value = installments.value.filter(i => i.id !== id)
    } finally {
      isActionLoading.value = false
    }
  }

  return {
    installments,
    isLoading,
    isActionLoading,
    error,
    fetchInstallments,
    fetchInstallmentById,
    fetchSchedule,
    createInstallment,
    updateInstallment,
    payInstallment,
    deleteInstallment,
    uploadAttachment,
    deleteAttachment
  }
}
