<template>
  <div class="min-h-screen bg-[#090a0f] text-zinc-100 flex font-sans antialiased selection:bg-zinc-800 selection:text-white">
    <!-- Desktop Sidebar (Fixed to viewport height, sticky top-0) -->
    <aside class="hidden md:flex w-60 border-r border-zinc-800/80 bg-zinc-950 flex-col justify-between shrink-0 sticky top-0 h-screen overflow-y-auto z-20">
      <div>
        <!-- Brand -->
        <div class="h-14 px-5 flex items-center gap-2.5 border-b border-zinc-800/80">
          <div class="w-6 h-6 rounded bg-zinc-900 border border-zinc-700/80 flex items-center justify-center text-zinc-200">
            <Command class="w-3.5 h-3.5" />
          </div>
          <div class="flex items-center gap-2">
            <span class="font-semibold text-xs tracking-wider uppercase text-zinc-100">Life OS</span>
            <span class="text-[9px] font-mono px-1 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
              CONSOLE
            </span>
          </div>
        </div>

        <!-- Navigation Links -->
        <nav class="p-3 space-y-0.5">
          <RouterLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors group"
            :class="[
              $route.path === item.path
                ? 'bg-zinc-900 text-white border border-zinc-800 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40'
            ]"
          >
            <component
              :is="item.icon"
              class="w-3.5 h-3.5 transition-colors shrink-0"
              :class="$route.path === item.path ? 'text-zinc-200' : 'text-zinc-500 group-hover:text-zinc-300'"
            />
            <span class="truncate">{{ item.label }}</span>
          </RouterLink>
        </nav>
      </div>

      <!-- User footer -->
      <div class="p-3 border-t border-zinc-800/80 bg-zinc-950">
        <div class="flex items-center justify-between p-2 rounded-md bg-zinc-900/60 border border-zinc-800/60">
          <div class="flex items-center gap-2 truncate">
            <div class="w-6 h-6 rounded bg-zinc-800 border border-zinc-700/70 flex items-center justify-center text-[10px] font-mono font-medium text-zinc-300">
              {{ authStore.user?.username?.charAt(0).toUpperCase() || 'U' }}
            </div>
            <div class="truncate text-left">
              <div class="text-xs font-medium text-zinc-200 truncate">{{ authStore.user?.username }}</div>
              <div class="text-[10px] text-zinc-500 font-mono truncate">{{ authStore.user?.email }}</div>
            </div>
          </div>
          <button
            @click="handleLogout"
            title="Sign Out"
            class="text-zinc-500 hover:text-rose-400 p-1 rounded transition-colors"
          >
            <LogOut class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>

    <!-- Mobile Slide-over Drawer -->
    <div
      v-if="isMobileMenuOpen"
      class="fixed inset-0 z-50 md:hidden bg-black/75 backdrop-blur-sm flex"
      @click.self="isMobileMenuOpen = false"
    >
      <div class="w-64 bg-zinc-950 border-r border-zinc-800 flex flex-col justify-between h-full p-4">
        <div>
          <div class="flex items-center justify-between pb-4 border-b border-zinc-800 mb-4">
            <div class="flex items-center gap-2">
              <Command class="w-4 h-4 text-zinc-200" />
              <span class="font-semibold text-xs tracking-wider uppercase text-zinc-100">Life OS</span>
            </div>
            <button @click="isMobileMenuOpen = false" class="text-zinc-500 hover:text-zinc-300">
              <X class="w-4 h-4" />
            </button>
          </div>

          <nav class="space-y-1">
            <RouterLink
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              @click="isMobileMenuOpen = false"
              class="flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors"
              :class="[
                $route.path === item.path
                  ? 'bg-zinc-900 text-white border border-zinc-800'
                  : 'text-zinc-400 hover:text-zinc-200'
              ]"
            >
              <component :is="item.icon" class="w-4 h-4" />
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>
        </div>

        <div class="pt-4 border-t border-zinc-800 flex items-center justify-between">
          <span class="text-xs text-zinc-300 font-mono">{{ authStore.user?.username }}</span>
          <button @click="handleLogout" class="text-xs text-rose-400 hover:underline">
            Sign Out
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Topbar Header -->
      <header class="h-14 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur px-4 md:px-6 flex items-center justify-between shrink-0">
        <div class="flex items-center gap-3">
          <!-- Mobile Hamburger Toggle -->
          <button
            @click="isMobileMenuOpen = true"
            class="md:hidden p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 bg-zinc-900 border border-zinc-800"
            title="Open Menu"
          >
            <Menu class="w-4 h-4" />
          </button>

          <!-- Quick Search command pill (Interactive) -->
          <button
            @click="isCommandPaletteOpen = true"
            class="flex items-center gap-2 text-xs text-zinc-400 bg-zinc-900/60 border border-zinc-800/80 px-3 py-1.5 rounded-md w-48 sm:w-72 hover:border-zinc-700 transition cursor-pointer text-left"
          >
            <Search class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <span class="text-[11px] text-zinc-400 truncate">Search commands, assets...</span>
            <kbd class="ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700/60 text-zinc-400 shrink-0">
              {{ shortcutKey }}
            </kbd>
          </button>
        </div>

        <!-- Right Utilities -->
        <div class="flex items-center gap-3">
          <!-- Telegram Bot Connection Status -->
          <button
            @click="showTelegramModal = true"
            class="flex items-center gap-2 px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors border"
            :class="[
              authStore.user?.is_telegram_connected
                ? 'bg-zinc-900 text-zinc-300 border-zinc-800 hover:border-zinc-700'
                : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'
            ]"
          >
            <span
              class="w-1.5 h-1.5 rounded-full"
              :class="authStore.user?.is_telegram_connected ? 'bg-emerald-400' : 'bg-zinc-500'"
            />
            <span class="font-mono text-[11px]">
              {{ authStore.user?.is_telegram_connected ? 'BOT LINKED' : 'LINK BOT' }}
            </span>
          </button>

          <RouterLink
            to="/settings"
            class="p-1.5 text-zinc-400 hover:text-white rounded-md hover:bg-zinc-900 border border-transparent hover:border-zinc-800 transition-colors"
            title="Settings"
          >
            <Settings class="w-3.5 h-3.5" />
          </RouterLink>
        </div>
      </header>

      <!-- View Slot Container -->
      <main class="flex-1 p-4 md:p-8 overflow-y-auto">
        <RouterView />
      </main>
    </div>

    <!-- Telegram Link Modal -->
    <div
      v-if="showTelegramModal"
      class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-sans"
    >
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl relative">
        <button
          @click="showTelegramModal = false"
          class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <X class="w-4 h-4" />
        </button>

        <div class="flex items-center gap-3 mb-4">
          <div class="w-9 h-9 rounded-lg bg-zinc-900 text-zinc-200 flex items-center justify-center border border-zinc-800">
            <Bot class="w-4 h-4" />
          </div>
          <div>
            <h3 class="font-medium text-white text-sm">Telegram Butler Connection</h3>
            <p class="text-xs text-zinc-400 mt-0.5">Receive 10:00 AM advance reminders with settlement actions</p>
          </div>
        </div>

        <div v-if="authStore.user?.is_telegram_connected" class="p-3.5 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs space-y-1 font-mono">
          <div class="flex items-center gap-1.5 text-emerald-400 font-medium">
            <CheckCircle2 class="w-3.5 h-3.5" />
            <span>Telegram account connected</span>
          </div>
          <div class="text-[11px] text-zinc-500">
            Chat ID: {{ authStore.user.telegram_chat_id }}
          </div>
        </div>

        <div v-else class="space-y-4">
          <p class="text-xs text-zinc-300 leading-relaxed">
            Click below to open bot <span class="font-mono text-zinc-100">@brandy_personal_os_bot</span> in Telegram and click <strong>[ START ]</strong> to link your session.
          </p>
          <button
            @click="handleConnectTelegram"
            :disabled="isGeneratingToken"
            class="w-full py-2.5 px-4 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 font-semibold text-xs transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Send class="w-3.5 h-3.5" />
            <span>{{ isGeneratingToken ? 'Generating Link...' : 'Open Telegram & Authorize' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Command Palette (Ctrl+K / ⌘K) -->
    <CommandPalette
      :is-open="isCommandPaletteOpen"
      @close="isCommandPaletteOpen = false"
    />

    <!-- Global Toast Container -->
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'
import CommandPalette from '../components/common/CommandPalette.vue'
import ToastContainer from '../components/common/ToastContainer.vue'
import {
  Command,
  LayoutDashboard,
  CreditCard,
  TrendingUp,
  FolderKanban,
  Settings,
  Search,
  LogOut,
  Bot,
  CheckCircle2,
  Send,
  X,
  Menu
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToastStore()

const showTelegramModal = ref(false)
const isGeneratingToken = ref(false)
const isMobileMenuOpen = ref(false)
const isCommandPaletteOpen = ref(false)

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPod|iPad/.test(navigator.platform || navigator.userAgent)
const shortcutKey = isMac ? '⌘K' : 'Ctrl+K'

interface NavItem {
  path: string
  label: string
  icon: any
}

const navItems: NavItem[] = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/finance', label: 'Financial Radar', icon: CreditCard },
  { path: '/portfolio', label: 'Portfolio', icon: TrendingUp },
  { path: '/workspace', label: 'Workspace', icon: FolderKanban },
  { path: '/settings', label: 'Settings', icon: Settings },
]

async function handleLogout() {
  await authStore.logout()
  toast.info('Signed out successfully')
  router.push('/login')
}

async function handleConnectTelegram() {
  isGeneratingToken.value = true
  try {
    const data = await authStore.generateTelegramConnect()
    window.open(data.deep_link, '_blank')
  } finally {
    isGeneratingToken.value = false
  }
}

// Global hotkey listener for opening Command Palette
const handleKeyDown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    isCommandPaletteOpen.value = !isCommandPaletteOpen.value
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>
