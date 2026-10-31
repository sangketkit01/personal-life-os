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
            placeholder="e.g. Netflix, Spotify"
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
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Category <span class="text-rose-400">*</span></label>
          <select
            v-model="form.category"
            required
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option value="" disabled>Select category</option>
            <option value="STREAMING">Streaming & Entertainment</option>
            <option value="AI_TOOLS">AI & Machine Learning</option>
            <option value="CLOUD">Cloud & Storage</option>
            <option value="PRODUCTIVITY">Productivity</option>
            <option value="DEVELOPER">Developer & Infrastructure</option>
            <option value="GAMING">Gaming & Hobbies</option>
            <option value="HEALTH">Health & Fitness</option>
            <option value="GENERAL">General Services</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Billing Cycle <span class="text-rose-400">*</span></label>
          <select
            v-model="form.billing_cycle"
            required
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option value="" disabled>Select billing cycle</option>
            <option value="MONTHLY">Monthly</option>
            <option value="YEARLY">Yearly</option>
            <option value="QUARTERLY">Quarterly</option>
            <option value="WEEKLY">Weekly</option>
          </select>
        </div>
      </div>

      <!-- Currency -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Currency <span class="text-rose-400">*</span></label>
          <select
            v-model="form.currency"
            required
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option value="" disabled>Select currency</option>
            <option value="THB">THB (฿)</option>
            <option value="USD">USD ($)</option>
          </select>
        </div>
      </div>

      <!-- Amount Section with Single Amount / Itemized Switcher -->
      <div v-if="form.type === 'SUBSCRIPTION'" class="space-y-3 pt-1">
        <div class="flex items-center justify-between pb-1">
          <label class="block text-xs font-mono text-zinc-400">โครงสร้างราคา / Expense Structure</label>
          <div class="inline-flex rounded-lg border border-zinc-800 bg-zinc-900/80 p-0.5 text-xs font-mono">
            <button
              type="button"
              @click="setPricingMode(false)"
              class="px-2.5 py-1 rounded transition-colors text-[11px]"
              :class="!isItemized ? 'bg-zinc-800 text-zinc-100 font-medium shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
            >
              ยอดเดียว
            </button>
            <button
              type="button"
              @click="setPricingMode(true)"
              class="px-2.5 py-1 rounded transition-colors text-[11px]"
              :class="isItemized ? 'bg-zinc-800 text-zinc-100 font-medium shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
            >
              แยกรายการ
            </button>
          </div>
        </div>

        <!-- Mode A: Single Amount -->
        <div v-if="!isItemized">
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Recurring Amount <span class="text-rose-400">*</span>
          </label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">
              {{ form.currency === 'USD' ? '$' : (form.currency === 'THB' ? '฿' : '') }}
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

        <!-- Mode B: Itemized Breakdown -->
        <div v-else class="space-y-4 p-3.5 rounded-lg bg-zinc-900/40 border border-zinc-800 text-xs font-mono">
          <!-- 1. Fixed Items -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">ราคาคงที่</span>
              <span class="text-[10px] text-zinc-500">ระบุราคาล่วงหน้า</span>
            </div>

            <div v-if="fixedItems.length === 0" class="text-[11px] text-zinc-500 italic py-1">
              ไม่มีรายการราคาคงที่ (สามารถเพิ่มหรือใช้แบบกรอกยอดแต่ละรอบล้วนได้)
            </div>

            <div v-for="(it, idx) in fixedItems" :key="it.id" class="flex items-center gap-2">
              <input
                v-model="it.name"
                type="text"
                placeholder="ชื่อรายการ"
                class="flex-1 bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 focus:border-zinc-600 outline-none"
              />
              <div class="relative w-32">
                <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-[11px] text-zinc-500 font-mono">
                  {{ form.currency === 'USD' ? '$' : '฿' }}
                </span>
                <input
                  v-model.number="it.amount"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  class="w-full bg-zinc-950 border border-zinc-800 rounded pl-6 pr-2.5 py-1.5 text-xs text-zinc-100 font-mono text-right focus:border-zinc-600 outline-none"
                />
              </div>
              <button
                type="button"
                @click="removeFixedItem(idx)"
                class="p-1.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-zinc-800/80 transition-colors"
                title="ลบรายการ"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>

            <button
              type="button"
              @click="addFixedItem"
              class="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition-colors pt-1"
            >
              <Plus class="w-3 h-3" />
              <span>+ เพิ่มรายการราคาคงที่</span>
            </button>
          </div>

          <div class="border-t border-zinc-800/80"></div>

          <!-- 2. Dynamic Items -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">กรอกยอดแต่ละรอบ</span>
              <span class="text-[10px] text-zinc-500">กรอกราคาเมื่อชำระแต่ละรอบ</span>
            </div>

            <div v-if="dynamicItems.length === 0" class="text-[11px] text-zinc-500 italic py-1">
              ไม่มีรายการที่ต้องกรอกยอดแต่ละรอบ
            </div>

            <div v-for="(it, idx) in dynamicItems" :key="it.id" class="flex items-center gap-2">
              <input
                v-model="it.name"
                type="text"
                placeholder="ชื่อรายการ"
                class="flex-1 bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 focus:border-zinc-600 outline-none"
              />
              <span class="text-[11px] text-zinc-500 px-2 py-1 bg-zinc-950/60 rounded border border-zinc-800/60 whitespace-nowrap">
                กรอกตอนชำระ
              </span>
              <button
                type="button"
                @click="removeDynamicItem(idx)"
                class="p-1.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-zinc-800/80 transition-colors"
                title="ลบรายการ"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>

            <button
              type="button"
              @click="addDynamicItem"
              class="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition-colors pt-1"
            >
              <Plus class="w-3 h-3" />
              <span>+ เพิ่มรายการที่กรอกยอดแต่ละรอบ</span>
            </button>
          </div>

          <!-- 3. Auto-calculated Summary -->
          <div class="p-2.5 rounded bg-zinc-950/70 border border-zinc-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px]">
            <div class="text-zinc-300">
              รวมราคาคงที่: <span class="font-bold text-zinc-100 font-mono">{{ form.currency === 'USD' ? '$' : '฿' }}{{ formatNumber(itemizedFixedTotal) }}</span>
            </div>
            <div class="text-zinc-400">
              มี <span class="font-bold text-amber-400">{{ dynamicItems.length }}</span> รายการที่กรอกยอดตอนชำระ
            </div>
          </div>
        </div>
      </div>

      <!-- Free Trial Amount (Standard) -->
      <div v-else>
        <label class="block text-xs font-mono text-zinc-400 mb-1.5">
          Auto-Renew Cost <span class="text-rose-400">*</span>
        </label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">
            {{ form.currency === 'USD' ? '$' : (form.currency === 'THB' ? '฿' : '') }}
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
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Reminder Notification <span class="text-rose-400">*</span></label>
          <select
            v-model.number="form.alert_days_before"
            required
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option :value="null" disabled>Select reminder</option>
            <option :value="1">1 day prior</option>
            <option :value="2">2 days prior</option>
            <option :value="3">3 days prior</option>
            <option :value="5">5 days prior</option>
            <option :value="7">7 days prior</option>
          </select>
        </div>
      </div>

      <!-- Cost Calculation Bar -->
      <div class="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800/80 flex items-center justify-between text-xs font-mono">
        <span class="text-zinc-400">Monthly Projection:</span>
        <span class="font-semibold text-zinc-100">
          {{ form.currency === 'USD' ? '$' : (form.currency === 'THB' ? '฿' : '') }}{{ formatNumber(computedMonthlyCost) }} / mo
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
                placeholder="e.g. alex@example.com"
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
              placeholder="e.g. Settings > Account > Cancel Subscription"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors resize-none"
            ></textarea>
          </div>
        </div>
      </div>

      <div>
            <label class="block text-xs font-mono text-zinc-400 mb-1">{{ t('fin.linkedProject') }}</label>
            <select
              v-model="form.project"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
            >
              <option :value="null">—</option>
              <option v-for="p in workspaceStore.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSubscriptions } from '../../composables/finance/useSubscriptions'
