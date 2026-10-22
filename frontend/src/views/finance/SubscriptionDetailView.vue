<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans pb-12">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2 mb-2">
          <RouterLink
            to="/finance/subscriptions"
            class="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft class="w-3.5 h-3.5" />
            <span>Subscriptions & Trials</span>
          </RouterLink>
          <span class="text-zinc-600">/</span>
          <span class="text-xs font-mono text-zinc-300">{{ subscription?.title || 'Dossier' }}</span>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">
            {{ subscription?.title || 'Loading Service...' }}
          </h1>
          <span
            v-if="subscription?.metadata?.plan_name"
            class="text-[10px] font-mono px-2 py-0.5 rounded border border-zinc-800 bg-zinc-900 text-zinc-300"
          >
            {{ subscription.metadata.plan_name }}
          </span>
          <span
            class="text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-semibold"
            :class="getStatusBadgeClass(subscription?.status)"
          >
            {{ subscription?.status || 'ACTIVE' }}
          </span>
          <span
            v-if="subscription?.type === 'FREE_TRIAL'"
            class="text-[10px] font-mono uppercase px-2 py-0.5 rounded border bg-rose-500/10 text-rose-400 border-rose-500/20 font-semibold"
          >
            FREE TRIAL WATCHDOG
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Detailed subscription lifecycle dossier, automated billing rollover, and cancellation guide
        </p>
      </div>

      <!-- Action Buttons -->
      <div class="flex flex-wrap items-center gap-2 self-start sm:self-auto">
        <!-- Direct Cancel Web Link -->
        <a
          v-if="subscription?.metadata?.cancel_url"
          :href="subscription.metadata.cancel_url"
          target="_blank"
          rel="noopener noreferrer"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <ExternalLink class="w-3.5 h-3.5 text-zinc-400" />
          <span>Cancellation URL</span>
        </a>

        <!-- Mark Trial Cancelled (if FREE_TRIAL and not cancelled) -->
        <button
          v-if="subscription?.type === 'FREE_TRIAL' && subscription?.status !== 'CANCELLED'"
          @click="handleCancelTrial"
          :disabled="isActionLoading"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-rose-400 hover:text-rose-300 text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <ShieldAlert class="w-3.5 h-3.5 text-rose-400" />
          <span>Mark Cancelled</span>
        </button>

        <!-- Convert Free Trial to Recurring Subscription -->
        <button
          v-if="subscription?.type === 'FREE_TRIAL'"
          @click="showConvertModal = true"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-200 text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <Repeat class="w-3.5 h-3.5 text-zinc-400" />
          <span>Keep & Convert</span>
        </button>

        <!-- Record Renewal / Pay Bill -->
        <button
          v-if="subscription?.status === 'ACTIVE'"
          @click="showPayModal = true"
          type="button"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Receipt class="w-3.5 h-3.5 text-zinc-950" />
          <span>Record Renewal</span>
        </button>

        <!-- Delete / Retire -->
        <button
          @click="confirmDelete"
          type="button"
          class="p-1.5 rounded-md hover:bg-zinc-900 text-zinc-500 hover:text-rose-400 border border-transparent hover:border-zinc-800 transition-colors"
          title="Delete Subscription"
        >
          <Trash2 class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Trial Countdown Alert Banner (if FREE_TRIAL) -->
    <div
      v-if="subscription?.type === 'FREE_TRIAL'"
      class="p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      :class="[
        daysRemaining !== null && daysRemaining <= 1
          ? 'bg-rose-500/10 border-rose-500/30 text-rose-200'
          : (daysRemaining !== null && daysRemaining <= 3 ? 'bg-amber-500/10 border-amber-500/30 text-amber-200' : 'bg-zinc-900/40 border-zinc-800/80 text-zinc-300')
      ]"
    >
      <div class="flex items-start gap-3">
        <div class="w-9 h-9 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0">
          <ShieldAlert class="w-4 h-4 text-rose-400" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h3 class="text-xs font-semibold font-mono uppercase tracking-wide">
              Free Trial Countdown Watchdog
            </h3>
            <span
              class="text-[9px] font-mono px-1.5 py-0.2 rounded border font-semibold uppercase"
              :class="daysRemaining !== null && daysRemaining <= 1 ? 'bg-rose-950 text-rose-400 border-rose-800' : 'bg-zinc-900 text-zinc-400 border-zinc-800'"
            >
              {{ daysRemaining !== null && daysRemaining <= 0 ? 'EXPIRED' : `${daysRemaining ?? 0} DAYS LEFT` }}
            </span>
          </div>
          <p class="text-xs mt-0.5 opacity-90">
            {{ subscription?.status === 'CANCELLED'
              ? 'This trial has been marked as cancelled. No surprise recurring debits expected.'
              : `Cancel before ${subscription?.due_date || 'renewal date'} to prevent an automatic charge of ${subscriptionCurrencySymbol}${formatNumber(subscription?.amount)}.` }}
          </p>
        </div>
      </div>

      <div v-if="subscription?.status !== 'CANCELLED'" class="flex items-center gap-2 shrink-0">
        <a
          v-if="subscription?.metadata?.cancel_url"
          :href="subscription.metadata.cancel_url"
          target="_blank"
          class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5"
        >
          <span>Cancel on Site</span>
          <ExternalLink class="w-3.5 h-3.5 text-zinc-950" />
        </a>
        <button
          @click="handleCancelTrial"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs font-medium transition-colors"
        >
          Mark Cancelled
        </button>
      </div>
    </div>

    <!-- KPI Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- 1. Next Renewal / Due Date -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">Next Billing Date</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
            <Calendar class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2">
          {{ formatDate(subscription?.due_date) || `Day ${subscription?.billing_day || '-'}` }}
        </div>
        <p class="text-[11px] font-mono mt-1" :class="daysRemaining !== null && daysRemaining <= 3 ? 'text-rose-400' : 'text-zinc-500'">
          {{ daysRemaining !== null ? (daysRemaining < 0 ? `${Math.abs(daysRemaining)} days ago` : `${daysRemaining} days remaining`) : 'Not scheduled' }}
        </p>
      </div>

      <!-- 2. Cost per Billing Period -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">
            {{ subscription?.type === 'FREE_TRIAL' ? 'Auto-Renew Cost' : 'Period Fee' }}
          </span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-300 flex items-center justify-center">
            <CreditCard class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2">
          {{ subscriptionCurrencySymbol }}{{ formatNumber(subscription?.amount) }}
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono uppercase">
          Billed {{ subscription?.metadata?.billing_cycle || 'Monthly' }}
        </p>
      </div>

      <!-- 3. Normalized Monthly Equivalent -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">Monthly Equivalent</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
            <Calculator class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-200 mt-2">
          {{ subscriptionCurrencySymbol }}{{ formatNumber(monthlyEquivalent) }}
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          Monthly normalized cost
        </p>
      </div>

      <!-- 4. Annualized Burn -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">Annualized Burn</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
            <Clock class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2">
          {{ subscriptionCurrencySymbol }}{{ formatNumber(monthlyEquivalent * 12) }}
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          Projected 12-month spend
        </p>
      </div>
    </div>

    <!-- Main Grid: Service Specs & Invoices Vault -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Column: Specs & Cancellation Guide (2 cols) -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Service Specs Dossier -->
        <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 p-5 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80">
            <div class="flex items-center gap-2">
              <FileText class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Subscription Parameters
              </h2>
            </div>
            <span class="text-[11px] font-mono text-zinc-500">ID: {{ subscription?.id?.slice(0, 8) }}</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            <div>
              <span class="text-[10px] uppercase text-zinc-500 block">Category</span>
              <span class="text-zinc-200 font-sans mt-0.5 block">{{ subscription?.metadata?.category || 'General' }}</span>
            </div>

            <div>
              <span class="text-[10px] uppercase text-zinc-500 block">Subscribed Email / Account</span>
              <span class="text-zinc-200 mt-0.5 block truncate">{{ subscription?.metadata?.account_email || '-' }}</span>
            </div>

            <div>
              <span class="text-[10px] uppercase text-zinc-500 block">Linked Payment Method</span>
              <span class="text-zinc-200 font-sans mt-0.5 block">{{ subscription?.metadata?.payment_method || '-' }}</span>
            </div>

            <div>
              <span class="text-[10px] uppercase text-zinc-500 block">Early Alert Notification</span>
              <span class="text-zinc-200 mt-0.5 block">{{ subscription?.metadata?.alert_days_before || 3 }} days prior to billing</span>
            </div>
          </div>

          <!-- Cancellation URL & Instructions Guide -->
          <div class="pt-3 border-t border-zinc-800/80 space-y-2">
            <span class="text-[10px] font-mono uppercase text-zinc-500 block">Cancellation Guide & Direct Links</span>
            <div v-if="subscription?.metadata?.cancel_url" class="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-between gap-3">
              <div class="truncate text-xs font-mono text-zinc-300">
                <span class="text-zinc-500 mr-2">URL:</span>
                <a :href="subscription.metadata.cancel_url" target="_blank" class="hover:underline text-zinc-200">{{ subscription.metadata.cancel_url }}</a>
              </div>
              <a
                :href="subscription.metadata.cancel_url"
                target="_blank"
                class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs font-medium transition-colors shrink-0 flex items-center gap-1"
              >
                <span>Open URL</span>
                <ExternalLink class="w-3 h-3 text-zinc-400" />
              </a>
            </div>

            <div v-if="subscription?.metadata?.cancel_steps" class="p-3 rounded-lg bg-zinc-950/60 border border-zinc-800 text-xs text-zinc-300 leading-relaxed font-sans">
              <div class="font-semibold text-zinc-200 mb-1 font-mono text-[11px] uppercase text-zinc-400">Steps to Cancel:</div>
              {{ subscription.metadata.cancel_steps }}
            </div>

            <div v-if="!subscription?.metadata?.cancel_url && !subscription?.metadata?.cancel_steps" class="text-xs text-zinc-500 italic">
              No cancellation instructions recorded for this service.
            </div>
          </div>
        </div>

        <!-- Payment & Renewal History Ledger -->
        <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
          <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <History class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Renewal & Payment Ledger
              </h2>
            </div>
            <span class="text-[11px] font-mono text-zinc-500">{{ paymentHistories.length }} Payments Recorded</span>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs font-mono">
              <thead>
                <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[10px] text-zinc-500 uppercase">
                  <th class="py-2.5 px-4 font-semibold">Payment Date</th>
                  <th class="py-2.5 px-4 font-semibold text-right">Amount Paid</th>
                  <th class="py-2.5 px-4 font-semibold">Note / Remarks</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/50">
                <tr
                  v-for="p in paymentHistories"
                  :key="p.id"
                  class="hover:bg-zinc-900/50 transition-colors"
                >
                  <td class="py-3 px-4 text-zinc-300">
                    {{ formatDate(p.paid_at) }}
                  </td>
                  <td class="py-3 px-4 text-right font-semibold text-emerald-400 tabular-nums">
                    {{ subscriptionCurrencySymbol }}{{ formatNumber(p.paid_amount) }}
                  </td>
                  <td class="py-3 px-4 text-zinc-400 text-[11px]">
                    {{ p.note || 'Subscription renewal payment' }}
                  </td>
                </tr>

                <tr v-if="paymentHistories.length === 0">
                  <td colspan="3" class="py-8 text-center text-xs text-zinc-500">
                    No payment history recorded yet for this service
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Right Column: Document Vault & Quick Attachments (1 col) -->
      <div class="space-y-6">
        <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 p-5 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80">
            <div class="flex items-center gap-2">
              <FolderArchive class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Document Vault
              </h2>
            </div>
            <label class="text-xs font-mono text-zinc-300 hover:text-white cursor-pointer transition-colors">
              <span>+ Upload</span>
              <input
                type="file"
                class="hidden"
                @change="handleFileUpload"
              />
            </label>
          </div>

          <p class="text-xs text-zinc-500">
            Archive renewal invoices, payment slips, or cancellation proof receipts
          </p>

          <!-- Upload Status Indicator -->
          <div v-if="isUploading" class="p-2.5 rounded bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-400 text-center">
            Uploading document...
          </div>

          <!-- Attachments List -->
          <div v-if="attachments.length > 0" class="space-y-2">
            <div
              v-for="att in attachments"
              :key="att.id"
              class="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80 flex items-center justify-between gap-2"
            >
              <div class="flex items-center gap-2 truncate">
                <FileText class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <div class="truncate text-xs font-mono">
                  <a
                    :href="att.file_url || att.file"
                    target="_blank"
                    class="text-zinc-200 hover:text-white hover:underline truncate block"
                  >
                    {{ att.file_name }}
                  </a>
                  <span class="text-[10px] text-zinc-500 block">{{ formatFileSize(att.file_size) }} · {{ att.file_type }}</span>
                </div>
              </div>
              <a
                :href="att.file_url || att.file"
                download
                target="_blank"
                class="p-1 text-zinc-400 hover:text-zinc-100"
                title="Download"
              >
                <Download class="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          <div v-else class="text-xs text-zinc-500 font-mono py-4 text-center">
            No invoices or slips stored
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <!-- Pay / Renewal Modal -->
    <div v-if="showPayModal" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl relative">
        <h3 class="text-sm font-semibold text-zinc-100">Record Subscription Renewal</h3>
        <p class="text-xs text-zinc-400 mt-1">
          Records a payment and advances the billing due date according to cycle ({{ subscription?.metadata?.billing_cycle || 'Monthly' }})
        </p>

        <form @submit.prevent="submitRenewal" class="space-y-4 mt-4 text-xs font-mono">
          <div>
            <label class="block text-zinc-400 mb-1">Amount Paid</label>
            <input
              v-model.number="payAmount"
              type="number"
              step="0.01"
              required
              class="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-100 focus:border-zinc-700 outline-none"
            />
          </div>

          <div>
            <label class="block text-zinc-400 mb-1">Notes / Invoice Ref</label>
            <input
              v-model="payNote"
              type="text"
              placeholder="e.g. Auto-debited on KBank Card"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-100 focus:border-zinc-700 outline-none"
            />
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-zinc-400">Deduct from Account / Card</label>
              <span class="text-[10px] text-zinc-500">Ledger 2-Way Sync</span>
            </div>
            <select
              v-model="payAccountId"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-100 focus:border-zinc-700 outline-none"
            >
              <option value="">-- No Account Link --</option>
              <option
                v-for="acc in ledgerStore.activeAccounts"
                :key="acc.id"
                :value="acc.id"
              >
                {{ acc.name }} ({{ acc.currency }} {{ Number(acc.current_balance).toLocaleString('en-US', { minimumFractionDigits: 2 }) }})
              </option>
            </select>
          </div>

          <div>
            <label class="block text-zinc-400 mb-1">Upload Receipt Slip (Optional)</label>
            <input
              type="file"
              @change="(e: any) => paySlipFile = e.target.files[0]"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-400 text-xs file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:bg-zinc-800 file:text-zinc-200"
            />
          </div>

          <div class="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              @click="showPayModal = false"
              class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isSubmittingPay"
              class="px-4 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 font-semibold"
            >
              {{ isSubmittingPay ? 'Processing...' : 'Confirm Payment' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Convert Trial Modal -->
    <div v-if="showConvertModal" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl relative">
        <h3 class="text-sm font-semibold text-zinc-100">Convert Trial to Recurring Subscription</h3>
        <p class="text-xs text-zinc-400 mt-1">
          Keep this service active and establish a recurring billing cycle.
        </p>

        <form @submit.prevent="submitConvertTrial" class="space-y-4 mt-4 text-xs font-mono">
          <div>
            <label class="block text-zinc-400 mb-1">Billing Cycle</label>
            <select
              v-model="convertCycle"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-100 focus:border-zinc-700 outline-none"
            >
              <option value="MONTHLY">Monthly</option>
              <option value="YEARLY">Yearly</option>
              <option value="QUARTERLY">Quarterly</option>
            </select>
          </div>

          <div>
            <label class="block text-zinc-400 mb-1">Recurring Cost</label>
            <input
              v-model.number="convertAmount"
              type="number"
              step="0.01"
              required
              class="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-100 focus:border-zinc-700 outline-none"
            />
          </div>

          <div class="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              @click="showConvertModal = false"
              class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isConverting"
              class="px-4 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 font-semibold"
            >
              {{ isConverting ? 'Converting...' : 'Convert to Active' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Confirm Modal -->
    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      @confirm="handleConfirmAction"
      @cancel="confirmModal.isOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSubscriptions } from '../../composables/finance/useSubscriptions'
import { useLedgerStore } from '../../stores/ledger'
import { useToastStore } from '../../stores/toast'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import {
  ArrowLeft,
  ExternalLink,
  ShieldAlert,
  Repeat,
  Receipt,
  Trash2,
  Calendar,
  CreditCard,
  Calculator,
  Clock,
  FileText,
  History,
  FolderArchive,
  Download
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const {
  currentSubscription,
  paymentHistories,
  attachments,
  isActionLoading,
  fetchSubscription,
  renewSubscription,
  cancelTrial,
  convertToSubscription,
  uploadDocument,
  deleteSubscription
} = useSubscriptions()

const toast = useToastStore()
const ledgerStore = useLedgerStore()
const subscriptionId = computed(() => route.params.id as string)
const subscription = computed(() => currentSubscription.value)

const showPayModal = ref(false)
const payAmount = ref(0)
const payNote = ref('')
const payAccountId = ref('')
const paySlipFile = ref<File | null>(null)
const isSubmittingPay = ref(false)

const showConvertModal = ref(false)
const convertCycle = ref('MONTHLY')
const convertAmount = ref(0)
const isConverting = ref(false)

const isUploading = ref(false)

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  action: () => {}
})

const subscriptionCurrencySymbol = computed(() => {
  return subscription.value?.currency === 'USD' ? '$' : '฿'
})

const daysRemaining = computed(() => {
  if (!subscription.value?.due_date) return null
  const target = new Date(subscription.value.due_date).getTime()
  const now = new Date(new Date().toISOString().split('T')[0]).getTime()
  return Math.round((target - now) / (1000 * 60 * 60 * 24))
})

const monthlyEquivalent = computed(() => {
  const amt = Number(subscription.value?.amount || 0)
  const cycle = subscription.value?.metadata?.billing_cycle || 'MONTHLY'
  if (cycle === 'YEARLY') return amt / 12
  if (cycle === 'QUARTERLY') return amt / 3
  if (cycle === 'WEEKLY') return amt * 4.333
  return amt
})

function getStatusBadgeClass(status?: string) {
  switch (status) {
    case 'ACTIVE':
      return 'bg-zinc-900 text-emerald-400 border-zinc-800'
    case 'CANCELLED':
      return 'bg-zinc-900 text-zinc-500 border-zinc-800'
    case 'PAUSED':
      return 'bg-zinc-900 text-amber-400 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

function formatDate(dateStr?: string | null) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

function formatNumber(val: any): string {
  const num = Number(val || 0)
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '0 KB'
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(0)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

async function handleCancelTrial() {
  try {
    await cancelTrial(subscriptionId.value)
    toast.success('Free trial marked as cancelled')
  } catch {
    toast.error('Failed to cancel trial')
  }
}

async function submitRenewal() {
  isSubmittingPay.value = true
  try {
    await renewSubscription(
      subscriptionId.value,
      payAmount.value,
      payNote.value,
      paySlipFile.value || undefined,
      payAccountId.value || undefined
    )
    if (payAccountId.value) {
      ledgerStore.fetchAccounts().catch(() => {})
      ledgerStore.fetchSummary().catch(() => {})
    }
    toast.success('Subscription renewal recorded successfully')
    showPayModal.value = false
    paySlipFile.value = null
    payNote.value = ''
    payAccountId.value = ''
  } catch {
    toast.error('Failed to record subscription payment')
  } finally {
    isSubmittingPay.value = false
  }
}

async function submitConvertTrial() {
  isConverting.value = true
  try {
    await convertToSubscription(subscriptionId.value, {
      billing_cycle: convertCycle.value,
      amount: convertAmount.value
    })
    toast.success('Converted trial to recurring subscription')
    showConvertModal.value = false
  } catch {
    toast.error('Failed to convert trial')
  } finally {
    isConverting.value = false
  }
}

async function handleFileUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  isUploading.value = true
  try {
    await uploadDocument(subscriptionId.value, file, 'STATEMENT')
    toast.success('Document uploaded to vault')
    target.value = ''
  } catch {
    toast.error('Failed to upload document')
  } finally {
    isUploading.value = false
  }
}

function confirmDelete() {
  confirmModal.title = 'Delete Subscription'
  confirmModal.message = 'Are you sure you want to delete this subscription dossier? All payment records and alarms will be removed.'
  confirmModal.confirmText = 'Delete Subscription'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await deleteSubscription(subscriptionId.value)
      toast.info('Deleted subscription record')
      router.push('/finance/subscriptions')
    } catch {
      toast.error('Failed to delete subscription')
    }
  }
  confirmModal.isOpen = true
}

function handleConfirmAction() {
  confirmModal.isOpen = false
  confirmModal.action()
}

onMounted(async () => {
  try {
    const data = await fetchSubscription(subscriptionId.value)
    if (data) {
      payAmount.value = Number(data.amount || 0)
      convertAmount.value = Number(data.amount || 0)
    }
  } catch {
    toast.error('Failed to load subscription dossier')
    router.push('/finance/subscriptions')
  }
})
</script>
