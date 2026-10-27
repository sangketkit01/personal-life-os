<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-[65] flex items-center justify-center p-2 sm:p-4 overflow-hidden font-sans">
      <div class="absolute inset-0 bg-black/75 backdrop-blur-sm" @click="emit('close')" />

      <form
        @submit.prevent="save"
        class="relative w-full max-w-lg max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden"
      >
        <div class="flex items-center justify-between px-5 py-3.5 border-b border-zinc-800 shrink-0">
          <div class="flex items-center gap-2">
            <KeyRound class="w-4 h-4 text-amber-400" />
            <h3 class="text-sm font-semibold text-zinc-100">
              {{ editing ? t('cred.form.editTitle') : t('cred.form.createTitle') }}
            </h3>
          </div>
          <button type="button" @click="emit('close')" class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-100 transition-colors cursor-pointer">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4 sm:p-5 space-y-3">
          <label class="block">
            <span class="text-[11px] text-zinc-400 font-mono">{{ t('cred.form.title') }} *</span>
            <input v-model="form.title" type="text" required maxlength="150"
              class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
          </label>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label class="block">
              <span class="text-[11px] text-zinc-400 font-mono">{{ t('cred.form.category') }}</span>
              <select v-model="form.category"
                class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                <option v-for="c in CATEGORIES" :key="c" :value="c">{{ t(`cred.categories.${c}`) }}</option>
              </select>
            </label>
            <label class="block">
              <span class="text-[11px] text-zinc-400 font-mono">{{ t('cred.form.asset') }}</span>
              <select v-model="form.asset"
                class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                <option value="">{{ t('cred.form.noAsset') }}</option>
                <option v-for="a in assets" :key="a.id" :value="a.id">{{ a.name }}</option>
              </select>
            </label>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label class="block">
              <span class="text-[11px] text-zinc-400 font-mono">{{ t('cred.form.username') }}</span>
              <input v-model="form.username" type="text"
                class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
            </label>
            <label class="block">
              <span class="text-[11px] text-zinc-400 font-mono">{{ t('cred.form.host') }}</span>
              <input v-model="form.host_or_url" type="text" placeholder="postgres://host:5432/db"
                class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
            </label>
          </div>

          <label class="block">
            <span class="text-[11px] text-zinc-400 font-mono">
              {{ t('cred.form.secret') }}<span v-if="!editing"> *</span>
              <span v-if="editing && credential?.has_secret" class="text-emerald-500/80">· {{ t('cred.form.stored') }}</span>
            </span>
            <textarea v-model="secret" rows="3" :required="!editing"
              :placeholder="editing ? t('cred.form.keepPlaceholder') : '••••••••••'"
              class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
          </label>

          <label class="block">
            <span class="text-[11px] text-zinc-400 font-mono">{{ t('cred.form.notes') }}</span>
            <textarea v-model="form.notes" rows="2"
              class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
          </label>
        </div>

        <div class="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-zinc-800 shrink-0 bg-zinc-950/90">
          <button type="button" @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 text-xs transition-colors cursor-pointer">
            {{ t('common.cancel') }}
          </button>
          <button type="submit" :disabled="isSaving"
            class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer">
            <Save class="w-3.5 h-3.5" />
            {{ t('common.save') }}
          </button>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { KeyRound, X, Save } from 'lucide-vue-next'
import { t } from '../../i18n'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import type { ServerCredential, CredentialCategory, InfrastructureAsset } from '../../types/workspace'

const props = defineProps<{
  isOpen: boolean
  projectId: string
  credential: ServerCredential | null
  assets: InfrastructureAsset[]
}>()

const emit = defineEmits<{ (e: 'close'): void; (e: 'saved'): void }>()

useBodyScrollLock(() => props.isOpen)

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const CATEGORIES: CredentialCategory[] = ['SSH', 'DATABASE', 'API_KEY', 'ENV_VARS', 'ADMIN_PANEL', 'OTHER']

const editing = computed(() => !!props.credential)
const isSaving = ref(false)
const secret = ref('')

const emptyForm = () => ({
  title: '',
  category: 'OTHER' as CredentialCategory,
  asset: '',
  username: '',
  host_or_url: '',
  notes: ''
})
const form = ref(emptyForm())

watch(() => props.isOpen, (open) => {
  if (!open) return
  secret.value = ''
  if (props.credential) {
    form.value = {
      title: props.credential.title,
      category: props.credential.category,
      asset: props.credential.asset || '',
      username: props.credential.username,
      host_or_url: props.credential.host_or_url,
      notes: props.credential.notes
    }
  } else {
    form.value = emptyForm()
  }
})

async function save() {
  if (!form.value.title.trim() || (!editing.value && !secret.value.trim())) return
  isSaving.value = true
  try {
    const payload: Record<string, any> = {
      project: props.projectId,
      ...form.value,
      asset: form.value.asset || null
    }
    if (secret.value.trim()) payload.secret = secret.value

    if (props.credential) {
      await workspaceStore.updateServerCredential(props.credential.id, payload)
      toast.success(t('cred.toast.updated'))
    } else {
      await workspaceStore.createServerCredential(payload)
      toast.success(t('cred.toast.created'))
    }
    emit('saved')
    emit('close')
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('cred.toast.saveFailed'))
  } finally {
    isSaving.value = false
  }
}
</script>
