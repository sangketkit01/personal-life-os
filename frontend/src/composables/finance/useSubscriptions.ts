import { ref } from 'vue'
import apiClient from '../../api/client'
import type { FinancialObligation, ObligationAttachmentItem, PaymentHistoryItem } from '../../types/finance'

export interface CreateSubscriptionPayload {
  title: string
  type: 'SUBSCRIPTION' | 'FREE_TRIAL'
  amount: number
  currency?: string
  due_date?: string
  billing_day?: number
  metadata: {
    plan_name?: string
    billing_cycle?: 'MONTHLY' | 'YEARLY' | 'QUARTERLY' | 'WEEKLY'
    account_email?: string
    payment_method?: string
    category?: string
    cancel_url?: string
    cancel_steps?: string
    alert_days_before?: number
    auto_renew_cost?: number
    notes?: string
  }
}

export function useSubscriptions() {
  const subscriptions = ref<FinancialObligation[]>([])
  const currentSubscription = ref<FinancialObligation | null>(null)
  const paymentHistories = ref<PaymentHistoryItem[]>([])
  const attachments = ref<ObligationAttachmentItem[]>([])
  const isLoading = ref(false)
  const isActionLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchSubscriptions(params?: {
    type?: 'ALL' | 'SUBSCRIPTION' | 'FREE_TRIAL'
    status?: string
    search?: string
  }) {
    isLoading.value = true
    error.value = null
    try {
      const qParams: Record<string, string> = {
        ordering: 'due_date'
      }
      if (params?.type && params.type !== 'ALL') {
        qParams.type = params.type
      }
      if (params?.status) {
        qParams.status = params.status
      }
      if (params?.search) {
        qParams.search = params.search
      }

      const res = await apiClient.get('/finance/obligations/', { params: qParams })
      const data = res.data
      const rawList: FinancialObligation[] = Array.isArray(data) ? data : (data.results || [])
      subscriptions.value = rawList.filter(o => o.type === 'SUBSCRIPTION' || o.type === 'FREE_TRIAL')
      return subscriptions.value
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to fetch subscriptions'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchSubscription(id: string) {
    isLoading.value = true
    error.value = null
    try {
      const res = await apiClient.get(`/finance/obligations/${id}/`)
      currentSubscription.value = res.data
      attachments.value = res.data.attachments || []

      // Also fetch payment histories
      try {
        const payRes = await apiClient.get(`/finance/obligations/${id}/payments/`)
        paymentHistories.value = payRes.data || []
      } catch {
        paymentHistories.value = res.data.payment_histories || []
      }

      return currentSubscription.value
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to load subscription dossier'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createSubscription(payload: CreateSubscriptionPayload) {
    isActionLoading.value = true
    error.value = null
    try {
      const res = await apiClient.post('/finance/obligations/', {
        title: payload.title,
        type: payload.type,
        amount: payload.amount,
        currency: payload.currency || 'THB',
        direction: 'OUTFLOW',
        status: 'ACTIVE',
        due_date: payload.due_date || null,
        billing_day: payload.billing_day || null,
        metadata: payload.metadata
      })
      await fetchSubscriptions()
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to create subscription'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function updateSubscription(id: string, payload: Partial<FinancialObligation>) {
    isActionLoading.value = true
    error.value = null
    try {
      const res = await apiClient.patch(`/finance/obligations/${id}/`, payload)
      if (currentSubscription.value?.id === id) {
        currentSubscription.value = res.data
      }
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to update subscription'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function renewSubscription(
    id: string,
    paidAmount?: number,
    note?: string,
    slipFile?: File,
    accountId?: string,
    driveData?: {
      drive_file_id?: string
      drive_view_link?: string
      drive_download_link?: string
      file_name?: string
      file_size?: number
    }
  ) {
    isActionLoading.value = true
    error.value = null
    try {
      const payload: Record<string, any> = {}
      if (paidAmount !== undefined && paidAmount !== null) payload.paid_amount = paidAmount
      if (note) payload.note = note
      if (accountId) payload.account_id = accountId
      if (driveData) {
        if (driveData.drive_file_id) payload.drive_file_id = driveData.drive_file_id
        if (driveData.drive_view_link) payload.drive_view_link = driveData.drive_view_link
        if (driveData.drive_download_link) payload.drive_download_link = driveData.drive_download_link
        if (driveData.file_name) payload.file_name = driveData.file_name
        if (driveData.file_size) payload.file_size = driveData.file_size
      }

      if (slipFile) {
        const formData = new FormData()
        Object.entries(payload).forEach(([k, v]) => formData.append(k, String(v)))
        formData.append('slip_file', slipFile)
        const res = await apiClient.post(`/finance/obligations/${id}/pay/`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        await fetchSubscription(id)
        return res.data
      }

      const res = await apiClient.post(`/finance/obligations/${id}/pay/`, payload)
      await fetchSubscription(id)
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to record subscription payment'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function cancelTrial(id: string) {
    isActionLoading.value = true
    error.value = null
    try {
      const res = await apiClient.post(`/finance/obligations/${id}/cancel-trial/`)
      if (currentSubscription.value?.id === id) {
        currentSubscription.value = res.data.obligation
      }
      await fetchSubscriptions()
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to cancel trial'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function convertToSubscription(id: string, payload?: { billing_cycle?: string; amount?: number }) {
    isActionLoading.value = true
    error.value = null
    try {
      const res = await apiClient.post(`/finance/obligations/${id}/convert-to-subscription/`, payload || {})
      if (currentSubscription.value?.id === id) {
        currentSubscription.value = res.data.obligation
      }
      await fetchSubscriptions()
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to convert trial'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function uploadDocument(id: string, file: File, fileType: string = 'OTHER') {
    isActionLoading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('file_type', fileType)

      const res = await apiClient.post(`/finance/obligations/${id}/upload-attachment/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      attachments.value.unshift(res.data)
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to upload document'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  async function deleteSubscription(id: string) {
    isActionLoading.value = true
    error.value = null
    try {
      await apiClient.delete(`/finance/obligations/${id}/`)
      subscriptions.value = subscriptions.value.filter(s => s.id !== id)
      if (currentSubscription.value?.id === id) {
        currentSubscription.value = null
      }
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to delete subscription'
      throw err
    } finally {
      isActionLoading.value = false
    }
  }

  return {
    subscriptions,
    currentSubscription,
    paymentHistories,
    attachments,
    isLoading,
    isActionLoading,
    error,
    fetchSubscriptions,
    fetchSubscription,
    createSubscription,
    updateSubscription,
    renewSubscription,
    cancelTrial,
    convertToSubscription,
    uploadDocument,
    deleteSubscription
  }
}
