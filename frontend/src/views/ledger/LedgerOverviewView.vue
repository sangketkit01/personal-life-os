<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans pb-16">
    <!-- Header: Period Selector & Quick Actions -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Cash Flow & Multi-Account Ledger</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            REAL BALANCE & SPLITS
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Central cash management across bank accounts, cards, shared bills, and automated Radar settlements
        </p>
      </div>

      <!-- Action Buttons & Month Picker -->
      <div class="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
        <!-- Month Selector -->
        <input
          v-model="activeMonth"
          type="month"
          @change="handleMonthChange"
          class="px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-200 outline-none focus:border-zinc-700"
        />

        <button
          @click="showTransferModal = true"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors flex items-center gap-1.5"
        >
          <ArrowRightLeft class="w-3.5 h-3.5 text-zinc-400" />
          <span>Transfer</span>
        </button>

        <button
          @click="showTransactionModal = true"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>+ Record Cash Flow</span>
        </button>
      </div>
    </div>

    <!-- 4 High-Density Executive Financial Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      <!-- 1. Net Cash Flow -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 relative">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Net Cash Flow</span>
          <span :class="Number(ledgerStore.summary?.net_cash_flow || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'">
            {{ Number(ledgerStore.summary?.net_cash_flow || 0) >= 0 ? '+ Inflow' : '- Deficit' }}
          </span>
        </div>
        <div v-if="ledgerStore.isSummaryLoading" class="h-7 w-32 bg-zinc-800 animate-pulse rounded mt-2.5"></div>
        <div v-else class="mt-2.5 flex items-baseline gap-1.5">
          <span
            class="text-xl font-semibold font-mono tabular-nums"
            :class="Number(ledgerStore.summary?.net_cash_flow || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          >
            ฿{{ Number(ledgerStore.summary?.net_cash_flow || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5 font-mono">
          <span>In: ฿{{ Number(ledgerStore.summary?.total_inflow || 0).toLocaleString('en-US') }}</span>
          <span>Net Out: ฿{{ Number(ledgerStore.summary?.total_net_outflow || 0).toLocaleString('en-US') }}</span>
        </div>
      </div>

      <!-- 2. Total Liquid Cash -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 relative">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Total Liquid Cash</span>
          <span>Accounts</span>
        </div>
        <div v-if="ledgerStore.isSummaryLoading" class="h-7 w-32 bg-zinc-800 animate-pulse rounded mt-2.5"></div>
        <div v-else class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            ฿{{ Number(ledgerStore.summary?.total_liquid_balance || ledgerStore.totalLiquidCash).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5 font-mono">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>Across {{ liquidAccountsCount }} active deposit accounts</span>
        </div>
      </div>

      <!-- 3. Credit Card Outflow & Debt -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 relative">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Active Card Balance</span>
          <span>Credit</span>
        </div>
        <div v-if="ledgerStore.isSummaryLoading" class="h-7 w-32 bg-zinc-800 animate-pulse rounded mt-2.5"></div>
        <div v-else class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-300 tabular-nums">
            ฿{{ Number(ledgerStore.summary?.total_credit_debt || ledgerStore.totalCreditDebt).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5 font-mono">
          <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
          <span>Unsettled card charges</span>
        </div>
      </div>

      <!-- 4. Pending Split Receivables -->
      <RouterLink
        to="/ledger/splits"
        class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700 transition-colors block group relative"
      >
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Pending Friend Splits</span>
          <span class="text-zinc-400 group-hover:text-zinc-200">View →</span>
        </div>
        <div v-if="ledgerStore.isSummaryLoading" class="h-7 w-32 bg-zinc-800 animate-pulse rounded mt-2.5"></div>
        <div v-else class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            ฿{{ Number(ledgerStore.summary?.pending_splits_amount || ledgerStore.pendingSplitsTotal).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5 font-mono">
          <span class="w-1.5 h-1.5 rounded-full" :class="(ledgerStore.summary?.pending_splits_count || 0) > 0 ? 'bg-amber-400' : 'bg-zinc-600'" />
          <span>{{ ledgerStore.summary?.pending_splits_count || 0 }} friends awaiting reimbursement</span>
        </div>
      </RouterLink>
    </div>

    <!-- Accounts Strip: Cards & Wallets Carousel -->
    <div class="space-y-3">
      <div class="flex items-center justify-between pb-2 border-b border-zinc-800/80">
        <div class="flex items-center gap-2">
          <Wallet class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Accounts & Wallets ({{ ledgerStore.accounts.length }})
          </h2>
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="showCreateAccountModal = true"
            class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            + New Account
          </button>
          <RouterLink
            to="/ledger/accounts"
            class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors ml-2"
          >
            Manage All →
          </RouterLink>
        </div>
      </div>

      <!-- Empty State for Accounts -->
      <div
        v-if="ledgerStore.accounts.length === 0"
        class="p-8 text-center border border-dashed border-zinc-800 rounded-xl space-y-2 bg-zinc-950/40 font-mono text-xs text-zinc-500"
      >
        <Wallet class="w-6 h-6 text-zinc-600 mx-auto" />
        <p>No financial accounts or wallets added yet.</p>
        <button
          @click="showCreateAccountModal = true"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-semibold text-xs transition-colors inline-block shadow-sm"
        >
          + Add First Account
        </button>
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div
          v-for="acc in ledgerStore.accounts"
          :key="acc.id"
          class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700 transition-all flex flex-col justify-between"
        >
          <div>
            <div class="flex items-start justify-between">
              <span class="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
                {{ acc.account_type }}
              </span>
              <span v-if="acc.is_default" class="text-[9px] font-mono text-zinc-400 border border-zinc-700/60 px-1 rounded">
                Default
              </span>
            </div>
            <h3 class="text-sm font-semibold text-zinc-100 mt-2 font-sans truncate">{{ acc.name }}</h3>
            <div class="text-[10px] text-zinc-500 font-mono mt-0.5">
              {{ acc.institution_name || 'Personal Wallet' }}
              <span v-if="acc.account_number"> • {{ acc.account_number }}</span>
            </div>
          </div>

          <div class="mt-4 pt-2.5 border-t border-zinc-800/60 flex items-center justify-between">
            <span class="text-sm font-bold font-mono text-zinc-100 tabular-nums">
              ฿{{ Number(acc.current_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
            </span>
            <RouterLink
              :to="`/ledger/accounts/${acc.id}`"
              class="text-[10px] font-mono text-zinc-400 hover:text-zinc-200"
            >
              Statement →
            </RouterLink>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Transactions Ledger Table -->
    <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <Receipt class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Recent Cash Flow Activity
          </h2>
          <span class="text-[11px] font-mono text-zinc-500 ml-1">({{ ledgerStore.transactions.length }} recorded)</span>
        </div>

        <RouterLink
          to="/ledger/transactions"
          class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          View Full Ledger with Filters →
        </RouterLink>
      </div>

      <!-- Empty State -->
      <div
        v-if="ledgerStore.transactions.length === 0"
        class="p-12 text-center text-xs font-mono text-zinc-500 space-y-2"
      >
        <p>No transactions recorded for {{ activeMonth }}.</p>
        <button
          @click="showTransactionModal = true"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-medium text-xs transition-colors inline-block shadow-sm"
        >
          + Record First Transaction
        </button>
      </div>

      <!-- Table View -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs font-mono">
          <thead>
            <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[10px] uppercase text-zinc-500 tracking-wider">
              <th class="py-3 px-4">Date</th>
              <th class="py-3 px-4">Description / Merchant</th>
              <th class="py-3 px-4">Account</th>
              <th class="py-3 px-4">Category</th>
              <th class="py-3 px-4 text-right">Gross Amount</th>
              <th class="py-3 px-4 text-right">Net Share</th>
              <th class="py-3 px-4 text-right pr-4">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="tx in ledgerStore.transactions.slice(0, 15)"
              :key="tx.id"
              class="hover:bg-zinc-900/40 transition-colors"
            >
              <!-- Date -->
              <td class="py-3 px-4 text-zinc-400 whitespace-nowrap">{{ tx.transaction_date }}</td>

              <!-- Title & Split Tag -->
              <td class="py-3 px-4 font-sans font-medium text-zinc-200">
                <div class="flex items-center gap-2 flex-wrap">
                  <span>{{ tx.title }}</span>
                  <span
                    v-if="tx.is_split"
                    class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center gap-1"
                  >
                    <Users class="w-2.5 h-2.5" />
                    <span>Split ({{ tx.splits?.length || 0 }} friends)</span>
                  </span>
                  <span
                    v-if="tx.transfer_destination || tx.transfer_peer"
                    class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400"
                  >
                    Transfer
                  </span>
                </div>
              </td>

              <!-- Account -->
              <td class="py-3 px-4 text-zinc-400 font-sans">
                {{ tx.account_name || 'Account' }}
              </td>

              <!-- Category -->
              <td class="py-3 px-4 text-zinc-400 font-sans">
                <span class="px-2 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-800/80">
                  {{ tx.category_name || 'General' }}
                </span>
              </td>

              <!-- Gross Amount -->
              <td class="py-3 px-4 text-right font-mono tabular-nums font-semibold">
                <span :class="tx.transaction_type === 'INFLOW' ? 'text-emerald-400' : 'text-zinc-200'">
                  {{ tx.transaction_type === 'INFLOW' ? '+' : '-' }}฿{{ Number(tx.gross_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </span>
              </td>

              <!-- Net Share -->
              <td class="py-3 px-4 text-right font-mono tabular-nums text-zinc-400">
                ฿{{ Number(tx.net_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </td>

              <!-- Actions -->
              <td class="py-3 px-4 text-right pr-4">
                <button
                  @click="handleDeleteTransaction(tx.id)"
                  class="p-1 rounded text-zinc-600 hover:text-rose-400 transition-colors"
                  title="Delete Transaction"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modals -->
    <TransactionModal
      :is-open="showTransactionModal"
      @close="showTransactionModal = false"
      @created="handleRefresh"
    />

    <CreateAccountModal
      :is-open="showCreateAccountModal"
      @close="showCreateAccountModal = false"
      @saved="handleRefresh"
    />

    <TransferModal
      :is-open="showTransferModal"
      @close="showTransferModal = false"
      @transferred="handleRefresh"
    />

    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      @confirm="executeConfirmAction"
      @cancel="confirmModal.isOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useLedgerStore } from '../../stores/ledger'
import TransactionModal from '../../components/ledger/TransactionModal.vue'
import CreateAccountModal from '../../components/ledger/CreateAccountModal.vue'
import TransferModal from '../../components/ledger/TransferModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import {
  Wallet,
  Receipt,
  Users,
  Plus,
  ArrowRightLeft,
  Trash2
} from 'lucide-vue-next'

const ledgerStore = useLedgerStore()

const now = new Date()
const activeMonth = ref<string>(
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
)

const showTransactionModal = ref(false)
const showCreateAccountModal = ref(false)
const showTransferModal = ref(false)

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  action: () => {}
})

function executeConfirmAction() {
  confirmModal.isOpen = false
  confirmModal.action()
}

const liquidAccountsCount = computed(() => {
  return ledgerStore.accounts.filter(
    (a) => a.account_type !== 'CREDIT_CARD' && !a.is_archived
  ).length
})

onMounted(async () => {
  await Promise.all([
    ledgerStore.fetchAccounts(),
    ledgerStore.fetchCategories(),
    handleMonthChange(),
    ledgerStore.fetchPendingSplits()
  ])
})

async function handleMonthChange() {
  const [year, month] = activeMonth.value.split('-')
  const lastDay = new Date(Number(year), Number(month), 0).getDate()
  await Promise.all([
    ledgerStore.fetchSummary(activeMonth.value),
    ledgerStore.fetchTransactions({
      start_date: `${activeMonth.value}-01`,
      end_date: `${activeMonth.value}-${String(lastDay).padStart(2, '0')}`
    })
  ])
}

async function handleRefresh() {
  await Promise.all([
    ledgerStore.fetchAccounts(),
    handleMonthChange(),
    ledgerStore.fetchPendingSplits()
  ])
}

function handleDeleteTransaction(id: string) {
  confirmModal.title = 'Delete Transaction'
  confirmModal.message = 'Are you sure you want to delete this transaction? The corresponding account balance will be restored automatically.'
  confirmModal.confirmText = 'Delete Transaction'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    await ledgerStore.deleteTransaction(id)
    await handleRefresh()
  }
  confirmModal.isOpen = true
}
</script>
