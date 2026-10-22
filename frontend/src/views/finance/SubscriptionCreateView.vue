<template>
  <div class="space-y-6 max-w-4xl mx-auto font-sans pb-12">
    <!-- Header -->
    <div class="pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-2 mb-2">
        <RouterLink
          to="/finance/subscriptions"
          class="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <ArrowLeft class="w-3.5 h-3.5" />
          <span>Subscriptions & Trials</span>
        </RouterLink>
        <span class="text-zinc-600">/</span>
        <span class="text-xs font-mono text-zinc-300">New Commitment</span>
      </div>
      <div class="flex items-center gap-2.5">
        <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Register Recurring Service</h1>
        <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
          RECURRING ENGINE
        </span>
      </div>
      <p class="text-xs text-zinc-500 mt-1">
        Setup automated billing cycle reminders, track annualized burn rate, or set a free trial expiration alarm
      </p>
    </div>

    <!-- Mode Switcher Tabs -->
    <div class="grid grid-cols-2 gap-2 p-1 bg-zinc-900/60 border border-zinc-800/80 rounded-xl">
      <button
        type="button"
        @click="form.type = 'SUBSCRIPTION'"
        class="py-2.5 px-4 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-2"
        :class="[
          form.type === 'SUBSCRIPTION'
            ? 'bg-zinc-800 text-zinc-100 border border-zinc-700/60 shadow-sm'
            : 'text-zinc-400 hover:text-zinc-200'
        ]"
      >
        <Repeat class="w-4 h-4 text-zinc-300" />
        <div class="text-left">
          <div class="font-semibold">Standard Subscription</div>
          <div class="text-[10px] text-zinc-500 font-mono">Monthly / Yearly recurring SaaS bill</div>
        </div>
      </button>

      <button
        type="button"
        @click="form.type = 'FREE_TRIAL'"
        class="py-2.5 px-4 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-2"
        :class="[
          form.type === 'FREE_TRIAL'
            ? 'bg-zinc-800 text-zinc-100 border border-zinc-700/60 shadow-sm'
            : 'text-zinc-400 hover:text-zinc-200'
        ]"
      >
        <ShieldAlert class="w-4 h-4 text-rose-400" />
        <div class="text-left">
          <div class="font-semibold">Free Trial Watchdog</div>
          <div class="text-[10px] text-zinc-500 font-mono">Pre-billing trap countdown alarm</div>
        </div>
      </button>
    </div>

    <!-- Quick Preset Catalog -->
    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <label class="text-[11px] font-mono uppercase text-zinc-400 tracking-wider">
          Quick Preset Template
        </label>
        <span class="text-[10px] text-zinc-500 font-mono">1-click popular presets</span>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
        <button
          v-for="preset in presets"
          :key="preset.title"
          type="button"
          @click="applyPreset(preset)"
          class="p-2.5 rounded-lg border text-left transition-colors flex flex-col justify-between"
          :class="[
            form.title === preset.title
              ? 'bg-zinc-800/80 border-zinc-600 text-zinc-100'
              : 'bg-zinc-900/30 border-zinc-800/80 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
          ]"
        >
          <span class="text-xs font-semibold truncate">{{ preset.title }}</span>
          <div class="mt-1 flex items-center justify-between text-[10px] font-mono text-zinc-500">
            <span>{{ preset.plan }}</span>
            <span class="text-zinc-300">{{ preset.currency === 'USD' ? '$' : '฿' }}{{ preset.amount }}</span>
          </div>
        </button>
      </div>
    </div>

    <!-- Main Registration Form -->
    <form @submit.prevent="handleSubmit" class="space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Left: Form Inputs (2 cols) -->
        <div class="md:col-span-2 space-y-4">
          <!-- 1. Service Title & Plan Name -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                Service / Vendor <span class="text-rose-400">*</span>
              </label>
              <input
                v-model="form.title"
                type="text"
                required
                placeholder="e.g. Netflix, ChatGPT Plus, Spotify"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              />
            </div>

            <div>
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                Plan / Tier
              </label>
              <input
                v-model="form.plan_name"
                type="text"
                placeholder="e.g. Premium 4K, Pro, Family"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              />
            </div>
          </div>

          <!-- 2. Category & Billing Cycle -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                Category
              </label>
              <select
                v-model="form.category"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              >
                <option value="STREAMING">Streaming & Entertainment</option>
                <option value="AI_TOOLS">AI & Machine Learning</option>
                <option value="CLOUD">Cloud & File Storage</option>
                <option value="PRODUCTIVITY">Productivity & Office</option>
                <option value="DEVELOPER">Developer & Infrastructure</option>
                <option value="GAMING">Gaming & Hobbies</option>
                <option value="HEALTH">Health & Fitness</option>
                <option value="GENERAL">General Services</option>
              </select>
            </div>

            <div v-if="form.type === 'SUBSCRIPTION'">
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                Billing Cycle
              </label>
              <select
                v-model="form.billing_cycle"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              >
                <option value="MONTHLY">Monthly (Every 1 Month)</option>
                <option value="YEARLY">Yearly (Every 12 Months)</option>
                <option value="QUARTERLY">Quarterly (Every 3 Months)</option>
                <option value="WEEKLY">Weekly (Every 7 Days)</option>
              </select>
            </div>

            <div v-else>
              <label class="block text-[11px] font-mono uppercase text-rose-400 mb-1.5">
                Renewal Cycle If Not Cancelled
              </label>
              <select
                v-model="form.billing_cycle"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              >
                <option value="MONTHLY">Monthly Auto-Renew</option>
                <option value="YEARLY">Yearly Auto-Renew (High Risk!)</option>
              </select>
            </div>
          </div>

          <!-- 3. Cost & Currency -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                {{ form.type === 'FREE_TRIAL' ? 'Auto-Renew Cost (Liability)' : 'Recurring Fee' }} <span class="text-rose-400">*</span>
              </label>
              <div class="relative">
                <input
                  v-model.number="form.amount"
                  type="number"
                  step="0.01"
                  required
                  placeholder="0.00"
                  class="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-8 pr-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
                />
                <span class="absolute left-3 top-2 text-xs font-mono text-zinc-500">
                  {{ form.currency === 'USD' ? '$' : '฿' }}
                </span>
              </div>
            </div>

            <div>
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                Currency
              </label>
              <select
                v-model="form.currency"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              >
                <option value="THB">Thai Baht (THB ฿)</option>
                <option value="USD">US Dollar (USD $)</option>
              </select>
            </div>
          </div>

          <!-- 4. Due Date / Expiration & Alert Lead Time -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                {{ form.type === 'FREE_TRIAL' ? 'Trial Expiration Date' : 'Next Billing Due Date' }} <span class="text-rose-400">*</span>
              </label>
              <input
                v-model="form.due_date"
                type="date"
                required
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              />
            </div>

            <div>
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                Early Alert Lead Time
              </label>
              <select
                v-model.number="form.alert_days_before"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              >
                <option :value="1">1 Day Before Renewal</option>
                <option :value="2">2 Days Before Renewal</option>
                <option :value="3">3 Days Before Renewal (Recommended)</option>
                <option :value="5">5 Days Before Renewal</option>
                <option :value="7">7 Days Before Renewal</option>
              </select>
            </div>
          </div>

          <!-- 5. Linked Account & Payment Method -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                Subscribed Email / Account
              </label>
              <input
                v-model="form.account_email"
                type="text"
                placeholder="user@example.com"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              />
            </div>

            <div>
              <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
                Payment Method / Card
              </label>
              <input
                v-model="form.payment_method"
                type="text"
                placeholder="e.g. KBank VISA (..8912), Apple ID"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
              />
            </div>
          </div>

          <!-- 6. Direct Cancellation URL & Steps -->
          <div>
            <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
              Direct Cancellation Web Link
            </label>
            <input
              v-model="form.cancel_url"
              type="url"
              placeholder="https://vendor.com/account/cancel"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
            />
          </div>

          <div>
            <label class="block text-[11px] font-mono uppercase text-zinc-400 mb-1.5">
              Cancellation Steps / Retention Notes
            </label>
            <textarea
              v-model="form.cancel_steps"
              rows="2"
              placeholder="e.g. Go to Settings -> Subscriptions -> Cancel Plan before 11:59 PM"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-700 outline-none transition-colors"
            ></textarea>
          </div>
        </div>

        <!-- Right: Real-time Live Impact Summary (1 col) -->
        <div class="space-y-4">
          <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3.5 sticky top-6">
            <div class="flex items-center gap-2 pb-2 border-b border-zinc-800/80">
              <Calculator class="w-4 h-4 text-zinc-400" />
              <h3 class="text-xs font-semibold text-zinc-200 uppercase font-mono">
                Commitment Impact
              </h3>
            </div>

            <!-- Normalized Monthly Cost -->
            <div>
              <span class="text-[10px] font-mono uppercase text-zinc-500 block">Monthly Equivalent</span>
              <div class="text-xl font-bold font-mono text-zinc-100 tabular-nums mt-0.5">
                {{ form.currency === 'USD' ? '$' : '฿' }}{{ formatNumber(computedMonthlyCost) }}
              </div>
              <span class="text-[10px] text-zinc-500 font-mono">Normalized per month</span>
            </div>

            <!-- Annualized Burn -->
            <div>
              <span class="text-[10px] font-mono uppercase text-zinc-500 block">Annualized Burn Rate</span>
              <div class="text-lg font-semibold font-mono text-zinc-300 tabular-nums mt-0.5">
                {{ form.currency === 'USD' ? '$' : '฿' }}{{ formatNumber(computedAnnualCost) }}
              </div>
              <span class="text-[10px] text-zinc-500 font-mono">12-month projection</span>
            </div>

            <!-- Trial Trap Alert if FREE_TRIAL -->
            <div v-if="form.type === 'FREE_TRIAL'" class="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs space-y-1">
              <div class="flex items-center gap-1.5 font-semibold">
                <AlertTriangle class="w-3.5 h-3.5 text-rose-400" />
                <span>Auto-Debit Trap Warning</span>
              </div>
              <p class="text-[11px] leading-relaxed text-rose-300/80">
                If not cancelled by {{ form.due_date || 'expiry' }}, your account will be billed {{ form.currency === 'USD' ? '$' : '฿' }}{{ formatNumber(form.amount || 0) }}.
              </p>
            </div>

            <!-- Countdown Preview -->
            <div class="pt-2 border-t border-zinc-800/80 text-xs font-mono text-zinc-400">
              <div class="flex justify-between text-[11px]">
                <span class="text-zinc-500">Days to Trigger:</span>
                <span :class="daysUntilDue !== null && daysUntilDue <= 3 ? 'text-rose-400 font-bold' : 'text-zinc-200'">
                  {{ daysUntilDue !== null ? `${daysUntilDue} days` : '-' }}
                </span>
              </div>
              <div class="flex justify-between text-[11px] mt-1">
                <span class="text-zinc-500">Alert Notification:</span>
                <span class="text-zinc-300">{{ form.alert_days_before }} days prior</span>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="pt-3">
              <button
                type="submit"
                :disabled="isSubmitting"
                class="w-full py-2.5 px-4 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
              >
                <Plus class="w-3.5 h-3.5 text-zinc-950" />
                <span>{{ isSubmitting ? 'Registering...' : (form.type === 'FREE_TRIAL' ? 'Arm Trial Watchdog' : 'Confirm Subscription') }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSubscriptions } from '../../composables/finance/useSubscriptions'
