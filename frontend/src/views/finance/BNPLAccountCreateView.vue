<template>
  <div class="max-w-xl mx-auto py-4 font-sans pb-16 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          type="button"
          @click="router.push('/finance/bnpl')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
          title="Back to Credit Accounts"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Credit Line</h1>
          <p class="text-xs text-zinc-500 mt-0.5">
            Configure revolving BNPL credit limit and billing cycle dates
          </p>
        </div>
      </div>
    </div>

    <!-- Quick Provider Suggestion Chips -->
    <div class="space-y-1.5">
      <span class="text-[11px] font-mono uppercase text-zinc-500">Popular Providers</span>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="preset in providerPresets"
          :key="preset.name"
          type="button"
          @click="applyPreset(preset)"
          class="px-2.5 py-1 rounded text-xs font-mono border transition-colors cursor-pointer"
          :class="form.title === preset.name
            ? 'bg-zinc-800 text-zinc-100 border-zinc-600'
            : 'bg-zinc-950 text-zinc-400 border-zinc-800 hover:text-zinc-200 hover:border-zinc-700'"
        >
          {{ preset.name }}
        </button>
      </div>
    </div>

    <!-- Main Clean Form -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Title & Provider -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Account Display Name <span class="text-rose-400">*</span>
          </label>
          <input
            v-model="form.title"
            type="text"
            required
            placeholder="e.g. Shopee SPayLater"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Provider</label>
          <input
            v-model="form.provider"
            type="text"
            placeholder="e.g. Shopee, Lazada"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>
      </div>

      <!-- Credit Limit -->
      <div>
        <label class="block text-xs font-mono text-zinc-400 mb-1.5">
          Approved Credit Limit <span class="text-rose-400">*</span>
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
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-7 pr-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>
      </div>

      <!-- Cutoff & Due Day -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Statement Cut-off Day of Month <span class="text-rose-400">*</span>
          </label>
          <input
            v-model.number="form.cutoff_day"
            type="number"
            min="1"
            max="31"
            required
            placeholder="25"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Payment Due Day of Month <span class="text-rose-400">*</span>
          </label>
          <input
            v-model.number="form.due_day"
            type="number"
            min="1"
            max="31"
            required
            placeholder="10"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>
      </div>

      <!-- Progressive Disclosure: Additional Details -->
      <div class="pt-1">
        <button
          type="button"
          @click="showAdvanced = !showAdvanced"
          class="text-xs font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <span>{{ showAdvanced ? '- Less Details' : '+ Account Details & Notes (Optional)' }}</span>
        </button>

        <div v-if="showAdvanced" class="mt-3 space-y-3 pt-3 border-t border-zinc-800/60">
          <div>
            <label class="block text-xs font-mono text-zinc-400 mb-1">Linked Phone / Account Ref</label>
            <input
              v-model="form.account_number"
              type="text"
              placeholder="e.g. 081-xxx-xxxx"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
            />
          </div>

          <div>
            <label class="block text-xs font-mono text-zinc-400 mb-1">Notes</label>
            <textarea
              v-model="form.notes"
              rows="2"
              placeholder="e.g. Primary shopping account"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors resize-none"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
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
          <span>{{ isActionLoading ? 'Saving...' : 'Create Credit Line' }}</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useBNPL } from '../../composables/finance/useBNPL'
import { useToastStore } from '../../stores/toast'
import { ArrowLeft, Check } from 'lucide-vue-next'

const router = useRouter()
const toast = useToastStore()
const { createAccount, isActionLoading } = useBNPL()

const showAdvanced = ref(false)

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

function applyPreset(preset: typeof providerPresets[0]) {
  form.title = preset.name
  form.provider = preset.provider
  form.cutoff_day = preset.cutoff
  form.due_day = preset.due
}

async function handleSubmit() {
  if (!form.title.trim() || !form.credit_limit) {
    toast.error('Please enter account title and credit limit')
    return
  }

  try {
    const created = await createAccount({
      title: form.title.trim(),
      provider: form.provider.trim() || form.title.trim(),
      credit_limit: Number(form.credit_limit),
      cutoff_day: Number(form.cutoff_day),
      due_day: Number(form.due_day),
      account_number: form.account_number.trim(),
      notes: form.notes.trim()
    })
    toast.success(`Created ${created.title} successfully!`)
    router.push(`/finance/bnpl/${created.id}`)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to create BNPL credit line')
  }
}
</script>
