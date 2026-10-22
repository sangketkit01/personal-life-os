<template>
  <div class="max-w-7xl mx-auto space-y-6 font-sans">
    <!-- Top Bar: Back Link, Account Identity & Master Actions -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          @click="router.push('/finance/bnpl')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Shopping Credit Master Overview"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>

        <div>
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 font-semibold">
              {{ account?.metadata?.provider || 'BNPL FACILITY' }}
            </span>
            <h1 class="text-lg font-semibold text-zinc-100 tracking-tight font-sans">
              {{ account?.title || 'Account Dossier' }}
            </h1>
            <span
              class="text-[9px] font-mono px-2 py-0.2 rounded border uppercase font-medium"
              :class="account?.status === 'ACTIVE' ? 'bg-zinc-900 text-zinc-300 border-zinc-700' : 'bg-zinc-900 text-zinc-500 border-zinc-800'"
            >
              {{ account?.status || 'ACTIVE' }}
            </span>
          </div>
          <div class="flex flex-wrap items-center gap-3 text-xs text-zinc-500 font-mono mt-0.5">
            <span v-if="account?.metadata?.account_number">Ref: {{ account.metadata.account_number }}</span>
            <span>Cut-off: Day {{ account?.metadata?.cutoff_day || 25 }}</span>
            <span>Due: Day {{ account?.metadata?.due_day || 10 }}</span>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex flex-wrap items-center gap-2 self-start sm:self-auto">
        <button
          @click="showEditModal = true"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Edit Facility Parameters"
        >
          <Edit2 class="w-4 h-4" />
        </button>

        <button
          @click="confirmDeleteAccount"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-500 hover:text-rose-400 transition-colors"
          title="Delete Account"
        >
          <Trash2 class="w-4 h-4" />
        </button>

        <button
          @click="router.push(`/finance/bnpl/${accountId}/new-order`)"
          class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-100 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>New Order</span>
        </button>

        <button
          @click="openPayStatementModal"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <CreditCard class="w-3.5 h-3.5 text-zinc-950" />
          <span>Pay Bill (฿{{ Number(account?.summary?.current_bill_amount || 0).toLocaleString('en-US') }})</span>
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="p-16 text-center text-xs font-mono text-zinc-500">
      Loading account dossier...
    </div>

    <div v-else-if="account" class="space-y-6">
      <!-- 4 Key High-Contrast Metrics Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <!-- Card 1: Approved Limit -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Approved Limit</span>
          <div class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            ฿{{ Number(account.metadata?.credit_limit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">Max revolving ceiling</span>
        </div>

        <!-- Card 2: Used Debt Balance -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono uppercase text-zinc-500 block">Total In-Use Debt</span>
            <span class="text-[10px] font-mono text-zinc-400">
              {{ account.summary?.utilization_pct || 0 }}% used
            </span>
          </div>
          <div class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            ฿{{ Number(account.summary?.total_remaining_debt || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </div>
          <!-- Gauge bar -->
          <div class="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden mt-1.5">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="(account.summary?.utilization_pct || 0) > 85 ? 'bg-rose-500/80' : 'bg-zinc-300'"
              :style="{ width: `${Math.min(100, Number(account.summary?.utilization_pct || 0))}%` }"
            />
          </div>
        </div>

        <!-- Card 3: Available Buying Power -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Available Power</span>
          <div class="text-xl font-semibold font-mono text-emerald-400 tabular-nums">
            ฿{{ Number(account.summary?.available_credit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">Remaining credit line</span>
        </div>

        <!-- Card 4: Statement Bill Due -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono uppercase text-zinc-500 block">Cycle Bill Due</span>
            <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
              Day {{ account.metadata?.due_day || 10 }}
            </span>
          </div>
          <div class="text-xl font-semibold font-mono text-rose-400 tabular-nums">
            ฿{{ Number(account.summary?.current_bill_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">
            {{ activeSubOrders.length }} active order installments
          </span>
        </div>
      </div>

      <!-- Segmented Workspace Tabs -->
      <div class="border-b border-zinc-800/80">
        <div class="flex items-center gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="px-4 py-2 text-xs font-mono transition-colors border-b-2 flex items-center gap-2"
            :class="[
              activeTab === tab.id
                ? 'border-zinc-200 text-zinc-100 font-semibold bg-zinc-900/30'
                : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/20'
            ]"
          >
            <component :is="tab.icon" class="w-3.5 h-3.5" />
            <span>{{ tab.label }}</span>
            <span
              v-if="tab.badge"
              class="px-1.5 py-0.2 rounded text-[10px] font-mono bg-zinc-900 border border-zinc-800 text-zinc-400"
            >
              {{ tab.badge }}
            </span>
          </button>
        </div>
      </div>

      <!-- TAB 1: STATEMENT RECONCILIATION -->
      <div v-if="activeTab === 'STATEMENT'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-5">
          <!-- Statement Summary Banner -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/60">
            <div>
              <span class="text-[10px] font-mono uppercase text-zinc-500 block">Statement Billing Cycle</span>
              <h2 class="text-sm font-semibold text-zinc-100 font-sans mt-0.5">
                Current Consolidated Monthly Bill
              </h2>
              <p class="text-xs text-zinc-400 mt-1">
                Aggregates all installment terms closing on Day {{ account.metadata?.cutoff_day || 25 }}, payable by Day {{ account.metadata?.due_day || 10 }}.
              </p>
            </div>

            <div class="flex items-center gap-3">
              <div class="text-right font-mono">
                <span class="text-[10px] text-zinc-500 uppercase block">Total Due</span>
                <span class="text-base font-semibold text-rose-400 tabular-nums">
                  ฿{{ Number(account.summary?.current_bill_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </span>
              </div>
              <button
                @click="openPayStatementModal"
                class="px-4 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm"
              >
                <Check class="w-3.5 h-3.5" />
                <span>Pay Statement Bill</span>
              </button>
            </div>
          </div>

          <!-- Active Sub-Orders Line Items Breakdown -->
          <div class="space-y-2">
            <h3 class="text-xs font-mono uppercase tracking-wider text-zinc-400 font-semibold">
              Line Items Due in Current Statement ({{ activeSubOrders.length }})
            </h3>

            <div v-if="activeSubOrders.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500 bg-zinc-950/40 rounded-lg border border-zinc-800">
              No orders due in current statement cycle.
            </div>

            <div v-else class="rounded-lg border border-zinc-800 overflow-hidden bg-zinc-950/60">
              <table class="w-full text-left text-xs font-mono">
                <thead>
                  <tr class="border-b border-zinc-800 text-[10px] text-zinc-500 uppercase tracking-wider bg-zinc-950">
                    <th class="py-2.5 pl-4">Purchase Item / Merchant</th>
                    <th class="py-2.5">Term Due</th>
                    <th class="py-2.5 text-right">Term Amount</th>
                    <th class="py-2.5 text-right">Remaining Order Debt</th>
                    <th class="py-2.5 text-right pr-4">Order Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-zinc-800/60">
                  <tr
                    v-for="order in activeSubOrders"
                    :key="order.id"
                    class="hover:bg-zinc-900/30 transition-colors"
                  >
                    <td class="py-2.5 pl-4">
                      <div class="font-medium text-zinc-200">{{ order.title }}</div>
                      <div class="text-[10px] text-zinc-500">
                        {{ order.metadata?.store || 'Direct Purchase' }}
                        <span v-if="order.metadata?.order_number"> • {{ order.metadata.order_number }}</span>
                      </div>
                    </td>
                    <td class="py-2.5 text-zinc-300">
                      Term {{ (order.metadata?.current_term || 0) + 1 }} of {{ order.metadata?.total_terms || 1 }}
                    </td>
                    <td class="py-2.5 text-right font-semibold text-rose-400 tabular-nums">
                      ฿{{ Number(order.amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                    </td>
                    <td class="py-2.5 text-right text-zinc-400 tabular-nums">
                      ฿{{ Number(getOrderRemainingDebt(order)).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                    </td>
                    <td class="py-2.5 text-right pr-4">
                      <span class="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-700 text-zinc-300">
                        INCLUDED IN BILL
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 2: SUB-ORDERS LEDGER -->
      <div v-if="activeTab === 'ORDERS'" class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/80">
          <div class="flex items-center gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-lg">
            <button
              v-for="tab in ['ALL', 'ACTIVE', 'COMPLETED']"
              :key="tab"
              @click="ordersFilter = tab as any"
              class="px-2.5 py-1 rounded text-xs font-mono transition-colors"
              :class="ordersFilter === tab ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
            >
              {{ tab }}
            </button>
          </div>

          <button
            @click="router.push(`/finance/bnpl/${accountId}/new-order`)"
            class="px-3 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm self-start sm:self-auto"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>Add Purchase Order</span>
          </button>
        </div>

        <div v-if="filteredSubOrders.length === 0" class="p-12 text-center text-xs font-mono text-zinc-500 bg-zinc-900/20 rounded-xl border border-zinc-800 space-y-2">
          <p>No purchase orders matching filter.</p>
          <button
            @click="router.push(`/finance/bnpl/${accountId}/new-order`)"
            class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-sans text-xs transition-colors"
          >
            + Create First Purchase Order
          </button>
        </div>

        <div v-else class="rounded-xl border border-zinc-800/80 overflow-hidden bg-zinc-900/30 shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs font-mono">
              <thead>
                <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-950/40">
                  <th class="py-2.5 pl-4">Order / Item Name</th>
                  <th class="py-2.5">Store / Platform</th>
                  <th class="py-2.5">Date</th>
                  <th class="py-2.5">Term Progress</th>
                  <th class="py-2.5 text-right">Monthly Installment</th>
                  <th class="py-2.5 text-right">Remaining Balance</th>
                  <th class="py-2.5">Status</th>
                  <th class="py-2.5 text-right pr-4">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/50">
                <tr
                  v-for="order in filteredSubOrders"
                  :key="order.id"
                  class="hover:bg-zinc-900/40 transition-colors"
                >
                  <td class="py-3 pl-4">
                    <div class="font-medium text-zinc-200">{{ order.title }}</div>
                    <div v-if="order.metadata?.order_number" class="text-[10px] text-zinc-500">
                      #{{ order.metadata.order_number }}
                    </div>
                  </td>
                  <td class="py-3 text-zinc-400">
                    {{ order.metadata?.store || '-' }}
                  </td>
                  <td class="py-3 text-zinc-500">
                    {{ order.metadata?.order_date || (order.created_at ? new Date(order.created_at).toLocaleDateString('en-GB') : '-') }}
                  </td>
                  <td class="py-3">
                    <div class="space-y-1">
                      <div class="flex items-center justify-between text-[10px] text-zinc-400">
                        <span>{{ order.metadata?.current_term || 0 }} of {{ order.metadata?.total_terms || 1 }}</span>
                        <span>{{ Math.round(((order.metadata?.current_term || 0) / (order.metadata?.total_terms || 1)) * 100) }}%</span>
                      </div>
                      <div class="w-24 bg-zinc-800 h-1 rounded-full overflow-hidden">
                        <div
                          class="h-full bg-zinc-300 rounded-full"
                          :style="{ width: `${Math.min(100, ((order.metadata?.current_term || 0) / (order.metadata?.total_terms || 1)) * 100)}%` }"
                        />
                      </div>
                    </div>
                  </td>
                  <td class="py-3 text-right font-semibold text-rose-400 tabular-nums">
                    ฿{{ Number(order.amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-3 text-right text-zinc-300 tabular-nums font-semibold">
                    ฿{{ Number(getOrderRemainingDebt(order)).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-3">
                    <span
                      class="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border"
                      :class="order.status === 'ACTIVE' ? 'bg-zinc-900 text-zinc-300 border-zinc-700' : 'bg-zinc-900 text-zinc-500 border-zinc-800'"
                    >
                      {{ order.status }}
                    </span>
                  </td>
                  <td class="py-3 text-right pr-4">
                    <button
                      @click="handleDeleteOrder(order.id)"
                      class="p-1 rounded text-zinc-500 hover:text-rose-400 transition-colors"
                      title="Delete Order"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 3: DOCUMENT & STATEMENT VAULT -->
      <div v-if="activeTab === 'DOCS'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/60">
            <div>
              <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Document & e-Statement Vault
              </h3>
              <p class="text-xs text-zinc-500 mt-0.5">
                Upload official monthly PDF statements, billing app screenshots, and receipts.
              </p>
            </div>

            <!-- Upload File Trigger -->
            <label class="px-3.5 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs font-mono transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm">
              <Upload class="w-3.5 h-3.5 text-zinc-400" />
              <span>{{ isActionLoading ? 'Uploading...' : 'Upload Document' }}</span>
              <input
                type="file"
                class="hidden"
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                @change="handleFileUpload"
              />
            </label>
          </div>

          <!-- Attachments List -->
          <div v-if="!account.attachments || account.attachments.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500 bg-zinc-950/40 rounded-lg border border-zinc-800">
            No uploaded statement documents or screenshots found.
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div
              v-for="att in account.attachments"
              :key="att.id"
              class="p-3.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 flex items-center justify-between font-mono text-xs hover:border-zinc-700 transition-colors"
            >
              <div class="flex items-center gap-2.5 truncate">
                <FileText class="w-4 h-4 text-zinc-400 shrink-0" />
                <div class="truncate">
                  <a
                    :href="att.file_url || att.file"
                    target="_blank"
                    class="text-zinc-200 hover:underline truncate block font-medium"
                  >
                    {{ att.file_name || 'Attached Statement Document' }}
                  </a>
                  <span class="text-[10px] text-zinc-500">
                    {{ att.file_size ? `${Math.round(att.file_size / 1024)} KB` : '' }} • {{ new Date(att.uploaded_at).toLocaleDateString('en-GB') }}
                  </span>
                </div>
              </div>

              <div class="flex items-center gap-1.5">
                <a
                  :href="att.file_url || att.file"
                  target="_blank"
                  download
                  class="p-1 rounded text-zinc-400 hover:text-white transition-colors"
                  title="Download File"
                >
                  <Download class="w-3.5 h-3.5" />
                </a>
                <button
                  @click="handleDeleteAttachment(att.id)"
                  class="p-1 rounded text-zinc-500 hover:text-rose-400 transition-colors"
                  title="Delete Document"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 4: PAYMENT HISTORY TIMELINE -->
      <div v-if="activeTab === 'HISTORY'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/60">
            <div>
              <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Historical Statement Settlements
              </h3>
              <p class="text-xs text-zinc-500 mt-0.5">
                Audit log of all monthly cycle payments made to this revolving facility.
              </p>
            </div>
            <span class="text-[10px] font-mono text-zinc-500">
              {{ account.payment_histories?.length || 0 }} settlement records
            </span>
          </div>

          <div v-if="!account.payment_histories || account.payment_histories.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500 bg-zinc-950/40 rounded-lg border border-zinc-800">
            No payment history recorded for this credit line yet.
          </div>

          <div v-else class="rounded-lg border border-zinc-800 overflow-hidden bg-zinc-950/60">
            <table class="w-full text-left text-xs font-mono">
              <thead>
                <tr class="border-b border-zinc-800 text-[10px] text-zinc-500 uppercase tracking-wider bg-zinc-950">
                  <th class="py-2.5 pl-4">Payment Timestamp</th>
                  <th class="py-2.5 text-right">Settled Amount</th>
                  <th class="py-2.5">Notes & Receipt Reference</th>
                  <th class="py-2.5 text-right pr-4">Slip Attachment</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/60">
                <tr
                  v-for="p in account.payment_histories"
                  :key="p.id"
                  class="hover:bg-zinc-900/30 transition-colors"
                >
                  <td class="py-2.5 pl-4 text-zinc-300">
                    {{ new Date(p.paid_at).toLocaleString('en-GB') }}
                  </td>
                  <td class="py-2.5 text-right font-semibold text-emerald-400 tabular-nums">
                    ฿{{ Number(p.paid_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-2.5 text-zinc-400">
                    {{ p.note || 'Monthly statement payoff' }}
                  </td>
                  <td class="py-2.5 text-right pr-4">
                    <span v-if="p.attachments && p.attachments.length > 0" class="text-zinc-300">
                      <a :href="p.attachments[0].file_url || p.attachments[0].file" target="_blank" class="hover:underline flex items-center justify-end gap-1 text-[11px]">
                        <FileText class="w-3 h-3 text-zinc-400" />
                        <span>Slip</span>
                      </a>
                    </span>
                    <span v-else class="text-[10px] text-zinc-600">None</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <PayModal
      :is-open="showPayModal"
      :obligation="account"
      @close="showPayModal = false"
      @paid="handlePaymentFinished"
    />

    <EditObligationModal
      :is-open="showEditModal"
      :obligation="account"
      @close="showEditModal = false"
      @updated="refreshAccount"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBNPL } from '../../composables/finance/useBNPL'
import { useToastStore } from '../../stores/toast'
import type { FinancialObligation } from '../../types/finance'
import PayModal from '../../components/finance/PayModal.vue'
import EditObligationModal from '../../components/finance/EditObligationModal.vue'
import {
  ArrowLeft,
  CreditCard,
  Plus,
  Edit2,
  Trash2,
  FileText,
  ShoppingBag,
  History,
  Check,
  Upload,
  Download
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const {
  currentAccount: account,
  subOrders,
  isLoading,
  isActionLoading,
  fetchAccountById,
  deleteAccount,
  deleteOrder,
  uploadAttachment,
  deleteAttachment
} = useBNPL()

const accountId = computed(() => route.params.id as string)
const activeTab = ref<'STATEMENT' | 'ORDERS' | 'DOCS' | 'HISTORY'>('STATEMENT')
const ordersFilter = ref<'ALL' | 'ACTIVE' | 'COMPLETED'>('ACTIVE')

const showPayModal = ref(false)
const showEditModal = ref(false)

const tabs = computed<Array<{ id: 'STATEMENT' | 'ORDERS' | 'DOCS' | 'HISTORY'; label: string; icon: any; badge?: string }>>(() => [
  { id: 'STATEMENT', label: 'Statement Reconciliation', icon: CreditCard, badge: activeSubOrders.value.length ? `${activeSubOrders.value.length}` : undefined },
  { id: 'ORDERS', label: 'Purchase Orders', icon: ShoppingBag, badge: `${subOrders.value.length}` },
  { id: 'DOCS', label: 'Statements & Slips', icon: FileText, badge: account.value?.attachments?.length ? `${account.value.attachments.length}` : undefined },
  { id: 'HISTORY', label: 'Payment Ledger', icon: History, badge: account.value?.payment_histories?.length ? `${account.value.payment_histories.length}` : undefined }
])

onMounted(async () => {
  if (accountId.value) {
    await refreshAccount()
  }
})

async function refreshAccount() {
  try {
    await fetchAccountById(accountId.value)
  } catch (err: any) {
    toast.error('Failed to load account')
  }
}

const activeSubOrders = computed(() => {
  return subOrders.value.filter(o => o.status === 'ACTIVE')
})

const filteredSubOrders = computed(() => {
  if (ordersFilter.value === 'ALL') return subOrders.value
  return subOrders.value.filter(o => o.status === ordersFilter.value)
})

function getOrderRemainingDebt(order: FinancialObligation): number {
  const meta = order.metadata || {}
  const totalTerms = Number(meta.total_terms || 1)
  const currentTerm = Number(meta.current_term || 0)
  const remainingTerms = Math.max(0, totalTerms - currentTerm)
  return Number(order.amount || 0) * remainingTerms
}

function openPayStatementModal() {
  showPayModal.value = true
}

async function handlePaymentFinished() {
  await refreshAccount()
  toast.success('Statement bill payment settled!')
}

async function handleDeleteOrder(orderId: string) {
  if (!confirm('Are you sure you want to delete this purchase order?')) return
  try {
    await deleteOrder(orderId, accountId.value)
    toast.success('Order deleted')
  } catch (err: any) {
    toast.error('Failed to delete order')
  }
}

async function handleFileUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  try {
    await uploadAttachment(accountId.value, file, 'STATEMENT')
    toast.success('Document uploaded to vault')
    target.value = ''
  } catch (err: any) {
    toast.error('Failed to upload file')
  }
}

async function handleDeleteAttachment(attachmentId: string) {
  if (!confirm('Delete this statement document?')) return
  try {
    await deleteAttachment(attachmentId, accountId.value)
    toast.success('Document removed')
  } catch (err: any) {
    toast.error('Failed to delete document')
  }
}

async function confirmDeleteAccount() {
  if (!confirm(`Are you sure you want to delete "${account.value?.title}"? All sub-orders will be removed.`)) return
  try {
    await deleteAccount(accountId.value)
    toast.success('BNPL facility deleted')
    router.push('/finance/bnpl')
  } catch (err: any) {
    toast.error('Failed to delete account')
  }
}
</script>
