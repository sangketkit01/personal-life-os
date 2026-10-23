<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl relative">
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="mb-4">
        <h3 class="text-base font-semibold text-zinc-100 tracking-tight">Create Workspace Project</h3>
        <p class="text-xs text-zinc-500 mt-0.5">Organize documents and deadlines by initiative or client</p>
      </div>

      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-3.5">
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Project Name</label>
          <input
            v-model="name"
            type="text"
            required
            placeholder="e.g. Client Alpha, Tax 2026"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Color Indicator</label>
          <div class="flex items-center gap-2">
            <button
              v-for="c in presetColors"
              :key="c"
              type="button"
              @click="selectedColor = c"
              class="w-5 h-5 rounded-full border transition-all"
              :class="selectedColor === c ? 'border-white scale-110' : 'border-transparent hover:scale-105 opacity-80'"
              :style="{ backgroundColor: c }"
            />
          </div>
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Description (Optional)</label>
          <input
            v-model="description"
            type="text"
            placeholder="Brief scope of work"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {{ isSubmitting ? 'Creating...' : 'Create Project' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useWorkspaceStore } from '../../stores/workspace'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created'): void
}>()

const workspaceStore = useWorkspaceStore()

const name = ref('')
const description = ref('')
const selectedColor = ref('#71717a')
const isSubmitting = ref(false)
const errorMessage = ref('')

const presetColors = [
  '#71717a',
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
]

async function handleSubmit() {
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    await workspaceStore.createProject({
      name: name.value,
      description: description.value,
      color: selectedColor.value
    })
    emit('created')
    emit('close')
    name.value = ''
    description.value = ''
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || 'Failed to create project'
  } finally {
    isSubmitting.value = false
  }
}
</script>
