<template>
  <div class="max-w-xl mx-auto py-4 font-sans pb-16 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <router-link
          to="/finance/installments"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Installments"
        >
          <ArrowLeft class="w-4 h-4" />
        </router-link>
        <div>
          <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Installment Contract</h1>
          <p class="text-xs text-zinc-500 mt-0.5">
            Record a hire-purchase loan, 0% installment plan, or fixed-term credit
          </p>
        </div>
      </div>
    </div>

    <!-- Subtype Selector -->
    <div class="grid grid-cols-2 gap-1 p-1 bg-zinc-900/80 border border-zinc-800 rounded-lg">
      <button
        type="button"
        @click="form.subtype = 'STANDARD'"
        class="py-2 px-3 rounded text-xs font-medium transition-colors flex items-center justify-center gap-2"
        :class="form.subtype === 'STANDARD' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <CreditCard class="w-3.5 h-3.5" />
        <span>Standard / 0% Plan</span>
      </button>

      <button
        type="button"
        @click="form.subtype = 'HIRE_PURCHASE'"
        class="py-2 px-3 rounded text-xs font-medium transition-colors flex items-center justify-center gap-2"
        :class="form.subtype === 'HIRE_PURCHASE' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <Car class="w-3.5 h-3.5" />
        <span>Vehicle Hire Purchase</span>
      </button>
    </div>

    <!-- Main Clean Form -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Title & Lender -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Item / Contract Name <span class="text-rose-400">*</span>
          </label>
          <input
            v-model="form.title"
            type="text"
            required
            placeholder="e.g. MacBook Pro M3, Car Loan"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Lender / Bank <span class="text-rose-400">*</span>
          </label>
          <input
            v-model="form.lender"
            type="text"
            required
            placeholder="e.g. KBank, Krungsri Auto, SCB"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>
      </div>

      <!-- Financed Amount & Flat Rate -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Financed Principal (฿) <span class="text-rose-400">*</span>
          </label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">฿</span>
            <input
              v-model.number="form.financed_amount"
              type="number"
              min="1"
              step="0.01"
              required
              placeholder="0.00"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-7 pr-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
            />
          </div>
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Flat Interest Rate (% p.a.)
          </label>
          <input
            v-model.number="form.flat_rate_pa"
            type="number"
            min="0"
            step="0.01"
            placeholder="0.00 (0% for interest-free)"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>
      </div>

      <!-- Total Terms & First Due Date -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-xs font-mono text-zinc-400">
              Total Terms (Months) <span class="text-rose-400">*</span>
            </label>
            <div class="flex items-center gap-1">
              <button
                v-for="t in [6, 10, 12, 24, 48]"
                :key="t"
                type="button"
                @click="form.total_terms = t"
                class="px-1.5 py-0.5 rounded text-[10px] font-mono border transition-colors"
                :class="form.total_terms === t ? 'bg-zinc-800 text-zinc-100 border-zinc-600' : 'text-zinc-500 border-zinc-800 hover:text-zinc-300'"
              >
                {{ t }}m
              </button>
            </div>
          </div>
          <input
            v-model.number="form.total_terms"
            type="number"
            min="1"
            max="120"
            required
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            First Payment Due Date <span class="text-rose-400">*</span>
          </label>
          <input
            v-model="form.due_date"
            type="date"
            required
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>
      </div>

      <!-- Real-Time Loan Calculation Strip -->
      <div class="p-3.5 rounded-lg bg-zinc-900/50 border border-zinc-800/80 grid grid-cols-3 gap-3 text-xs font-mono">
        <div>
          <span class="text-[10px] text-zinc-500 uppercase block">Monthly Installment</span>
          <span class="text-sm font-bold text-zinc-100 tabular-nums">
            ฿{{ calculatedMonthlyInstallment.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </span>
        </div>

        <div>
          <span class="text-[10px] text-zinc-500 uppercase block">Total Interest</span>
          <span class="text-sm font-medium text-zinc-300 tabular-nums">
            ฿{{ calculatedTotalInterest.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </span>
        </div>

        <div>
          <span class="text-[10px] text-zinc-500 uppercase block">Total Obligation</span>
          <span class="text-sm font-semibold text-zinc-100 tabular-nums">
            ฿{{ calculatedTotalRepayment.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </span>
        </div>
      </div>

      <!-- Progressive Disclosure: Additional Details -->
      <div class="pt-1">
        <button
          type="button"
          @click="showAdvanced = !showAdvanced"
          class="text-xs font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1.5 transition-colors"
        >
          <span>{{ showAdvanced ? '- Less Details' : '+ Contract & Asset Details (Optional)' }}</span>
        </button>

        <div v-if="showAdvanced" class="mt-3 space-y-3 pt-3 border-t border-zinc-800/60">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Contract Number</label>
              <input
                v-model="form.contract_number"
                type="text"
                placeholder="e.g. HP-998811"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>

            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Monthly Billing Day</label>
              <input
                v-model.number="form.billing_day"
                type="number"
                min="1"
                max="31"
                placeholder="5"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>

            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Already Paid Terms</label>
              <input
                v-model.number="form.current_term"
                type="number"
                min="0"
                :max="form.total_terms"
                placeholder="0"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>
          </div>

          <div v-if="form.subtype === 'HIRE_PURCHASE'" class="space-y-3 pt-2 border-t border-zinc-800/40">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-mono text-zinc-400 mb-1">Down Payment (฿)</label>
                <input
                  v-model.number="form.down_payment"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
                />
              </div>

              <div>
                <label class="block text-xs font-mono text-zinc-400 mb-1">Vehicle License Plate</label>
                <input
                  v-model="form.license_plate"
                  type="text"
                  placeholder="e.g. 1AB 8888 Bangkok"
                  class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-mono text-zinc-400 mb-1">Insurance Provider</label>
                <input
                  v-model="form.insurance_provider"
                  type="text"
                  placeholder="e.g. Viriyah, Bangkok Insurance"
                  class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
                />
              </div>

              <div>
                <label class="block text-xs font-mono text-zinc-400 mb-1">Tax Expiry Date</label>
                <input
                  v-model="form.tax_expiry_date"
                  type="date"
                  class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
                />
              </div>
            </div>
          </div>

          <div>
            <label class="block text-xs font-mono text-zinc-400 mb-1">Notes</label>
            <textarea
              v-model="form.notes"
              rows="2"
              placeholder="e.g. 0% promotion, warranty notes"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors resize-none"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
        <router-link
          to="/finance/installments"
          class="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 font-medium transition-colors"
        >
          Cancel
        </router-link>
        <button
          type="submit"
          :disabled="isSubmitting || !isFormValid"
          class="px-5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
        >
          <Loader2 v-if="isSubmitting" class="w-3.5 h-3.5 animate-spin" />
          <Check v-else class="w-3.5 h-3.5" />
          <span>{{ isSubmitting ? 'Creating...' : 'Create Contract' }}</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useInstallments } from '../../composables/finance/useInstallments'
import { useToastStore } from '../../stores/toast'
import {
  ArrowLeft,
  Car,
  CreditCard,
  Check,
  Loader2
} from 'lucide-vue-next'

const router = useRouter()
const toast = useToastStore()
const { createInstallment } = useInstallments()

const isSubmitting = ref(false)
const showAdvanced = ref(false)

const form = reactive({
  title: '',
  subtype: 'STANDARD' as 'HIRE_PURCHASE' | 'STANDARD',
  lender: '',
  contract_number: '',
  due_date: new Date().toISOString().split('T')[0],
  billing_day: new Date().getDate(),
  financed_amount: 30000,
  down_payment: 0,
  flat_rate_pa: 0,
  total_terms: 10,
  current_term: 0,
  vehicle_model: '',
  license_plate: '',
  insurance_provider: '',
  policy_number: '',
  tax_expiry_date: '',
  notes: ''
})

const isFormValid = computed(() => {
  return (
    form.title.trim().length > 0 &&
    form.lender.trim().length > 0 &&
    form.financed_amount > 0 &&
    form.total_terms > 0 &&
    form.due_date.length > 0
  )
})

const calculatedTotalInterest = computed(() => {
  if (form.total_terms <= 0 || form.financed_amount <= 0 || form.flat_rate_pa <= 0) return 0
  const years = form.total_terms / 12
  return form.financed_amount * (form.flat_rate_pa / 100) * years
})

const calculatedTotalRepayment = computed(() => {
  return form.financed_amount + calculatedTotalInterest.value
})

const calculatedMonthlyInstallment = computed(() => {
  if (form.total_terms <= 0) return 0
  return calculatedTotalRepayment.value / form.total_terms
})

async function handleSubmit() {
  if (!isFormValid.value || isSubmitting.value) return
  isSubmitting.value = true

  try {
    const payload: any = {
      title: form.title.trim(),
      type: 'INSTALLMENT',
      subtype: form.subtype,
      direction: 'OUTFLOW',
      amount: Number(calculatedMonthlyInstallment.value.toFixed(2)),
      currency: 'THB',
      status: form.current_term >= form.total_terms ? 'COMPLETED' : 'ACTIVE',
      due_date: form.due_date,
      billing_day: form.billing_day || undefined,
      metadata: {
        subtype: form.subtype,
        total_terms: form.total_terms,
        current_term: form.current_term,
        lender: form.lender.trim(),
        total_principal: form.financed_amount.toString(),
        financed_amount: form.financed_amount.toString(),
        down_payment: form.down_payment.toString(),
        flat_rate_pa: form.flat_rate_pa.toString(),
        contract_number: form.contract_number.trim(),
        notes: form.notes.trim()
      }
    }

    if (form.subtype === 'HIRE_PURCHASE') {
      payload.metadata.vehicle_model = form.vehicle_model.trim() || form.title.trim()
      payload.metadata.license_plate = form.license_plate.trim()
      payload.metadata.insurance_provider = form.insurance_provider.trim()
      payload.metadata.policy_number = form.policy_number.trim()
      if (form.tax_expiry_date) {
        payload.metadata.tax_expiry_date = form.tax_expiry_date
      }
    }

    const created = await createInstallment(payload)
    toast.success('Installment contract created successfully')
    router.push(`/finance/installments/${created.id}`)
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.response?.data?.metadata || err?.message || 'Failed to create contract'
    toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally {
    isSubmitting.value = false
  }
}
</script>
