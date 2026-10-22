<template>
  <div class="space-y-6 max-w-5xl mx-auto font-sans pb-12">
    <!-- Breadcrumb & Header -->
    <div class="pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-2 text-xs font-mono text-zinc-500 mb-2">
        <router-link to="/finance/overview" class="hover:text-zinc-300 transition-colors">Finance</router-link>
        <span>/</span>
        <router-link to="/finance/installments" class="hover:text-zinc-300 transition-colors">Installments & Contracts</router-link>
        <span>/</span>
        <span class="text-zinc-300">New Contract</span>
      </div>

      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2.5">
            <h1 class="text-xl font-semibold text-zinc-100 tracking-tight">Originate Installment Contract</h1>
            <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
              NEW CONTRACT
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-1">
            Establish a vehicle hire-purchase contract, formal personal loan, or 0% product installment schedule
          </p>
        </div>

        <div class="flex items-center gap-2 self-start sm:self-auto">
          <router-link
            to="/finance/installments"
            class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-mono transition-colors"
          >
            Cancel
          </router-link>
          <button
            @click="handleSubmit"
            :disabled="isSubmitting || !isFormValid"
            type="button"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50 cursor-pointer"
          >
            <Loader2 v-if="isSubmitting" class="w-3.5 h-3.5 animate-spin" />
            <Check v-else class="w-3.5 h-3.5 text-zinc-950" />
            <span>{{ isSubmitting ? 'Creating Contract...' : 'Create Contract' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Main Creation Form Grid -->
    <form @submit.prevent="handleSubmit" class="space-y-6">
      <!-- 1. Contract Category Selection -->
      <div class="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-4">
        <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono flex items-center gap-2">
          <FileText class="w-4 h-4 text-zinc-400" />
          <span>1. Contract Type & Category</span>
        </h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <!-- Type Option A: Vehicle Hire Purchase -->
          <div
            @click="form.subtype = 'HIRE_PURCHASE'"
            class="p-4 rounded-lg border cursor-pointer transition-all space-y-2 select-none"
            :class="form.subtype === 'HIRE_PURCHASE'
              ? 'bg-zinc-800/60 border-zinc-500 ring-1 ring-zinc-500'
              : 'bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700'"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Car class="w-4 h-4 text-zinc-300" />
                <span class="text-sm font-semibold text-zinc-100">Vehicle Hire Purchase</span>
              </div>
              <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
                OCPB 2023 Regulated
              </span>
            </div>
            <p class="text-xs text-zinc-400 font-sans leading-relaxed">
              Automobile & motorcycle lease agreements with flat rate interest, down payment, and statutory early payoff discount calculations.
            </p>
          </div>

          <!-- Type Option B: Standard 0% or Bank Loan -->
          <div
            @click="form.subtype = 'STANDARD'"
            class="p-4 rounded-lg border cursor-pointer transition-all space-y-2 select-none"
            :class="form.subtype === 'STANDARD'
              ? 'bg-zinc-800/60 border-zinc-500 ring-1 ring-zinc-500'
              : 'bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700'"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <CreditCard class="w-4 h-4 text-zinc-300" />
                <span class="text-sm font-semibold text-zinc-100">Standard / 0% Installment</span>
              </div>
              <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
                Fixed Term
              </span>
            </div>
            <p class="text-xs text-zinc-400 font-sans leading-relaxed">
              Credit card installment plans (0% 10-month), consumer electronics (Apple, Samsung), appliances, or personal bank loans.
            </p>
          </div>
        </div>
      </div>

      <!-- 2. Primary Identifiers -->
      <div class="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-4">
        <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono flex items-center gap-2">
          <Layers class="w-4 h-4 text-zinc-400" />
          <span>2. Identification & Creditor</span>
        </h2>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="space-y-1.5 sm:col-span-2">
            <label class="block text-xs font-mono text-zinc-400">
              Contract Title / Item Name <span class="text-rose-400">*</span>
            </label>
            <input
              v-model="form.title"
              type="text"
              required
              placeholder="e.g. Honda Civic e:HEV RS, MacBook Pro M3, Personal Loan"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-sans outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Lender / Finance Institution <span class="text-rose-400">*</span>
            </label>
            <input
              v-model="form.lender"
              type="text"
              required
              placeholder="e.g. Krungsri Auto, Tisco, KBank, SCB"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-sans outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Contract / Account Reference Number
            </label>
            <input
              v-model="form.contract_number"
              type="text"
              placeholder="e.g. HP-2024-998811"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              First Payment Due Date <span class="text-rose-400">*</span>
            </label>
            <input
              v-model="form.due_date"
              type="date"
              required
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Monthly Due Day of Month
            </label>
            <input
              v-model.number="form.billing_day"
              type="number"
              min="1"
              max="31"
              placeholder="e.g. 5, 10, 25"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
            />
          </div>
        </div>
      </div>

      <!-- 3. Financial Terms & Term Tenor -->
      <div class="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-4">
        <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono flex items-center gap-2">
          <Calculator class="w-4 h-4 text-zinc-400" />
          <span>3. Financial Terms & Loan Parameters</span>
        </h2>

        <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Financed Principal (฿) <span class="text-rose-400">*</span>
            </label>
            <input
              v-model.number="form.financed_amount"
              type="number"
              min="0"
              step="0.01"
              required
              placeholder="0.00"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono font-semibold outline-none transition-colors"
            />
          </div>

          <div v-if="form.subtype === 'HIRE_PURCHASE'" class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Down Payment (฿)
            </label>
            <input
              v-model.number="form.down_payment"
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Flat Interest Rate (% p.a.)
            </label>
            <input
              v-model.number="form.flat_rate_pa"
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00 (0% for interest-free)"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Total Terms (Months) <span class="text-rose-400">*</span>
            </label>
            <input
              v-model.number="form.total_terms"
              type="number"
              min="1"
              max="120"
              required
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono font-semibold outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Current Paid Terms (Start At)
            </label>
            <input
              v-model.number="form.current_term"
              type="number"
              min="0"
              :max="form.total_terms"
              placeholder="0 (if brand new)"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
            />
          </div>
        </div>

        <!-- Tenor Preset Pills -->
        <div class="flex items-center gap-1.5 flex-wrap pt-1">
          <span class="text-[11px] font-mono text-zinc-500 mr-1">Common Tenors:</span>
          <button
            v-for="t in [6, 10, 12, 24, 36, 48, 60, 72, 84]"
            :key="t"
            type="button"
            @click="form.total_terms = t"
            class="px-2.5 py-0.5 rounded text-[11px] font-mono border transition-colors"
            :class="form.total_terms === t
              ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-bold'
              : 'bg-zinc-950 text-zinc-400 border-zinc-800 hover:text-zinc-200 hover:border-zinc-700'"
          >
            {{ t }}m
          </button>
        </div>

        <!-- Real-Time Loan Calculation Preview Card -->
        <div class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <span class="text-[10px] text-zinc-500 uppercase block">Monthly Installment</span>
            <span class="text-base font-bold text-zinc-100 tabular-nums">
              ฿{{ calculatedMonthlyInstallment.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            </span>
            <span class="text-[10px] text-zinc-500 block">per month</span>
          </div>

          <div>
            <span class="text-[10px] text-zinc-500 uppercase block">Total Interest</span>
            <span class="text-base font-semibold text-zinc-300 tabular-nums">
              ฿{{ calculatedTotalInterest.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            </span>
            <span class="text-[10px] text-zinc-500 block">over {{ form.total_terms }} months</span>
          </div>

          <div>
            <span class="text-[10px] text-zinc-500 uppercase block">Total Repayment</span>
            <span class="text-base font-semibold text-zinc-100 tabular-nums">
              ฿{{ calculatedTotalRepayment.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            </span>
            <span class="text-[10px] text-zinc-500 block">Principal + Interest</span>
          </div>

          <div>
            <span class="text-[10px] text-zinc-500 uppercase block">Initial Remaining</span>
            <span class="text-base font-semibold text-zinc-300 tabular-nums">
              ฿{{ calculatedInitialRemaining.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            </span>
            <span class="text-[10px] text-zinc-500 block">{{ form.total_terms - form.current_term }} terms left</span>
          </div>
        </div>
      </div>

      <!-- 4. Vehicle Specific Details (if HIRE_PURCHASE) -->
      <div v-if="form.subtype === 'HIRE_PURCHASE'" class="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-4">
        <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono flex items-center gap-2">
          <Car class="w-4 h-4 text-zinc-400" />
          <span>4. Vehicle & Insurance Registration Details</span>
        </h2>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Vehicle Model / Variant
            </label>
            <input
              v-model="form.vehicle_model"
              type="text"
              placeholder="e.g. Honda Civic FE 1.5 Turbo RS"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-sans outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              License Plate & Province
            </label>
            <input
              v-model="form.license_plate"
              type="text"
              placeholder="e.g. 1AB 8888 Bangkok"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Annual Tax Expiry Date
            </label>
            <input
              v-model="form.tax_expiry_date"
              type="date"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Insurance Provider
            </label>
            <input
              v-model="form.insurance_provider"
              type="text"
              placeholder="e.g. Viriyah Insurance, Bangkok Insurance"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-sans outline-none transition-colors"
            />
          </div>

          <div class="space-y-1.5 sm:col-span-2">
            <label class="block text-xs font-mono text-zinc-400">
              Insurance Policy Number
            </label>
            <input
              v-model="form.policy_number"
              type="text"
              placeholder="e.g. POL-2024-998811-A"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
            />
          </div>
        </div>
      </div>

      <!-- 5. Additional Notes -->
      <div class="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-4">
        <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono flex items-center gap-2">
          <Calendar class="w-4 h-4 text-zinc-400" />
          <span>5. Contract Notes</span>
        </h2>

        <div>
          <textarea
            v-model="form.notes"
            rows="3"
            placeholder="Add relevant clauses, payment channels, auto-debit account, or special dealer promotions..."
            class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-sans outline-none transition-colors"
          />
        </div>
      </div>

      <!-- Footer Buttons -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800/80">
        <router-link
          to="/finance/installments"
          class="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-mono transition-colors"
        >
          Cancel
        </router-link>
        <button
          type="submit"
          :disabled="isSubmitting || !isFormValid"
          class="px-5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50 cursor-pointer"
        >
          <Loader2 v-if="isSubmitting" class="w-3.5 h-3.5 animate-spin" />
          <Check v-else class="w-3.5 h-3.5 text-zinc-950" />
          <span>{{ isSubmitting ? 'Creating Contract...' : 'Create Contract' }}</span>
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
  FileText,
  Car,
  CreditCard,
  Layers,
  Calculator,
  Calendar,
  Check,
  Loader2
} from 'lucide-vue-next'

const router = useRouter()
const toast = useToastStore()
const { createInstallment } = useInstallments()

const isSubmitting = ref(false)

const form = reactive({
  title: '',
  subtype: 'HIRE_PURCHASE' as 'HIRE_PURCHASE' | 'STANDARD',
  lender: '',
  contract_number: '',
  due_date: new Date().toISOString().split('T')[0],
  billing_day: new Date().getDate(),
  financed_amount: 500000,
  down_payment: 100000,
  flat_rate_pa: 2.49,
  total_terms: 48,
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

const calculatedInitialRemaining = computed(() => {
  const remTerms = Math.max(0, form.total_terms - form.current_term)
  return remTerms * calculatedMonthlyInstallment.value
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
