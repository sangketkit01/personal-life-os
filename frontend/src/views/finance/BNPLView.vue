<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- View Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Shopping Credit (BNPL)</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            REVOLVING CREDIT
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">E-commerce buy-now-pay-later credit accounts (Shopee SPayLater, LazPayLater, TikTok Shop) and sub-orders</p>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <button
          @click="router.push('/finance/bnpl/new')"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>New BNPL Line</span>
        </button>
      </div>
    </div>

    <!-- Content Section -->
    <div v-if="isLoading" class="p-12 text-center text-xs font-mono text-zinc-500">
      Loading BNPL accounts...
    </div>

    <BNPLSection
      v-else
      :obligations="accounts"
      @open-create="router.push('/finance/bnpl/new')"
      @open-pay="openPayModal"
      @open-history="openHistoryModal"
      @open-edit="openEditModal"
      @delete-order="handleDeleteOrder"
      @order-created="refreshAll"
    />

    <!-- Common Modals -->
    <CreateObligationModal
      :is-open="showCreateModal"
      @close="showCreateModal = false"
      @created="refreshAll"
    />

    <EditObligationModal
      :is-open="showEditModal"
      :obligation="selectedObligationForEdit"
      @close="showEditModal = false"
      @updated="refreshAll"
    />

    <PaymentHistoryModal
      :is-open="showHistoryModal"
      :obligation="selectedObligationForHistory"
      @close="showHistoryModal = false"
    />

    <PayModal
      :is-open="showPayModal"
      :obligation="selectedObligationForPay"
      @close="showPayModal = false"
      @paid="refreshAll"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useBNPL } from '../../composables/finance/useBNPL'
import { useToastStore } from '../../stores/toast'
import type { FinancialObligation } from '../../types/finance'
import BNPLSection from '../../components/finance/bnpl/BNPLSection.vue'
import CreateObligationModal from '../../components/finance/CreateObligationModal.vue'
import EditObligationModal from '../../components/finance/EditObligationModal.vue'
import PaymentHistoryModal from '../../components/finance/PaymentHistoryModal.vue'
import PayModal from '../../components/finance/PayModal.vue'
import { Plus } from 'lucide-vue-next'

const router = useRouter()
const { accounts, isLoading, fetchAccounts, deleteOrder } = useBNPL()
const toast = useToastStore()

const showCreateModal = ref(false)
const showEditModal = ref(false)
const showHistoryModal = ref(false)
const showPayModal = ref(false)

const selectedObligationForPay = ref<FinancialObligation | null>(null)
const selectedObligationForEdit = ref<FinancialObligation | null>(null)
const selectedObligationForHistory = ref<FinancialObligation | null>(null)

onMounted(async () => {
  await refreshAll()
})

async function refreshAll() {
  await fetchAccounts()
}

function openPayModal(ob: FinancialObligation) {
  selectedObligationForPay.value = ob
  showPayModal.value = true
}

function openEditModal(ob: FinancialObligation) {
  selectedObligationForEdit.value = ob
  showEditModal.value = true
}

function openHistoryModal(ob: FinancialObligation) {
  selectedObligationForHistory.value = ob
  showHistoryModal.value = true
}

async function handleDeleteOrder(id: string) {
  if (!confirm('Are you sure you want to delete this BNPL sub-order?')) return
  try {
    await deleteOrder(id)
    toast.info('Deleted BNPL sub-order')
    await fetchAccounts()
  } catch {
    toast.error('Failed to delete BNPL sub-order')
  }
}
</script>
