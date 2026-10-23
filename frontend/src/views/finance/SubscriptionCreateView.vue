<template>
  <div class="max-w-xl mx-auto py-4 font-sans pb-16 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <RouterLink
          to="/finance/subscriptions"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Subscriptions"
        >
          <ArrowLeft class="w-4 h-4" />
        </RouterLink>
        <div>
          <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Recurring Service</h1>
          <p class="text-xs text-zinc-500 mt-0.5">
            Track subscription renewals and free trial expiration alerts
          </p>
        </div>
      </div>
    </div>

    <!-- Mode Selector: Subscription vs Free Trial -->
    <div class="grid grid-cols-2 gap-1 p-1 bg-zinc-900/80 border border-zinc-800 rounded-lg">
      <button
        type="button"
        @click="form.type = 'SUBSCRIPTION'"
        class="py-2 px-3 rounded text-xs font-medium transition-colors flex items-center justify-center gap-2"
        :class="form.type === 'SUBSCRIPTION' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <Repeat class="w-3.5 h-3.5" />
        <span>Standard Subscription</span>
      </button>

      <button
        type="button"
        @click="form.type = 'FREE_TRIAL'"
        class="py-2 px-3 rounded text-xs font-medium transition-colors flex items-center justify-center gap-2"
        :class="form.type === 'FREE_TRIAL' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <ShieldAlert class="w-3.5 h-3.5 text-zinc-400" />
        <span>Free Trial Alert</span>
      </button>
    </div>

    <!-- Quick Suggestion Chips (Compact 1-row) -->
    <div class="space-y-1.5">
      <span class="text-[11px] font-mono uppercase text-zinc-500">Popular Presets</span>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="p in popularPresets"
          :key="p.title"
          type="button"
          @click="applyPreset(p)"
          class="px-2.5 py-1 rounded text-xs font-mono border transition-colors"
          :class="form.title === p.title
            ? 'bg-zinc-800 text-zinc-100 border-zinc-600'
            : 'bg-zinc-950 text-zinc-400 border-zinc-800 hover:text-zinc-200 hover:border-zinc-700'"
        >
          {{ p.title }}
        </button>
      </div>
    </div>

    <!-- Main Clean Form -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Title & Plan -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Service Name <span class="text-rose-400">*</span>
          </label>
          <input
            v-model="form.title"
            type="text"
            required
            placeholder="e.g. Netflix, ChatGPT, Spotify"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Plan / Tier
          </label>
          <input
            v-model="form.plan_name"
            type="text"
            placeholder="e.g. Premium 4K, Pro, Family"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>
      </div>

      <!-- Category & Cycle -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Category</label>
          <select
            v-model="form.category"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option value="STREAMING">Streaming & Entertainment</option>
            <option value="AI_TOOLS">AI & Machine Learning</option>
            <option value="CLOUD">Cloud & Storage</option>
            <option value="PRODUCTIVITY">ProductIVITY</option>
            <option value="DEVELOPER">Developer & Infrastructure</option>
            <option value="GAMING">Gaming & Hobbies</option>
            <option value="HEALTH">Health & Fitness</option>
            <option value="GENERAL">General Services</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Billing Cycle</label>
          <select
            v-model="form.billing_cycle"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option value="MONTHLY">Monthly</option>
            <option value="YEARLY">Yearly</option>
            <option value="QUARTERLY">Quarterly</option>
            <option value="WEEKLY">Weekly</option>
          </select>
        </div>
      </div>

      <!-- Amount & Currency -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            {{ form.type === 'FREE_TRIAL' ? 'Auto-Renew Cost' : 'Recurring Amount' }} <span class="text-rose-400">*</span>
          </label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">
              {{ form.currency === 'USD' ? '$' : '฿' }}
            </span>
            <input
              v-model.number="form.amount"
              type="number"
              step="0.01"
              required
              placeholder="0.00"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-7 pr-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
            />
          </div>
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Currency</label>
          <select
            v-model="form.currency"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option value="THB">THB (฿)</option>
            <option value="USD">USD ($)</option>
          </select>
        </div>
      </div>

      <!-- Next Due Date & Alert Lead Time -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            {{ form.type === 'FREE_TRIAL' ? 'Trial Expiration Date' : 'Next Billing Date' }} <span class="text-rose-400">*</span>
          </label>
          <input
            v-model="form.due_date"
            type="date"
            required
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Reminder Notification</label>
          <select
            v-model.number="form.alert_days_before"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option :value="1">1 day prior</option>
            <option :value="2">2 days prior</option>
            <option :value="3">3 days prior (Recommended)</option>
            <option :value="5">5 days prior</option>
            <option :value="7">7 days prior</option>
          </select>
        </div>
      </div>

      <!-- Cost Calculation Bar -->
      <div class="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800/80 flex items-center justify-between text-xs font-mono">
        <span class="text-zinc-400">Monthly Projection:</span>
        <span class="font-semibold text-zinc-100">
          {{ form.currency === 'USD' ? '$' : '฿' }}{{ formatNumber(computedMonthlyCost) }} / mo
        </span>
      </div>

      <!-- Progressive Disclosure: Additional Details -->
      <div class="pt-1">
        <button
          type="button"
          @click="showAdvanced = !showAdvanced"
          class="text-xs font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1.5 transition-colors"
        >
          <span>{{ showAdvanced ? '- Less Details' : '+ Additional Details (Optional)' }}</span>
        </button>

        <div v-if="showAdvanced" class="mt-3 space-y-3 pt-3 border-t border-zinc-800/60">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Account Email</label>
              <input
                v-model="form.account_email"
                type="email"
                placeholder="user@example.com"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>

            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Payment Method</label>
              <input
                v-model="form.payment_method"
                type="text"
                placeholder="e.g. VISA ..1234, Apple Pay"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-mono text-zinc-400 mb-1">Cancellation URL</label>
            <input
              v-model="form.cancel_url"
              type="url"
              placeholder="https://vendor.com/account/cancel"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
            />
          </div>

          <div>
            <label class="block text-xs font-mono text-zinc-400 mb-1">Cancellation Steps / Notes</label>
            <textarea
              v-model="form.cancel_steps"
              rows="2"
              placeholder="e.g. Settings -> Subscriptions -> Cancel Plan"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors resize-none"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
        <RouterLink
          to="/finance/subscriptions"
          class="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 font-medium transition-colors"
        >
          Cancel
        </RouterLink>
        <button
          type="submit"
          :disabled="isSubmitting"
          class="px-5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
        >
          <Check class="w-3.5 h-3.5" />
          <span>{{ isSubmitting ? 'Saving...' : (form.type === 'FREE_TRIAL' ? 'Create Trial Alert' : 'Create Subscription') }}</span>
        </button>
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
  Check
} from 'lucide-vue-next'

