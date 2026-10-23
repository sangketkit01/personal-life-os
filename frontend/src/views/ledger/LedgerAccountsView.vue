<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans pb-16">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2 mb-2">
          <RouterLink
            to="/ledger"
            class="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft class="w-3.5 h-3.5" />
            <span>Cash Flow Ledger</span>
          </RouterLink>
          <span class="text-zinc-600">/</span>
          <span class="text-xs font-mono text-zinc-300">Accounts & Wallets</span>
        </div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Accounts & Wallets</h1>
        </div>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <button
          @click="showTransferModal = true"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 hover:border-zinc-700 border border-zinc-800 text-xs font-medium text-zinc-300 transition-all active:scale-[0.98] flex items-center gap-1.5"
        >
          <ArrowRightLeft class="w-3.5 h-3.5 text-zinc-400" />
          <span>Transfer</span>
        </button>

        <button
          @click="openCreateAccount"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-all active:scale-[0.98] flex items-center gap-1.5 shadow-sm hover:shadow-white/10"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>+ Add Account</span>
        </button>
      </div>
    </div>

    <!-- Summary KPI Strip -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Total Liquid Cash</span>
        <div class="text-2xl font-bold text-zinc-100 mt-2 tabular-nums tracking-tight">
          ฿{{ Number(ledgerStore.totalLiquidCash).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5">Checking, savings, and cash reserves</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Total Credit Card Balance</span>
        <div class="text-2xl font-bold text-zinc-200 mt-2 tabular-nums tracking-tight">
          ฿{{ Number(ledgerStore.totalCreditDebt).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5">Outstanding balances awaiting billing settlement</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Total Accounts</span>
        <div class="text-2xl font-bold text-zinc-100 mt-2 tabular-nums tracking-tight">
          {{ ledgerStore.accounts.length }} accounts
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5">Banks, portfolios, cards, and wallets</span>
      </div>
    </div>

    <!-- Accounts Grid -->
    <div
      v-if="ledgerStore.accounts.length === 0"
      class="p-16 rounded-xl bg-zinc-900/20 border border-dashed border-zinc-800 text-center space-y-3 font-mono text-xs text-zinc-500"
    >
      <Wallet class="w-8 h-8 text-zinc-600 mx-auto" />
      <p>No financial accounts or wallets added yet.</p>
      <button
        @click="openCreateAccount"
        class="px-4 py-2 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-semibold text-xs transition-colors inline-block shadow-sm"
      >
        + Add First Account
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="acc in ledgerStore.accounts"
        :key="acc.id"
        class="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200 flex flex-col justify-between space-y-4 group"
      >
        <div>
          <!-- Top Row -->
          <div class="flex items-start justify-between">
            <span class="text-[9px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 font-semibold group-hover:border-zinc-700 transition-colors">
              {{ acc.account_type }}
            </span>

            <div class="flex items-center gap-1.5">
              <span v-if="acc.is_default" class="text-[9px] font-mono text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 px-1.5 rounded font-semibold">
                Default
              </span>
              <button
                @click="openEditAccount(acc)"
                class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-100 hover:bg-zinc-800 active:scale-[0.95] transition-all"
                title="Edit Account"
              >
                <Edit2 class="w-3.5 h-3.5" />
              </button>
              <button
                @click="handleRecalculate(acc.id)"
                class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-100 hover:bg-zinc-800 active:scale-[0.95] transition-all"
                title="Recalculate balance from history"
              >
                <RefreshCw class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- Account Identity -->
          <h3 class="text-base font-semibold text-zinc-100 mt-2 font-sans group-hover:text-white transition-colors">{{ acc.name }}</h3>
          <div class="text-xs text-zinc-400 font-mono mt-0.5">
            {{ acc.institution_name || 'Personal Wallet' }}
            <span v-if="acc.account_number"> • {{ acc.account_number }}</span>
          </div>
        </div>

        <!-- Balance Section -->
        <div class="space-y-2 pt-2 border-t border-zinc-800/60 font-mono">
          <div class="flex justify-between items-baseline">
            <span class="text-xs text-zinc-400">Current Balance:</span>
            <span class="text-lg font-bold text-zinc-100 tabular-nums">
              ฿{{ Number(acc.current_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
            </span>
          </div>

          <!-- Credit Card Limit & Utilization Meter -->
          <div v-if="acc.credit_limit && Number(acc.credit_limit) > 0" class="space-y-1.5 pt-1">
            <div class="flex justify-between text-[11px] text-zinc-400">
              <span>Limit: ฿{{ Number(acc.credit_limit).toLocaleString('en-US') }}</span>
              <span class="font-bold text-zinc-300">
                {{ Math.min(100, Math.round((Math.abs(Number(acc.current_balance || 0)) / Number(acc.credit_limit)) * 100)) }}% used
              </span>
            </div>
            <div class="w-full bg-zinc-800/80 h-1.5 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-300"
                :class="(Math.abs(Number(acc.current_balance || 0)) / Number(acc.credit_limit)) > 0.8 ? 'bg-amber-400' : 'bg-emerald-400'"
                :style="{ width: `${Math.min(100, (Math.abs(Number(acc.current_balance || 0)) / Number(acc.credit_limit)) * 100)}%` }"
              />
            </div>
          </div>

          <div class="pt-2 flex items-center justify-between text-xs">
            <span class="text-[10px] text-zinc-500">{{ acc.transaction_count || 0 }} items</span>
            <RouterLink
              :to="`/ledger/accounts/${acc.id}`"
              class="text-xs text-zinc-300 hover:text-white font-medium flex items-center gap-1 hover:underline transition-colors"
            >
              <span>View Statement</span>
              <ArrowRight class="w-3.5 h-3.5 text-zinc-400" />
            </RouterLink>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <CreateAccountModal
      :is-open="showCreateModal"
      :editing-account="editingAccount"
      @close="showCreateModal = false"
      @saved="ledgerStore.fetchAccounts"
    />

    <TransferModal
      :is-open="showTransferModal"
      @close="showTransferModal = false"
      @transferred="ledgerStore.fetchAccounts"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLedgerStore } from '../../stores/ledger'
import { useToastStore } from '../../stores/toast'
import type { LedgerAccount } from '../../types/ledger'
import CreateAccountModal from '../../components/ledger/CreateAccountModal.vue'
import TransferModal from '../../components/ledger/TransferModal.vue'
import {
  ArrowLeft,
  Plus,
  ArrowRightLeft,
  Edit2,
  RefreshCw,
  ArrowRight,
  Wallet
} from 'lucide-vue-next'

const ledgerStore = useLedgerStore()
const toast = useToastStore()
const showCreateModal = ref(false)
const showTransferModal = ref(false)
const editingAccount = ref<LedgerAccount | null>(null)

onMounted(async () => {
  await ledgerStore.fetchAccounts()
})

function openCreateAccount() {
  editingAccount.value = null
  showCreateModal.value = true
}

function openEditAccount(acc: LedgerAccount) {
  editingAccount.value = acc
  showCreateModal.value = true
}

async function handleRecalculate(id: string) {
  try {
    await ledgerStore.recalculateBalance(id)
    toast.success('Account balance recalculated and verified')
  } catch (err: any) {
    toast.error('Failed to recalculate balance')
  }
}
</script>