import { useToastStore } from '../../stores/toast'
import { useWorkspaceStore } from '../../stores/workspace'
import { t } from '../../i18n'
import {
  ArrowLeft,
  Repeat,
  ShieldAlert,
  Check,
  Plus,
  Trash2
} from 'lucide-vue-next'

const router = useRouter()
const { createSubscription } = useSubscriptions()
const toast = useToastStore()
const workspaceStore = useWorkspaceStore()

onMounted(async () => {
  if (workspaceStore.projects.length === 0) {
    await workspaceStore.fetchProjects().catch(() => { /* select stays empty */ })
  }
})

const isSubmitting = ref(false)
const showAdvanced = ref(false)

interface LineItemDraft {
  id: string
  name: string
  type: 'FIXED' | 'DYNAMIC'
  amount: number | null
}

const isItemized = ref(false)
const fixedItems = ref<LineItemDraft[]>([])
const dynamicItems = ref<LineItemDraft[]>([])

function setPricingMode(itemized: boolean) {
  if (itemized === isItemized.value) return
  if (!itemized && (fixedItems.value.length > 0 || dynamicItems.value.length > 0)) {
    if (!confirm('สลับเป็นแบบยอดเดียว? ข้อมูลรายการย่อยที่กรอกไว้จะถูกซ่อน')) {
      return
    }
  }
  isItemized.value = itemized
  if (itemized && fixedItems.value.length === 0 && dynamicItems.value.length === 0) {
    if (form.value.amount && form.value.amount > 0) {
      fixedItems.value.push({
        id: crypto.randomUUID(),
        name: form.value.plan_name || form.value.title || 'ค่าบริการหลัก',
        type: 'FIXED',
        amount: Number(form.value.amount)
      })
    }
  }
}

