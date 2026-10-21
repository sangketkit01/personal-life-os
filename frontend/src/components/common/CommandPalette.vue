<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-start justify-center pt-[15vh] p-4 font-sans"
    @click.self="close"
  >
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col">
      <!-- Search Input Header -->
      <div class="p-3 border-b border-zinc-800/80 flex items-center gap-2.5 bg-zinc-900/50">
        <Search class="w-4 h-4 text-zinc-400 shrink-0" />
        <input
          ref="inputRef"
          v-model="query"
          type="text"
          placeholder="Type a command, asset ticker, bill, or task..."
          class="w-full bg-transparent text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none"
          @keydown.down.prevent="navigateResults(1)"
          @keydown.up.prevent="navigateResults(-1)"
          @keydown.enter.prevent="selectActiveResult"
          @keydown.esc.prevent="close"
        />
        <kbd class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700/60 text-zinc-400 shrink-0">
          ESC
        </kbd>
      </div>

      <!-- Results List -->
      <div class="max-h-80 overflow-y-auto p-2 divide-y divide-zinc-900 text-xs">
        <!-- Empty State -->
        <div v-if="filteredResults.length === 0" class="py-8 text-center text-zinc-500 font-mono text-xs">
          No matching commands, assets, or tasks found.
        </div>

        <!-- Categorized Results -->
        <div v-else class="space-y-0.5">
          <div
            v-for="(item, idx) in filteredResults"
            :key="item.id"
            @click="handleSelect(item)"
            @mouseenter="activeIndex = idx"
            class="px-3 py-2 rounded-md flex items-center justify-between cursor-pointer transition-colors"
            :class="[
              activeIndex === idx
                ? 'bg-zinc-800/80 text-zinc-100'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
            ]"
          >
            <div class="flex items-center gap-2.5 truncate">
              <component :is="item.icon" class="w-3.5 h-3.5 shrink-0 text-zinc-400" />
              <div class="truncate">
                <span class="font-medium text-zinc-200">{{ item.title }}</span>
                <span v-if="item.subtitle" class="text-[10px] text-zinc-500 ml-2 font-mono">{{ item.subtitle }}</span>
              </div>
            </div>

            <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-500 uppercase shrink-0">
              {{ item.category }}
            </span>
          </div>
        </div>
      </div>

      <!-- Footer Info -->
      <div class="px-3 py-2 border-t border-zinc-800/80 bg-zinc-950 flex items-center justify-between text-[10px] font-mono text-zinc-500">
        <div class="flex items-center gap-3">
          <span>↑↓ to navigate</span>
          <span>↵ to select</span>
        </div>
        <span>{{ shortcutLabel }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useFinanceStore } from '../../stores/finance'
import { usePortfolioStore } from '../../stores/portfolio'
import { useWorkspaceStore } from '../../stores/workspace'
import {
  Search,
  LayoutDashboard,
  CreditCard,
  TrendingUp,
  FolderKanban,
  Settings,
  FileText,
  CalendarClock
} from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const router = useRouter()
const financeStore = useFinanceStore()
const portfolioStore = usePortfolioStore()
const workspaceStore = useWorkspaceStore()

const query = ref('')
const activeIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPod|iPad/.test(navigator.platform || navigator.userAgent)
const shortcutLabel = isMac ? '⌘K' : 'Ctrl+K'

interface CommandItem {
  id: string
  title: string
  subtitle?: string
  category: 'Navigation' | 'Finance' | 'Portfolio' | 'Workspace'
  icon: any
  action: () => void
}

const defaultCommands: CommandItem[] = [
  { id: 'nav-overview', title: 'System Overview', category: 'Navigation', icon: LayoutDashboard, action: () => router.push('/') },
  { id: 'nav-finance', title: 'Financial Radar', subtitle: 'Obligations & Trials', category: 'Navigation', icon: CreditCard, action: () => router.push('/finance') },
  { id: 'nav-portfolio', title: 'Portfolio Snapshot', subtitle: 'SET, US & Crypto', category: 'Navigation', icon: TrendingUp, action: () => router.push('/portfolio') },
  { id: 'nav-workspace', title: 'Workspace Pipeline', subtitle: 'Kanban & Notes', category: 'Navigation', icon: FolderKanban, action: () => router.push('/workspace') },
  { id: 'nav-settings', title: 'Settings & Security', subtitle: 'Sessions & Webhooks', category: 'Navigation', icon: Settings, action: () => router.push('/settings') },
]

const filteredResults = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) {
    return defaultCommands
  }

  const results: CommandItem[] = []

  // 1. Navigation matching
  for (const item of defaultCommands) {
    if (item.title.toLowerCase().includes(q) || item.subtitle?.toLowerCase().includes(q)) {
      results.push(item)
    }
  }

  // 2. Financial Obligations
  for (const ob of financeStore.obligations) {
    if (ob.title.toLowerCase().includes(q) || ob.type.toLowerCase().includes(q)) {
      results.push({
        id: `ob-${ob.id}`,
        title: ob.title,
        subtitle: `฿${Number(ob.amount).toLocaleString('th-TH')} • ${ob.type}`,
        category: 'Finance',
        icon: CalendarClock,
        action: () => router.push('/finance')
      })
    }
  }

  // 3. Portfolio Holdings
  for (const h of portfolioStore.holdings) {
    if (h.ticker.toLowerCase().includes(q) || h.name.toLowerCase().includes(q)) {
      results.push({
        id: `holding-${h.id}`,
        title: h.ticker,
        subtitle: `${h.name} • ฿${Number(h.position.market_value).toLocaleString('th-TH')}`,
        category: 'Portfolio',
        icon: TrendingUp,
        action: () => router.push('/portfolio')
      })
    }
  }

  // 4. Workspace Tasks & Notes
  for (const t of workspaceStore.tasks) {
    if (t.title.toLowerCase().includes(q) || t.doc_number?.toLowerCase().includes(q)) {
      results.push({
        id: `task-${t.id}`,
        title: t.title,
        subtitle: `Task • ${t.status}`,
        category: 'Workspace',
        icon: FileText,
        action: () => router.push('/workspace')
      })
    }
  }

  return results.slice(0, 15)
})

watch(() => props.isOpen, (open) => {
  if (open) {
    query.value = ''
    activeIndex.value = 0
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})

const navigateResults = (step: number) => {
  const count = filteredResults.value.length
  if (count === 0) return
  activeIndex.value = (activeIndex.value + step + count) % count
}

const selectActiveResult = () => {
  const selected = filteredResults.value[activeIndex.value]
  if (selected) {
    handleSelect(selected)
  }
}

const handleSelect = (item: CommandItem) => {
  item.action()
  close()
}

const close = () => {
  emit('close')
}

// Global Keyboard Shortcut listener
const handleGlobalKeydown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    if (props.isOpen) {
      close()
    } else {
      // Toggle handled via layout
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>
