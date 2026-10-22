<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- View Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Radar Overview</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            TIMELINE & CASHFLOW
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">Command center: Fixed burn rate, upcoming settlement calendar, and early warning radar</p>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <button
          @click="showCreateModal = true"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>New Obligation</span>
        </button>
      </div>
    </div>

    <!-- Dashboard Content -->
    <div v-if="financeStore.isLoading" class="p-12 text-center text-xs font-mono text-zinc-500">
      Loading radar data...
    </div>

    <FinanceRadarDashboard
      v-else
      :obligations="financeStore.obligations"
      @switch-tab="handleSwitchTab"
      @open-pay="openPayModal"
    />

    <!-- Common Modals -->
    <CreateObligationModal
      :is-open="showCreateModal"
      @close="showCreateModal = false"
      @created="refreshAll"
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
import { useFinanceStore } from '../../stores/finance'
import type { FinancialObligation } from '../../types/finance'
import FinanceRadarDashboard from '../../components/finance/overview/FinanceRadarDashboard.vue'
import CreateObligationModal from '../../components/finance/CreateObligationModal.vue'
import PayModal from '../../components/finance/PayModal.vue'
import { Plus } from 'lucide-vue-next'

const router = useRouter()
const financeStore = useFinanceStore()

const showCreateModal = ref(false)
const showPayModal = ref(false)
const selectedObligationForPay = ref<FinancialObligation | null>(null)

onMounted(async () => {
  await refreshAll()
})

async function refreshAll() {
  await Promise.all([
    financeStore.fetchOverview(),
    financeStore.fetchObligations()
  ])
}

function handleSwitchTab(tab: string) {
  if (tab === 'INSTALLMENT') router.push('/finance/installments')
  else if (tab === 'BNPL') router.push('/finance/bnpl')
  else if (tab === 'SUBSCRIPTION') router.push('/finance/subscriptions')
  else if (tab === 'DEBT') router.push('/finance/debts')
}

function openPayModal(ob: FinancialObligation) {
  selectedObligationForPay.value = ob
  showPayModal.value = true
}
</script>