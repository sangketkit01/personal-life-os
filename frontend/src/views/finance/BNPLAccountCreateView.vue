<template>
  <div class="max-w-4xl mx-auto space-y-6 font-sans">
    <!-- Breadcrumb & Back Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          @click="router.push('/finance/bnpl')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Shopping Credit Overview"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Revolving Credit Line</h1>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800 font-medium">
              BNPL FACILITY
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-0.5">
            Configure a new e-commerce shopping credit account with approved limit and billing cycle dates.
          </p>
        </div>
      </div>
    </div>

    <!-- Main Creation Layout: Form & Live Calculation Preview -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Left: Form Controls (7 cols) -->
      <form @submit.prevent="handleSubmit" class="lg:col-span-7 space-y-5">
        <!-- Card 1: Provider & Facility Name -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center gap-2 pb-2 border-b border-zinc-800/60">
            <ShoppingBag class="w-4 h-4 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Credit Facility Information
            </h2>
          </div>

          <!-- Quick Provider Presets -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Provider Presets
            </label>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="preset in providerPresets"
                :key="preset.name"
                type="button"
                @click="applyPreset(preset)"
                class="px-2.5 py-1 rounded text-xs font-mono border transition-colors"
                :class="form.provider === preset.name
                  ? 'bg-zinc-800 text-zinc-100 border-zinc-600'
                  : 'bg-zinc-950 text-zinc-400 border-zinc-800 hover:text-zinc-200 hover:border-zinc-700'"
              >
                {{ preset.name }}
              </button>
            </div>
          </div>

          <!-- Account Title -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Account Display Name <span class="text-rose-400">*</span>
            </label>
            <input
              v-model="form.title"
              type="text"
              required
              placeholder="e.g. Shopee SPayLater"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
            />
          </div>

          <!-- Provider & Account Number -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Provider Name
              </label>
              <input
                v-model="form.provider"
                type="text"
                placeholder="Shopee / SeaMoney"
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
              />
            </div>

            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Linked Phone / User Ref
              </label>
              <input
                v-model="form.account_number"
                type="text"
                placeholder="e.g. 081-xxx-xxxx"
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
              />
            </div>
          </div>
        </div>

        <!-- Card 2: Credit Limit & Billing Cycle Mechanics -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center gap-2 pb-2 border-b border-zinc-800/60">
            <Calendar class="w-4 h-4 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Credit Limit & Dual-Date Billing Cycle
            </h2>
          </div>

          <!-- Credit Limit -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Total Approved Credit Limit (฿) <span class="text-rose-400">*</span>
            </label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">฿</span>
              <input
                v-model.number="form.credit_limit"
                type="number"
                step="100"
                min="0"
                required
                placeholder="20000"
                class="w-full pl-7 pr-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
              />
            </div>
          </div>

          <!-- Dual-Date Cycle: Cut-off Day vs Due Day -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Statement Cut-off Day <span class="text-rose-400">*</span>
              </label>
              <div class="flex items-center gap-2">
                <input
                  v-model.number="form.cutoff_day"
                  type="number"
                  min="1"
                  max="31"
                  required
                  placeholder="25"
                  class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
                />
                <span class="text-xs font-mono text-zinc-500 whitespace-nowrap">of month</span>
              </div>
              <span class="text-[10px] text-zinc-500 block">Orders cut off for billing</span>
            </div>

            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Payment Due Day <span class="text-rose-400">*</span>
              </label>
              <div class="flex items-center gap-2">
                <input
                  v-model.number="form.due_day"
                  type="number"
                  min="1"
                  max="31"
                  required
                  placeholder="10"
                  class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
                />
                <span class="text-xs font-mono text-zinc-500 whitespace-nowrap">of next month</span>
              </div>
              <span class="text-[10px] text-zinc-500 block">Final payment deadline</span>
            </div>
          </div>
        </div>

        <!-- Card 3: Notes -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center gap-2 pb-2 border-b border-zinc-800/60">
            <FileText class="w-4 h-4 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Internal Notes
            </h2>
          </div>

          <div class="space-y-1.5">
            <textarea
              v-model="form.notes"
              rows="2"
              placeholder="e.g. 0% interest voucher limit, tied to SCB debit card autopay..."
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors resize-none"
            ></textarea>
          </div>
        </div>

        <!-- Submission Actions -->
        <div class="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            @click="router.push('/finance/bnpl')"
            class="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isActionLoading"
            class="px-5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
          >
            <Check class="w-3.5 h-3.5" />
            <span>{{ isActionLoading ? 'Creating Line...' : 'Create BNPL Line' }}</span>
          </button>
        </div>
      </form>

      <!-- Right: Live Facility & Billing Cycle Preview (5 cols) -->
      <div class="lg:col-span-5 space-y-4">
        <!-- Live Card Preview -->
        <div class="p-5 rounded-xl bg-zinc-900/60 border border-zinc-800/90 space-y-4 sticky top-6">
          <div class="flex items-center justify-between pb-2 border-b border-zinc-800/80">
            <div class="flex items-center gap-2">
              <CreditCard class="w-4 h-4 text-zinc-300" />
              <h3 class="text-xs font-semibold font-mono uppercase text-zinc-300">
                Facility Summary Preview
              </h3>
            </div>
            <span class="text-[10px] font-mono text-zinc-500 uppercase">
              LIVE PREVIEW
            </span>
          </div>

          <!-- Account Identity -->
          <div>
            <div class="flex items-center justify-between">
              <span class="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-zinc-950 text-zinc-400 border border-zinc-800 font-semibold">
                {{ form.provider || 'PROVIDER' }}
              </span>
              <span class="text-[10px] font-mono text-zinc-500">
                Ref: {{ form.account_number || 'N/A' }}
              </span>
            </div>
            <h4 class="text-base font-semibold text-zinc-100 font-sans mt-2">
              {{ form.title || 'Untitled Credit Facility' }}
            </h4>
          </div>

          <!-- Metrics Box -->
          <div class="grid grid-cols-2 gap-2.5 p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 font-mono text-xs">
            <div>
              <span class="text-[9px] text-zinc-500 uppercase block">Approved Limit</span>
              <span class="text-zinc-100 font-semibold text-sm">
                ฿{{ Number(form.credit_limit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </span>
            </div>
            <div>
              <span class="text-[9px] text-zinc-500 uppercase block">Available Buying Power</span>
              <span class="text-emerald-400 font-semibold text-sm">
                ฿{{ Number(form.credit_limit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </span>
            </div>
          </div>

          <!-- Billing Cycle Visual Flowchart -->
          <div class="p-3.5 rounded-lg bg-zinc-950/80 border border-zinc-800/60 space-y-2.5 font-mono text-xs">
            <span class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
              Billing Cycle Engine
            </span>

            <div class="flex items-center justify-between text-[11px] text-zinc-300 py-1 border-b border-zinc-900">
              <span class="text-zinc-500">Statement Cut-off:</span>
              <span class="font-semibold text-zinc-200">{{ form.cutoff_day }}th of each month</span>
            </div>

            <div class="flex items-center justify-between text-[11px] text-zinc-300 py-1 border-b border-zinc-900">
              <span class="text-zinc-500">Payment Due Date:</span>
              <span class="font-semibold text-zinc-200">{{ form.due_day }}th of next month</span>
            </div>

            <div class="flex items-center justify-between text-[11px] text-zinc-300 py-1">
              <span class="text-zinc-500">Grace Period:</span>
              <span class="font-semibold text-zinc-200">{{ calculateGracePeriodDays }} days</span>
            </div>

            <div class="mt-2 p-2.5 rounded bg-zinc-900/50 border border-zinc-800 text-[11px] text-zinc-400 leading-relaxed font-sans">
              ℹ️ Purchases made between the {{ form.cutoff_day + 1 }}th of last month and {{ form.cutoff_day }}th of this month are aggregated into one consolidated statement, payable on the {{ form.due_day }}th.
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useBNPL } from '../../composables/finance/useBNPL'
import { useToastStore } from '../../stores/toast'
import {
  ArrowLeft,
  ShoppingBag,
  Calendar,
  CreditCard,
  FileText,
  Check
} from 'lucide-vue-next'

const router = useRouter()
const toast = useToastStore()
const { createAccount, isActionLoading } = useBNPL()

const providerPresets = [
  { name: 'Shopee SPayLater', provider: 'Shopee', cutoff: 25, due: 10 },
  { name: 'Lazada LazPayLater', provider: 'Lazada', cutoff: 1, due: 15 },
  { name: 'TikTok Shop PayLater', provider: 'TikTok', cutoff: 20, due: 5 },
  { name: 'Atome BNPL', provider: 'Atome', cutoff: 15, due: 30 }
]

const form = reactive({
  title: '',
  provider: '',
  credit_limit: 20000,
  cutoff_day: 25,
  due_day: 10,
  account_number: '',
  notes: ''
})

const calculateGracePeriodDays = computed(() => {
  const cutoff = form.cutoff_day || 25
  const due = form.due_day || 10
  if (due >= cutoff) {
    return due - cutoff
  }
  return (30 - cutoff) + due
})

function applyPreset(preset: typeof providerPresets[0]) {
  form.title = preset.name
  form.provider = preset.provider
  form.cutoff_day = preset.cutoff
  form.due_day = preset.due
}

async function handleSubmit() {
  if (!form.title || !form.credit_limit) {
    toast.error('Please enter account title and credit limit')
    return
  }

  try {
    const created = await createAccount({
      title: form.title,
      provider: form.provider || form.title,
      credit_limit: Number(form.credit_limit),
      cutoff_day: Number(form.cutoff_day),
      due_day: Number(form.due_day),
      account_number: form.account_number,
      notes: form.notes
    })
    toast.success(`Created ${created.title} successfully!`)
    router.push(`/finance/bnpl/${created.id}`)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to create BNPL credit line')
  }
}
</script>