import { useToastStore } from '../../stores/toast'
import {
  ArrowLeft,
  Repeat,
  ShieldAlert,
  Calculator,
  AlertTriangle,
  Plus
} from 'lucide-vue-next'

const router = useRouter()
const { createSubscription } = useSubscriptions()
const toast = useToastStore()

const isSubmitting = ref(false)

const getNowLocalDate = () => {
  const d = new Date()
  return d.toISOString().split('T')[0]
}

const getFutureDate = (daysAhead: number) => {
  const d = new Date()
  d.setDate(d.getDate() + daysAhead)
  return d.toISOString().split('T')[0]
}

const form = ref({
  type: 'SUBSCRIPTION' as 'SUBSCRIPTION' | 'FREE_TRIAL',
  title: '',
  plan_name: '',
  category: 'STREAMING',
  billing_cycle: 'MONTHLY' as 'MONTHLY' | 'YEARLY' | 'QUARTERLY' | 'WEEKLY',
  amount: 0,
  currency: 'THB',
  due_date: getFutureDate(30),
  alert_days_before: 3,
  account_email: '',
  payment_method: '',
  cancel_url: '',
  cancel_steps: ''
})

interface Preset {
  title: string
  plan: string
  category: string
  amount: number
  currency: string
  billing_cycle: 'MONTHLY' | 'YEARLY'
  cancel_url: string
}

