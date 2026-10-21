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

  async function fetchObligations(type?: string, status?: string) {
    isLoading.value = true
    try {
      const params: Record<string, string> = {}
      if (type) params.type = type
      if (status) params.status = status

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

  async function payObligation(id: string, data: { paid_amount?: number; term_number?: number; note?: string } = {}) {
    const res = await apiClient.post<{ message: string; obligation: FinancialObligation }>(`/finance/obligations/${id}/pay/`, data)
    // อัปเดตข้อมูลใน store
    const idx = obligations.value.findIndex(o => o.id === id)
    if (idx !== -1) {
      obligations.value[idx] = res.data.obligation
    }
    await fetchOverview()
    return res.data
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
    payObligation,
    cancelTrial,
    deleteObligation,
  }
})