function addFixedItem() {
  fixedItems.value.push({
    id: crypto.randomUUID(),
    name: '',
    type: 'FIXED',
    amount: null
  })
}

function removeFixedItem(idx: number) {
  fixedItems.value.splice(idx, 1)
}

function addDynamicItem() {
  dynamicItems.value.push({
    id: crypto.randomUUID(),
    name: '',
    type: 'DYNAMIC',
    amount: null
  })
}

function removeDynamicItem(idx: number) {
  dynamicItems.value.splice(idx, 1)
}

const itemizedFixedTotal = computed(() => {
  const sum = fixedItems.value.reduce((acc, it) => acc + (Number(it.amount) || 0), 0)
  return Math.round((sum + Number.EPSILON) * 100) / 100
})

const form = ref({
  type: 'SUBSCRIPTION' as 'SUBSCRIPTION' | 'FREE_TRIAL',
  title: '',
  plan_name: '',
  category: '',
  billing_cycle: '' as 'MONTHLY' | 'YEARLY' | 'QUARTERLY' | 'WEEKLY' | '',
  amount: null as number | null,
  currency: '',
  due_date: '',
  alert_days_before: null as number | null,
  account_email: '',
  payment_method: '',
  project: null as string | null,
  cancel_url: '',
  cancel_steps: ''
})

const computedMonthlyCost = computed(() => {
  const amt = (isItemized.value && form.value.type === 'SUBSCRIPTION')
    ? itemizedFixedTotal.value
    : Number(form.value.amount || 0)
  if (!amt || !form.value.billing_cycle) return 0
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
  if (!form.value.category) {
    toast.error('Please select a category')
    return
  }
  if (!form.value.billing_cycle) {
    toast.error('Please select a billing cycle')
    return
  }
  if (!form.value.currency) {
    toast.error('Please select a currency')
    return
  }
  if (!form.value.due_date) {
    toast.error('Please select a date')
    return
  }

  const isSubItemized = (form.value.type === 'SUBSCRIPTION' && isItemized.value)

  if (isSubItemized) {
    const totalCount = fixedItems.value.length + dynamicItems.value.length
    if (totalCount === 0) {
      toast.error('กรุณาเพิ่มรายการค่าใช้จ่ายอย่างน้อย 1 รายการ')
      return
    }
    for (const it of [...fixedItems.value, ...dynamicItems.value]) {
      if (!it.name.trim()) {
        toast.error('กรุณาระบุชื่อรายการให้ครบทุกรายการ')
        return
      }
    }
    for (const it of fixedItems.value) {
      if (it.amount === null || it.amount === undefined || String(it.amount).trim() === '' || isNaN(Number(it.amount))) {
        toast.error(`กรุณาระบุราคาสำหรับรายการ '${it.name || 'คงที่'}' (ห้ามเว้นว่าง)`)
        return
      }
      const num = Number(it.amount)
      if (!isFinite(num) || num < 0) {
        toast.error(`ราคาสำหรับรายการ '${it.name}' ต้องเป็นตัวเลขที่ถูกต้องและไม่ติดลบ`)
        return
      }
    }
  } else {
    if (form.value.amount === null || form.value.amount === undefined || String(form.value.amount).trim() === '' || isNaN(Number(form.value.amount))) {
      toast.error('Please enter an amount')
      return
    }
  }

  isSubmitting.value = true
  try {
    const billingDay = form.value.due_date ? new Date(form.value.due_date).getDate() : undefined

    const finalAmount = isSubItemized ? itemizedFixedTotal.value : Number(form.value.amount || 0)

    const metadataPayload: Record<string, any> = {
      plan_name: form.value.plan_name.trim(),
      billing_cycle: form.value.billing_cycle,
      account_email: form.value.account_email.trim(),
      payment_method: form.value.payment_method.trim(),
      category: form.value.category,
      cancel_url: form.value.cancel_url.trim(),
      cancel_steps: form.value.cancel_steps.trim(),
      alert_days_before: Number(form.value.alert_days_before || 3),
      auto_renew_cost: finalAmount,
      is_itemized: isSubItemized
    }

    if (isSubItemized) {
      metadataPayload.items = [
        ...fixedItems.value.map(it => ({
          id: it.id,
          name: it.name.trim(),
          type: 'FIXED',
          amount: Math.round((Number(it.amount) + Number.EPSILON) * 100) / 100
        })),
        ...dynamicItems.value.map(it => ({ id: it.id, name: it.name.trim(), type: 'DYNAMIC', amount: null }))
      ]
    }

    const payload = {
      title: form.value.title.trim(),
      type: form.value.type,
      amount: finalAmount,
      currency: form.value.currency,
      due_date: form.value.due_date,
      billing_day: billingDay,
      project: form.value.project,
      metadata: metadataPayload
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
