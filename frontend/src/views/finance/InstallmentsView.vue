<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- View Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Installments & Contracts</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            AMORTIZATION & HP
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">Vehicle hire-purchase contracts, amortization schedules, and 0% fixed-term installments</p>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <button
          @click="router.push('/finance/installments/new')"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white active:scale-95 text-zinc-950 text-xs font-semibold transition-all flex items-center gap-1.5 shadow-sm cursor-pointer"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>New Contract</span>
        </button>
      </div>
    </div>

    <!-- Content Section -->
    <div v-if="isLoading && installments.length === 0" class="space-y-4">
      <SkeletonLoader variant="metrics" :count="3" />
      <SkeletonLoader variant="cards" :count="4" />
    </div>

    <InstallmentSection
      v-else
      :obligations="installments"
      @open-create="router.push('/finance/installments/new')"
      @select="id => router.push('/finance/installments/' + id)"
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
      :is-loading="confirmModal.isLoading"
      :error-message="confirmModal.errorMessage"
      @confirm="executeConfirmModal"
      @cancel="confirmModal.isOpen = false; confirmModal.errorMessage = ''"
    />
  </div>
</template>

<script setup lang="ts">
import SkeletonLoader from '../../components/common/SkeletonLoader.vue'
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useInstallments } from '../../composables/finance/useInstallments'
import { useToastStore } from '../../stores/toast'
import type { FinancialObligation } from '../../types/finance'
import InstallmentSection from '../../components/finance/installment/InstallmentSection.vue'
import CreateObligationModal from '../../components/finance/CreateObligationModal.vue'
import EditObligationModal from '../../components/finance/EditObligationModal.vue'
import PaymentHistoryModal from '../../components/finance/PaymentHistoryModal.vue'
import PayModal from '../../components/finance/PayModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import { Plus } from 'lucide-vue-next'

const router = useRouter()
const { installments, isLoading, fetchInstallments, deleteInstallment } = useInstallments()
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
  isLoading: false,
  errorMessage: '',
  action: async () => {}
})

async function executeConfirmModal() {
  confirmModal.isLoading = true
  confirmModal.errorMessage = ''
  try {
    await confirmModal.action()
    confirmModal.isOpen = false
  } catch (err: any) {
    confirmModal.errorMessage = err?.response?.data?.detail || err?.response?.data?.error || err?.message || 'Operation failed'
  } finally {
    confirmModal.isLoading = false
  }
}

onMounted(async () => {
  await refreshAll()
})

async function refreshAll() {
  await fetchInstallments()
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
  confirmModal.title = 'Delete Installment Contract'
  confirmModal.message = 'Are you sure you want to delete this installment contract? All amortization history will be removed.'
  confirmModal.confirmText = 'Delete Contract'
  confirmModal.isDanger = true
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    await deleteInstallment(id)
    toast.info('Deleted installment contract')
  }
  confirmModal.isOpen = true
}
</script>
