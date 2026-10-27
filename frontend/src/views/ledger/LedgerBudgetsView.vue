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
          <span class="text-xs font-mono text-zinc-300">Budgets</span>
        </div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Category Budgets</h1>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
        <input
          v-model="activeMonth"
          type="month"
          @change="loadBudgets"
          class="px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-xs font-mono text-zinc-200 outline-none focus:border-zinc-500 transition-colors"
        />

        <button
          @click="openCreateBudgetModal"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-all active:scale-[0.98] flex items-center gap-1.5 shadow-sm hover:shadow-white/10"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>+ Set Budget</span>
        </button>
      </div>
    </div>

    <!-- Executive Budget Summary Strip -->
    <div v-if="ledgerStore.budgets.length > 0" class="grid grid-cols-1 sm:grid-cols-3 gap-3.5 font-mono text-xs">
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Total Budget Limit</span>
        <div class="text-2xl font-bold text-zinc-100 mt-2 tabular-nums tracking-tight">
          ฿{{ totalBudgetCap.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5">Across {{ ledgerStore.budgets.length }} active categories</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Total Spent This Month</span>
        <div class="text-2xl font-bold text-zinc-200 mt-2 tabular-nums tracking-tight">
          ฿{{ totalBudgetSpent.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5">{{ overallUsagePct }}% of allocated limit</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Remaining Buffer</span>
        <div
          class="text-2xl font-bold mt-2 tabular-nums tracking-tight"
          :class="totalBudgetCushion < 0 ? 'text-rose-400' : 'text-emerald-400'"
        >
          ฿{{ totalBudgetCushion.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5 flex items-center gap-1">
          <AlertTriangle v-if="totalBudgetCushion < 0" class="w-3 h-3 text-rose-400" />
          {{ totalBudgetCushion < 0 ? 'Over Budget' : 'Remaining Cushion' }}
        </span>
      </div>
    </div>

    <!-- Budgets Grid -->
    <div v-if="ledgerStore.budgets.length === 0" class="p-16 rounded-xl bg-zinc-900/20 border border-zinc-800/80 text-center space-y-3 font-mono text-xs text-zinc-500">
      <p>No category budgets allocated for {{ activeMonth }}.</p>
      <button
        @click="openCreateBudgetModal"
        class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-medium text-xs transition-colors inline-block shadow-sm"
      >
        + Allocate Category Budget
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 font-mono">
      <div
        v-for="b in ledgerStore.budgets"
        :key="b.id"
        class="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200 space-y-4"
      >
        <div class="flex items-start justify-between">
          <div>
            <h3 class="text-sm font-semibold text-zinc-100 font-sans">{{ b.category_name }}</h3>
            <span class="text-[10px] text-zinc-400">{{ b.period_month }}</span>
          </div>

          <div class="flex items-center gap-1.5">
            <span
              class="text-xs font-bold mr-1"
              :class="b.usage_pct >= 90 ? 'text-rose-400' : (b.usage_pct >= 75 ? 'text-amber-400' : 'text-emerald-400')"
            >
              {{ b.usage_pct }}%
            </span>
            <button
              @click="openEditBudgetModal(b)"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-indigo-400 hover:bg-indigo-500/10 active:scale-[0.95] transition-all"
              title="Edit budget limit"
            >
              <Edit2 class="w-3.5 h-3.5" />
            </button>
            <button
              @click="confirmDeleteBudget(b.id, b.category_name)"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 active:scale-[0.95] transition-all"
              title="Delete this budget"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Gauge Progress Bar -->
        <div class="space-y-1.5">
          <div class="w-full bg-zinc-800/80 h-2 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="b.usage_pct >= 90 ? 'bg-rose-500' : (b.usage_pct >= 75 ? 'bg-amber-400' : 'bg-emerald-400')"
              :style="{ width: `${Math.min(100, b.usage_pct)}%` }"
            />
          </div>

          <div class="flex justify-between text-xs pt-1">
            <span class="text-zinc-300">
              Spent: ฿{{ Number(b.spent_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
            </span>
            <span class="text-zinc-400">
              Limit: ฿{{ Number(b.limit_amount).toLocaleString('en-US') }}
            </span>
          </div>
        </div>

        <!-- Remaining -->
        <div class="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-xs">
          <span class="text-[11px] text-zinc-400">Remaining:</span>
          <span
            class="font-bold tabular-nums"
            :class="Number(b.remaining_amount) < 0 ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'"
          >
            ฿{{ Number(b.remaining_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Create Budget Modal -->
    <div
      v-if="showCreateBudgetModal"
      @click.self="showCreateBudgetModal = false"
      class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-hidden font-sans"
    >
      <div class="relative bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col shadow-2xl overflow-hidden font-mono text-xs">
        <div class="shrink-0 px-4 sm:px-6 py-3.5 border-b border-zinc-800 flex items-center justify-between font-sans">
          <h3 class="text-base font-semibold text-zinc-100">
            {{ editingBudget ? 'Edit Budget Limit' : 'Set Category Budget' }}
          </h3>
          <button
            @click="showCreateBudgetModal = false"
            class="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <form @submit.prevent="handleSaveBudget" class="flex flex-col flex-1 min-h-0 overflow-hidden">
          <div class="flex-1 overflow-y-auto overscroll-contain min-h-0 p-4 sm:p-6 space-y-4">
            <div>
              <label class="block text-[11px] text-zinc-300 mb-1 font-medium font-sans">Expense Category <span class="text-rose-400">*</span></label>
              <div v-if="editingBudget" class="px-3 py-2 rounded-md bg-zinc-900/60 border border-zinc-800 text-zinc-200 font-mono text-xs flex items-center justify-between">
                <span>{{ editingBudget.category_name }}</span>
                <span class="text-[10px] text-zinc-500">{{ editingBudget.period_month }}</span>
              </div>
              <select
                v-else
                v-model="newBudgetCategory"
                required
                class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono transition-colors"
              >
                <option value="" disabled>Select category</option>
                <option
                  v-for="c in expenseCategories"
                  :key="c.id"
                  :value="c.id"
                >
                  {{ c.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-[11px] text-zinc-300 mb-1 font-medium font-sans">Monthly Limit (฿) <span class="text-rose-400">*</span></label>
              <input
                v-model.number="newBudgetLimit"
                type="number"
                step="100"
                required
                placeholder="0.00"
                class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono transition-colors"
              />
            </div>
          </div>

          <div class="shrink-0 p-4 border-t border-zinc-800/80 bg-zinc-950/90 flex items-center justify-end gap-2.5">
            <button
              type="button"
              @click="showCreateBudgetModal = false"
              class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-sans transition-all active:scale-[0.98]"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isSaving"
              class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-semibold transition-all active:scale-[0.98] disabled:opacity-50 shadow-sm cursor-pointer"
            >
              {{ isSaving ? 'Saving...' : (editingBudget ? 'Save Changes' : 'Save Budget') }}
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
      :is-loading="confirmModal.isLoading"
      :error-message="confirmModal.errorMessage"
      @confirm="executeConfirmAction"
      @cancel="confirmModal.isOpen = false; confirmModal.errorMessage = ''"
    />
  </div>
</template>

<script setup lang="ts">
import {
 ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useLedgerStore } from '../../stores/ledger'
import { useToastStore } from '../../stores/toast'
import { ledgerApi } from '../../api/ledger'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import type { CategoryBudgetItem } from '../../types/ledger'
import {
  AlertTriangle,
  ArrowLeft,
  Plus,
  X,
  Trash2,
  Edit2
} from 'lucide-vue-next'

const ledgerStore = useLedgerStore()
const toast = useToastStore()
const now = new Date()
const activeMonth = ref<string>(
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
)

const showCreateBudgetModal = ref(false)
const editingBudget = ref<CategoryBudgetItem | null>(null)
const isSaving = ref(false)
const newBudgetCategory = ref('')
const newBudgetLimit = ref<number | null>(null)

useBodyScrollLock(() => showCreateBudgetModal.value)

function openCreateBudgetModal() {
  editingBudget.value = null
  newBudgetCategory.value = ''
  newBudgetLimit.value = null
  showCreateBudgetModal.value = true
}

function openEditBudgetModal(b: CategoryBudgetItem) {
  editingBudget.value = b
  newBudgetCategory.value = b.category
  newBudgetLimit.value = Number(b.limit_amount)
  showCreateBudgetModal.value = true
}

const totalBudgetCap = computed(() => {
  return ledgerStore.budgets.reduce((sum, b) => sum + Number(b.limit_amount || 0), 0)
})

const totalBudgetSpent = computed(() => {
  return ledgerStore.budgets.reduce((sum, b) => sum + Number(b.spent_amount || 0), 0)
})

const totalBudgetCushion = computed(() => {
  return totalBudgetCap.value - totalBudgetSpent.value
})

const overallUsagePct = computed(() => {
  if (totalBudgetCap.value <= 0) return 0
  return Math.round((totalBudgetSpent.value / totalBudgetCap.value) * 100)
})

const expenseCategories = computed(() =>
  ledgerStore.categories.filter((c) => c.category_type === 'EXPENSE')
)

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  isLoading: false,
  errorMessage: '',
  action: async () => {}
})

async function executeConfirmAction() {
  confirmModal.isLoading = true
  confirmModal.errorMessage = ''
  try {
    await confirmModal.action()
    confirmModal.isOpen = false
  } catch (err: any) {
    confirmModal.errorMessage = err?.response?.data?.error || err?.message || 'Operation failed'
  } finally {
    confirmModal.isLoading = false
  }
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && showCreateBudgetModal.value) {
    showCreateBudgetModal.value = false
  }
}

watch(showCreateBudgetModal, (open) => {
  if (open) {
    window.addEventListener('keydown', handleKeyDown)
  } else {
    window.removeEventListener('keydown', handleKeyDown)
    editingBudget.value = null
    newBudgetCategory.value = ''
    newBudgetLimit.value = null
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

onMounted(async () => {
  await Promise.all([
    ledgerStore.fetchCategories('EXPENSE'),
    loadBudgets()
  ])
})

async function loadBudgets() {
  await ledgerStore.fetchBudgets(activeMonth.value)
}

async function handleSaveBudget() {
  if (isSaving.value) return
  if (newBudgetLimit.value === null || newBudgetLimit.value <= 0) {
    toast.error('Please enter a valid budget limit')
    return
  }
  if (!editingBudget.value && !newBudgetCategory.value) {
    toast.error('Please select an expense category')
    return
  }
  isSaving.value = true
  try {
    if (editingBudget.value) {
      await ledgerApi.updateBudget(editingBudget.value.id, {
        limit_amount: newBudgetLimit.value
      })
      toast.success('Budget limit updated successfully')
    } else {
      await ledgerApi.createBudget({
        category: newBudgetCategory.value,
        period_month: activeMonth.value,
        limit_amount: newBudgetLimit.value
      })
      toast.success('Category budget allocated successfully')
    }
    showCreateBudgetModal.value = false
    editingBudget.value = null
    await loadBudgets()
  } catch (err: any) {
    toast.error(err?.response?.data?.limit_amount || err?.response?.data?.error || 'Failed to save budget limit')
  } finally {
    isSaving.value = false
  }
}

function confirmDeleteBudget(id: string, name?: string) {
  const categoryName = name || 'Category'
  confirmModal.title = 'Remove Category Budget'
  confirmModal.message = `Are you sure you want to remove the monthly spending limit for "${categoryName}"?`
  confirmModal.confirmText = 'Remove Budget'
  confirmModal.isDanger = true
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    await ledgerApi.deleteBudget(id)
    toast.success(`Removed budget for ${categoryName}`)
    await loadBudgets()
  }
  confirmModal.isOpen = true
}
</script>
