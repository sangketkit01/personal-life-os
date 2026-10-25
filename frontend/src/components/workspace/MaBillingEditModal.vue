<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-[65] flex items-center justify-center p-4 font-sans">
      <div class="absolute inset-0 bg-black/75 backdrop-blur-sm" @click="emit('close')" />

      <form
        @submit.prevent="save"
        class="relative w-full max-w-2xl max-h-[88vh] flex flex-col rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden"
      >
        <div class="flex items-center justify-between px-5 py-3.5 border-b border-zinc-800 shrink-0">
          <div class="flex items-center gap-2">
            <FileSignature class="w-4 h-4 text-sky-400" />
            <h3 class="text-sm font-semibold text-zinc-100">{{ t('ma.edit.title') }}</h3>
          </div>
          <button type="button" @click="emit('close')" class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-100 transition-colors">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-5">
          <!-- Contract identity -->
          <section class="space-y-3">
            <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800/70 pb-1.5">{{ t('ma.edit.contract') }}</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="block sm:col-span-2">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.projectType') }}</span>
                <select v-model="form.project_type"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                  <option v-for="pt in PROJECT_TYPES" :key="pt" :value="pt">{{ t(`ma.types.${pt}`) }}</option>
                </select>
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.clientName') }}</span>
                <input v-model="form.client_name" type="text" maxlength="150"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.clientContact') }}</span>
                <input v-model="form.client_contact" type="text" maxlength="255" placeholder="LINE / email / phone"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.startDate') }}</span>
                <input v-model="form.ma_start_date" type="date"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.endDate') }}</span>
                <input v-model="form.ma_end_date" type="date"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
            </div>
          </section>

          <!-- Billing cycle -->
          <section class="space-y-3">
            <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800/70 pb-1.5">{{ t('ma.edit.billing') }}</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.amount') }}</span>
                <input v-model="form.ma_amount" type="number" step="0.01" min="0"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.currency') }}</span>
                <select v-model="form.ma_currency"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                  <option>THB</option>
                  <option>USD</option>
                </select>
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.cycle') }}</span>
                <select v-model="form.ma_billing_cycle"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                  <option>MONTHLY</option>
                  <option>QUARTERLY</option>
                  <option>YEARLY</option>
                  <option>ONE_TIME</option>
                </select>
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.nextBilling') }}</span>
                <input v-model="form.ma_next_billing_date" type="date"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
            </div>
            <p class="text-[10px] text-zinc-500 font-mono flex items-start gap-1.5">
              <Info class="w-3 h-3 mt-0.5 shrink-0 text-sky-400/80" />
              {{ t('ma.edit.syncHint') }}
            </p>
          </section>

          <!-- SLA -->
          <section class="space-y-3">
            <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800/70 pb-1.5">{{ t('ma.edit.sla') }}</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.uptime') }}</span>
                <input v-model="sla.uptime_target" type="text" placeholder="99.9%"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.responseTime') }}</span>
                <input v-model="sla.response_time" type="text" placeholder="< 2h"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.backup') }}</span>
                <input v-model="sla.backup_policy" type="text" placeholder="daily snapshot, 7d retention"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('ma.edit.quota') }}</span>
                <input v-model="sla.monthly_hours_quota" type="text" placeholder="5 h / month"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
            </div>
          </section>
        </div>

        <div class="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-zinc-800 shrink-0">
          <button type="button" @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 text-xs transition-colors">
            {{ t('common.cancel') }}
          </button>
          <button type="submit" :disabled="isSaving"
            class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50">
            <Save class="w-3.5 h-3.5" />
            {{ t('common.save') }}
          </button>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { FileSignature, X, Save, Info } from 'lucide-vue-next'
import { t } from '../../i18n'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import type { WorkspaceProject, ProjectType } from '../../types/workspace'

const props = defineProps<{
  isOpen: boolean
  project: WorkspaceProject
}>()

const emit = defineEmits<{ (e: 'close'): void; (e: 'saved'): void }>()

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const PROJECT_TYPES: ProjectType[] = ['INTERNAL', 'CLIENT_DEV', 'MA_CONTRACT']

const isSaving = ref(false)
const sla = reactive({
  uptime_target: '',
  response_time: '',
  backup_policy: '',
  monthly_hours_quota: ''
})

const emptyForm = () => ({
  project_type: 'INTERNAL' as ProjectType,
  client_name: '',
  client_contact: '',
  ma_start_date: '',
  ma_end_date: '',
  ma_billing_cycle: 'MONTHLY',
  ma_amount: '' as string | number,
  ma_currency: 'THB',
  ma_next_billing_date: ''
})
const form = ref(emptyForm())

watch(() => props.isOpen, (open) => {
  if (!open) return
  const p = props.project
  form.value = {
    project_type: p.project_type || 'INTERNAL',
    client_name: p.client_name || '',
    client_contact: p.client_contact || '',
    ma_start_date: p.ma_start_date || '',
    ma_end_date: p.ma_end_date || '',
    ma_billing_cycle: p.ma_billing_cycle || 'MONTHLY',
    ma_amount: p.ma_amount || '',
    ma_currency: p.ma_currency || 'THB',
    ma_next_billing_date: p.ma_next_billing_date || ''
  }
  const s = p.sla_details || {}
  sla.uptime_target = s.uptime_target || ''
  sla.response_time = s.response_time || ''
  sla.backup_policy = s.backup_policy || ''
  sla.monthly_hours_quota = s.monthly_hours_quota || ''
})

async function save() {
  isSaving.value = true
  try {
    await workspaceStore.updateProject(props.project.id, {
      project_type: form.value.project_type,
      client_name: form.value.client_name,
      client_contact: form.value.client_contact,
      ma_start_date: form.value.ma_start_date || null,
      ma_end_date: form.value.ma_end_date || null,
      ma_billing_cycle: form.value.ma_billing_cycle,
      ma_amount: form.value.ma_amount === '' ? '0' : String(form.value.ma_amount),
      ma_currency: form.value.ma_currency,
      ma_next_billing_date: form.value.ma_next_billing_date || null,
      sla_details: { ...sla }
    })
    toast.success(t('ma.edit.saved'))
    emit('saved')
    emit('close')
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('ma.edit.saveFailed'))
  } finally {
    isSaving.value = false
  }
}
</script>