const router = useRouter()
const { createSubscription } = useSubscriptions()
const toast = useToastStore()

const isSubmitting = ref(false)
const showAdvanced = ref(false)

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

const popularPresets = [
  { title: 'Netflix', plan: 'Premium 4K', category: 'STREAMING', amount: 419, currency: 'THB', cycle: 'MONTHLY' as const, url: 'https://netflix.com/youraccount' },
  { title: 'Spotify', plan: 'Individual', category: 'STREAMING', amount: 139, currency: 'THB', cycle: 'MONTHLY' as const, url: 'https://spotify.com/account' },
  { title: 'YouTube Premium', plan: 'Individual', category: 'STREAMING', amount: 179, currency: 'THB', cycle: 'MONTHLY' as const, url: 'https://youtube.com/paid_memberships' },
  { title: 'ChatGPT Plus', plan: 'Plus', category: 'AI_TOOLS', amount: 20, currency: 'USD', cycle: 'MONTHLY' as const, url: 'https://chatgpt.com/#settings/Subscription' },
  { title: 'Claude Pro', plan: 'Pro', category: 'AI_TOOLS', amount: 20, currency: 'USD', cycle: 'MONTHLY' as const, url: 'https://claude.ai/settings/billing' },
  { title: 'iCloud+', plan: '50 GB', category: 'CLOUD', amount: 35, currency: 'THB', cycle: 'MONTHLY' as const, url: 'https://appleid.apple.com' }
]

function applyPreset(p: typeof popularPresets[0]) {
  form.value.title = p.title
  form.value.plan_name = p.plan
  form.value.category = p.category
  form.value.amount = p.amount
  form.value.currency = p.currency
  form.value.billing_cycle = p.cycle
  form.value.cancel_url = p.url
}

const computedMonthlyCost = computed(() => {
  const amt = Number(form.value.amount || 0)
  if (form.value.billing_cycle === 'YEARLY') return amt / 12
  if (form.value.billing_cycle === 'QUARTERLY') return amt / 3
  if (form.value.billing_cycle === 'WEEKLY') return amt * 4.333
  return amt
})

function formatNumber(val: number): string {
  return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function handleSubmit() {
  if (!form.value.title.trim()) {
    toast.error('Please enter a service name')
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
    toast.success('Subscription saved successfully')
    router.push(`/finance/subscriptions/${created.id}`)
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || 'Failed to save subscription')
  } finally {
    isSubmitting.value = false
  }
}
</script>