const presets: Preset[] = [
  {
    title: 'Netflix',
    plan: 'Premium 4K',
    category: 'STREAMING',
    amount: 419,
    currency: 'THB',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://www.netflix.com/youraccount'
  },
  {
    title: 'Spotify',
    plan: 'Individual Premium',
    category: 'STREAMING',
    amount: 139,
    currency: 'THB',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://www.spotify.com/account/overview/'
  },
  {
    title: 'YouTube Premium',
    plan: 'Individual',
    category: 'STREAMING',
    amount: 179,
    currency: 'THB',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://www.youtube.com/paid_memberships'
  },
  {
    title: 'ChatGPT Plus',
    plan: 'Plus 4o',
    category: 'AI_TOOLS',
    amount: 20,
    currency: 'USD',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://chatgpt.com/#settings/Subscription'
  },
  {
    title: 'Claude Pro',
    plan: 'Pro Plan',
    category: 'AI_TOOLS',
    amount: 20,
    currency: 'USD',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://claude.ai/settings/billing'
  },
  {
    title: 'Apple iCloud+',
    plan: '50 GB',
    category: 'CLOUD',
    amount: 35,
    currency: 'THB',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://appleid.apple.com'
  },
  {
    title: 'Google One',
    plan: '100 GB Basic',
    category: 'CLOUD',
    amount: 70,
    currency: 'THB',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://one.google.com/settings'
  },
  {
    title: 'GitHub Copilot',
    plan: 'Individual',
    category: 'DEVELOPER',
    amount: 10,
    currency: 'USD',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://github.com/settings/copilot'
  },
  {
    title: 'Adobe Creative Cloud',
    plan: 'Photography Plan',
    category: 'PRODUCTIVITY',
    amount: 356,
    currency: 'THB',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://account.adobe.com/plans'
  },
  {
    title: 'Midjourney',
    plan: 'Standard Plan',
    category: 'AI_TOOLS',
    amount: 30,
    currency: 'USD',
    billing_cycle: 'MONTHLY',
    cancel_url: 'https://www.midjourney.com/account'
  }
]

