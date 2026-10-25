<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- View Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Two-Way Debt Ledger</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            LIABILITIES & DEBTORS
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">Track liabilities payable, peer debts receivable, and payment reminders</p>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <button
          @click="router.push('/finance/debts/new')"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white active:scale-95 text-zinc-950 text-xs font-semibold transition-all flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>New Debt Entry</span>
        </button>
      </div>
    </div>

    <!-- Content Section -->
    <div v-if="isLoading && debts.length === 0" class="space-y-4">
      <SkeletonLoader variant="metrics" :count="3" />
      <SkeletonLoader variant="cards" :count="4" />
    </div>

    <DebtSection
      v-else
      :obligations="debts"
      @open-create="router.push('/finance/debts/new')"
      @open-pay="openPayModal"
      @open-history="openHistoryModal"
      @open-edit="openEditModal"
      @delete="handleDelete"
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

    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      @confirm="executeConfirmModal"
      @cancel="confirmModal.isOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import SkeletonLoader from '../../components/common/SkeletonLoader.vue'
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDebts } from '../../composables/finance/useDebts'
import { useToastStore } from '../../stores/toast'
import type { FinancialObligation } from '../../types/finance'
import DebtSection from '../../components/finance/debt/DebtSection.vue'
import CreateObligationModal from '../../components/finance/CreateObligationModal.vue'
import EditObligationModal from '../../components/finance/EditObligationModal.vue'
import PaymentHistoryModal from '../../components/finance/PaymentHistoryModal.vue'
import PayModal from '../../components/finance/PayModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import { Plus } from 'lucide-vue-next'

const router = useRouter()
const { debts, isLoading, fetchDebts, deleteDebt } = useDebts()
const toast = useToastStore()

const showCreateModal = ref(false)
const showEditModal = ref(false)
const showHistoryModal = ref(false)
const showPayModal = ref(false)

const selectedObligationForPay = ref<FinancialObligation | null>(null)
const selectedObligationForEdit = ref<FinancialObligation | null>(null)
const selectedObligationForHistory = ref<FinancialObligation | null>(null)

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  action: () => {}
})

function executeConfirmModal() {
  confirmModal.isOpen = false
  confirmModal.action()
}

onMounted(async () => {
  await refreshAll()
})

async function refreshAll() {
  await fetchDebts()
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

function handleDelete(id: string) {
  confirmModal.title = 'Delete Debt Record'
  confirmModal.message = 'Are you sure you want to delete this debt record? All repayment logs will be removed.'
  confirmModal.confirmText = 'Delete Debt'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await deleteDebt(id)
      toast.info('Deleted debt record')
    } catch {
      toast.error('Failed to delete debt record')
    }
  }
  confirmModal.isOpen = true
}
</script>