function applyPreset(p: Preset) {
  form.value.title = p.title
  form.value.plan_name = p.plan
  form.value.category = p.category
  form.value.amount = p.amount
  form.value.currency = p.currency
  form.value.billing_cycle = p.billing_cycle
  form.value.cancel_url = p.cancel_url
}

const computedMonthlyCost = computed(() => {
  const amt = Number(form.value.amount || 0)
  if (form.value.billing_cycle === 'YEARLY') return amt / 12
  if (form.value.billing_cycle === 'QUARTERLY') return amt / 3
  if (form.value.billing_cycle === 'WEEKLY') return amt * 4.333
  return amt
})

const computedAnnualCost = computed(() => {
  return computedMonthlyCost.value * 12
})

const daysUntilDue = computed(() => {
  if (!form.value.due_date) return null
  const target = new Date(form.value.due_date).getTime()
  const now = new Date(getNowLocalDate()).getTime()
  const diffDays = Math.round((target - now) / (1000 * 60 * 60 * 24))
  return diffDays
})

function formatNumber(val: number): string {
  return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function handleSubmit() {
  if (!form.value.title.trim()) {
    toast.error('Please enter a service or vendor name')
    return
  }

  isSubmitting.value = true
  try {
    const billingDay = form.value.due_date ? new Date(form.value.due_date).getDate() : undefined

    const payload = {
      title: form.value.title.trim(),
      type: form.value.type,
      amount: Number(form.value.amount || 0),
      currency: form.value.currency,
      due_date: form.value.due_date,
      billing_day: billingDay,
      metadata: {
        plan_name: form.value.plan_name.trim(),
        billing_cycle: form.value.billing_cycle,
        account_email: form.value.account_email.trim(),
        payment_method: form.value.payment_method.trim(),
        category: form.value.category,
        cancel_url: form.value.cancel_url.trim(),
        cancel_steps: form.value.cancel_steps.trim(),
        alert_days_before: Number(form.value.alert_days_before || 3),
        auto_renew_cost: Number(form.value.amount || 0)
      }
    }

    const created = await createSubscription(payload)
    toast.success(`${form.value.type === 'FREE_TRIAL' ? 'Trial Watchdog' : 'Subscription'} registered successfully`)
    router.push(`/finance/subscriptions/${created.id}`)
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || 'Failed to register subscription')
  } finally {
    isSubmitting.value = false
  }
}
</script>
