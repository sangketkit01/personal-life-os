<template>
  <div class="min-h-screen bg-[#090a0f] text-zinc-100 flex font-sans antialiased selection:bg-zinc-800 selection:text-white">
    <!-- Desktop Sidebar (Fixed to viewport height, sticky top-0) -->
    <aside class="hidden md:flex w-64 border-r border-zinc-800/80 bg-zinc-950 flex-col justify-between shrink-0 sticky top-0 h-screen overflow-y-auto z-20">
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

        <!-- Navigation Links & Accordion Groups -->
        <nav class="p-3 space-y-1">
          <!-- 1. Executive Home Overview -->
          <RouterLink
            to="/"
            class="flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors group"
            :class="[
              $route.path === '/'
                ? 'bg-zinc-900 text-white border border-zinc-800 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40'
            ]"
          >
            <div class="flex items-center gap-2.5">
              <LayoutDashboard
                class="w-3.5 h-3.5 transition-colors shrink-0"
                :class="$route.path === '/' ? 'text-zinc-200' : 'text-zinc-500 group-hover:text-zinc-300'"
              />
              <span>Executive Overview</span>
            </div>
          </RouterLink>

          <!-- 2. Financial Radar Accordion Group -->
          <div class="pt-1.5">
            <!-- Group Header Button -->
            <button
              type="button"
              @click="toggleGroup('finance')"
              class="w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors group"
              :class="[
                $route.path.startsWith('/finance')
                  ? 'text-zinc-100 bg-zinc-900/60'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/30'
              ]"
            >
              <div class="flex items-center gap-2.5">
                <CreditCard
                  class="w-3.5 h-3.5 transition-colors shrink-0"
                  :class="$route.path.startsWith('/finance') ? 'text-zinc-100' : 'text-zinc-500 group-hover:text-zinc-300'"
                />
                <span class="font-semibold tracking-tight">Financial Radar</span>
              </div>
              <div class="flex items-center gap-1.5">
                <!-- Group Alert Badge if critical trial exists -->
                <span
                  v-if="criticalTrialsCount > 0"
                  class="w-1.5 h-1.5 rounded-full bg-rose-500/80 animate-pulse"
                  title="Expiring trials pending"
                />
                <ChevronDown
                  class="w-3.5 h-3.5 text-zinc-500 transition-transform duration-200"
                  :class="{ 'rotate-180': expandedGroups.finance }"
                />
              </div>
            </button>

            <!-- Collapsible Sub-menu -->
            <div v-show="expandedGroups.finance" class="pl-4 pr-1 py-1 space-y-0.5 border-l border-zinc-800/80 ml-4 my-1">
              <RouterLink
                v-for="sub in financeNavItems"
                :key="sub.path"
                :to="sub.path"
                class="flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors group"
                :class="[
                  isNavActive(sub.path)
                    ? 'bg-zinc-900 text-white border border-zinc-800/80 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40'
                ]"
              >
                <div class="flex items-center gap-2 truncate">
                  <component
                    :is="sub.icon"
                    class="w-3 h-3 transition-colors shrink-0"
                    :class="isNavActive(sub.path) ? 'text-zinc-200' : 'text-zinc-500 group-hover:text-zinc-300'"
                  />
                  <span class="truncate">{{ sub.label }}</span>
                </div>

                <!-- Sub-item Badge -->
                <span
                  v-if="sub.badge && sub.badge()"
                  class="text-[9px] font-mono px-1.5 py-0.2 rounded border uppercase font-semibold shrink-0"
                  :class="sub.badgeClass || 'bg-zinc-900 text-zinc-400 border-zinc-800'"
                >
                  {{ sub.badge() }}
                </span>
              </RouterLink>
            </div>
          </div>

          <!-- 3. Cash Flow & Ledger Accordion Group -->
          <div class="pt-1.5">
            <!-- Group Header Button -->
            <button
              type="button"
              @click="toggleGroup('ledger')"
              class="w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors group"
              :class="[
                $route.path.startsWith('/ledger')
                  ? 'text-zinc-100 bg-zinc-900/60'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/30'
              ]"
            >
              <div class="flex items-center gap-2.5">
                <Wallet
                  class="w-3.5 h-3.5 transition-colors shrink-0"
                  :class="$route.path.startsWith('/ledger') ? 'text-zinc-100' : 'text-zinc-500 group-hover:text-zinc-300'"
                />
                <span class="font-semibold tracking-tight">Cash Flow & Ledger</span>
              </div>
              <div class="flex items-center gap-1.5">
                <span
                  v-if="ledgerStore.pendingSplits.length > 0"
                  class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"
                  title="Pending split shares"
                />
                <ChevronDown
                  class="w-3.5 h-3.5 text-zinc-500 transition-transform duration-200"
                  :class="{ 'rotate-180': expandedGroups.ledger }"
                />
              </div>
            </button>

            <!-- Collapsible Sub-menu -->
            <div v-show="expandedGroups.ledger" class="pl-4 pr-1 py-1 space-y-0.5 border-l border-zinc-800/80 ml-4 my-1">
              <RouterLink
                v-for="sub in ledgerNavItems"
                :key="sub.path"
                :to="sub.path"
                class="flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors group"
                :class="[
                  isNavActive(sub.path)
                    ? 'bg-zinc-900 text-white border border-zinc-800/80 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40'
                ]"
              >
                <div class="flex items-center gap-2 truncate">
                  <component
                    :is="sub.icon"
                    class="w-3 h-3 transition-colors shrink-0"
                    :class="isNavActive(sub.path) ? 'text-zinc-200' : 'text-zinc-500 group-hover:text-zinc-300'"
                  />
                  <span class="truncate">{{ sub.label }}</span>
                </div>

                <span
                  v-if="sub.badge && sub.badge()"
                  class="text-[9px] font-mono px-1.5 py-0.2 rounded border uppercase font-semibold shrink-0"
                  :class="sub.badgeClass || 'bg-zinc-900 text-zinc-400 border-zinc-800'"
                >
                  {{ sub.badge() }}
                </span>
              </RouterLink>
            </div>
          </div>

          <!-- 4. Wealth & Portfolio Accordion Group -->
          <div class="pt-1.5">
            <!-- Group Header Button -->
            <button
              type="button"
              @click="toggleGroup('portfolio')"
              class="w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors group"
              :class="[
                $route.path.startsWith('/portfolio')
                  ? 'text-zinc-100 bg-zinc-900/60'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/30'
              ]"
            >
              <div class="flex items-center gap-2.5">
                <TrendingUp
                  class="w-3.5 h-3.5 transition-colors shrink-0"
                  :class="$route.path.startsWith('/portfolio') ? 'text-zinc-100' : 'text-zinc-500 group-hover:text-zinc-300'"
                />
                <span class="font-semibold tracking-tight">Wealth & Portfolio</span>
              </div>
              <ChevronDown
                class="w-3.5 h-3.5 text-zinc-500 transition-transform duration-200"
                :class="{ 'rotate-180': expandedGroups.portfolio }"
              />
            </button>

            <!-- Collapsible Sub-menu -->
            <div v-show="expandedGroups.portfolio" class="pl-4 pr-1 py-1 space-y-0.5 border-l border-zinc-800/80 ml-4 my-1">
              <RouterLink
                v-for="sub in portfolioNavItems"
                :key="sub.path"
                :to="sub.path"
                class="flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors group"
                :class="[
                  isNavActive(sub.path)
                    ? 'bg-zinc-900 text-white border border-zinc-800/80 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40'
                ]"
              >
                <div class="flex items-center gap-2 truncate">
                  <component
                    :is="sub.icon"
                    class="w-3 h-3 transition-colors shrink-0"
                    :class="isNavActive(sub.path) ? 'text-zinc-200' : 'text-zinc-500 group-hover:text-zinc-300'"
                  />
                  <span class="truncate">{{ sub.label }}</span>
                </div>

                <span
                  v-if="sub.badge && sub.badge()"
                  class="text-[9px] font-mono px-1.5 py-0.2 rounded border uppercase font-semibold shrink-0"
                  :class="sub.badgeClass || 'bg-zinc-900 text-zinc-400 border-zinc-800'"
                >
                  {{ sub.badge() }}
                </span>
              </RouterLink>
            </div>
          </div>

          <!-- 4. Workspace & Tasks (Standalone) -->
          <div class="pt-1.5">
            <RouterLink
              to="/workspace"
              class="flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors group"
              :class="[
                $route.path === '/workspace' || $route.path.startsWith('/workspace/')
                  ? 'bg-zinc-900 text-white border border-zinc-800 shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40'
              ]"
            >
              <div class="flex items-center gap-2.5">
                <FolderKanban
                  class="w-3.5 h-3.5 transition-colors shrink-0"
                  :class="$route.path === '/workspace' || $route.path.startsWith('/workspace/') ? 'text-zinc-200' : 'text-zinc-500 group-hover:text-zinc-300'"
                />
                <span>Workspace</span>
              </div>
            </RouterLink>
          </div>

          <!-- 5. Settings & Config (Standalone) -->
          <div>
            <RouterLink
              to="/settings"
              class="flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors group"
              :class="[
                $route.path === '/settings' || $route.path.startsWith('/settings/')
                  ? 'bg-zinc-900 text-white border border-zinc-800 shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40'
              ]"
            >
              <div class="flex items-center gap-2.5">
                <Settings
                  class="w-3.5 h-3.5 transition-colors shrink-0"
                  :class="$route.path === '/settings' || $route.path.startsWith('/settings/') ? 'text-zinc-200' : 'text-zinc-500 group-hover:text-zinc-300'"
                />
                <span>Settings</span>
              </div>
            </RouterLink>
          </div>
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
      <div class="w-64 bg-zinc-950 border-r border-zinc-800 flex flex-col justify-between h-full p-4 overflow-y-auto">
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

          <!-- Mobile Nav Links -->
          <nav class="space-y-1">
            <RouterLink
              to="/"
              @click="isMobileMenuOpen = false"
              class="flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium text-zinc-400 hover:text-zinc-200"
              :class="{ 'bg-zinc-900 text-white': $route.path === '/' }"
            >
              <LayoutDashboard class="w-3.5 h-3.5" />
              <span>Overview</span>
            </RouterLink>

            <!-- Finance Sub-list -->
            <div class="pt-2">
              <div class="text-[10px] font-mono uppercase text-zinc-500 px-3 py-1 font-semibold">Financial Radar</div>
              <RouterLink
                v-for="sub in financeNavItems"
                :key="sub.path"
                :to="sub.path"
                @click="isMobileMenuOpen = false"
                class="flex items-center gap-2.5 px-3 py-1.5 rounded-md text-xs text-zinc-400 hover:text-zinc-200 pl-5"
                :class="{ 'bg-zinc-900 text-white font-medium': isNavActive(sub.path) }"
              >
                <component :is="sub.icon" class="w-3 h-3" />
                <span>{{ sub.label }}</span>
              </RouterLink>
            </div>

            <!-- Ledger Sub-list -->
            <div class="pt-2">
              <div class="text-[10px] font-mono uppercase text-zinc-500 px-3 py-1 font-semibold">Cash Flow & Ledger</div>
              <RouterLink
                v-for="sub in ledgerNavItems"
                :key="sub.path"
                :to="sub.path"
                @click="isMobileMenuOpen = false"
                class="flex items-center gap-2.5 px-3 py-1.5 rounded-md text-xs text-zinc-400 hover:text-zinc-200 pl-5"
                :class="{ 'bg-zinc-900 text-white font-medium': isNavActive(sub.path) }"
              >
                <component :is="sub.icon" class="w-3 h-3" />
                <span>{{ sub.label }}</span>
              </RouterLink>
            </div>

            <!-- Portfolio Sub-list -->
            <div class="pt-2">
              <div class="text-[10px] font-mono uppercase text-zinc-500 px-3 py-1 font-semibold">Wealth & Portfolio</div>
              <RouterLink
                v-for="sub in portfolioNavItems"
                :key="sub.path"
                :to="sub.path"
                @click="isMobileMenuOpen = false"
                class="flex items-center gap-2.5 px-3 py-1.5 rounded-md text-xs text-zinc-400 hover:text-zinc-200 pl-5"
                :class="{ 'bg-zinc-900 text-white font-medium': isNavActive(sub.path) }"
              >
                <component :is="sub.icon" class="w-3 h-3" />
                <span>{{ sub.label }}</span>
              </RouterLink>
            </div>

            <div class="pt-2">
              <RouterLink
                to="/workspace"
                @click="isMobileMenuOpen = false"
                class="flex items-center gap-2.5 px-3 py-2 rounded-md text-xs transition-colors"
                :class="$route.path === '/workspace' || $route.path.startsWith('/workspace/') ? 'bg-zinc-900 text-white font-medium' : 'text-zinc-400 hover:text-zinc-200'"
              >
                <FolderKanban class="w-3.5 h-3.5" />
                <span>Workspace</span>
              </RouterLink>
              <RouterLink
                to="/settings"
                @click="isMobileMenuOpen = false"
                class="flex items-center gap-2.5 px-3 py-2 rounded-md text-xs transition-colors"
                :class="$route.path === '/settings' || $route.path.startsWith('/settings/') ? 'bg-zinc-900 text-white font-medium' : 'text-zinc-400 hover:text-zinc-200'"
              >
                <Settings class="w-3.5 h-3.5" />
                <span>Settings</span>
              </RouterLink>
            </div>
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
      <!-- Topbar Header with Breadcrumbs & Utilities -->
      <header class="h-14 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur px-4 md:px-6 flex items-center justify-between shrink-0">
        <div class="flex items-center gap-3 min-w-0">
          <!-- Mobile Hamburger Toggle -->
          <button
            @click="isMobileMenuOpen = true"
            class="md:hidden p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 bg-zinc-900 border border-zinc-800"
            title="Open Menu"
          >
            <Menu class="w-4 h-4" />
          </button>

          <!-- Dynamic Breadcrumbs -->
          <div class="hidden sm:flex items-center gap-2 text-xs font-mono text-zinc-500">
            <span class="text-zinc-400">{{ currentDomainLabel }}</span>
            <span v-if="currentSubdomainLabel" class="text-zinc-600">/</span>
            <span v-if="currentSubdomainLabel" class="text-zinc-200 font-medium font-sans">{{ currentSubdomainLabel }}</span>
          </div>

          <!-- Quick Search command pill -->
          <button
            @click="isCommandPaletteOpen = true"
            class="flex items-center gap-2 text-xs text-zinc-400 bg-zinc-900/60 border border-zinc-800/80 px-3 py-1.5 rounded-md w-44 sm:w-64 hover:border-zinc-700 transition cursor-pointer text-left ml-2"
          >
            <Search class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <span class="text-[11px] text-zinc-400 truncate">Search ({{ shortcutKey }})</span>
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
            <p class="text-xs text-zinc-400 mt-0.5">Receive advance reminders with settlement actions</p>
          </div>
        </div>

        <div v-if="authStore.user?.is_telegram_connected" class="p-3.5 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs space-y-1 font-mono">
          <div class="flex items-center gap-1.5 text-zinc-300 font-medium">
            <CheckCircle2 class="w-3.5 h-3.5 text-zinc-400" />
            <span>Telegram account connected</span>
          </div>
          <div class="text-[11px] text-zinc-500">
            Chat ID: {{ authStore.user.telegram_chat_id }}
          </div>
        </div>

        <div v-else class="space-y-4">
          <p class="text-xs text-zinc-300 leading-relaxed">
            Click below to open bot in Telegram and click <strong>[ START ]</strong> to link your session.
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useFinanceStore } from '../stores/finance'
import { useLedgerStore } from '../stores/ledger'
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
  Menu,
  ChevronDown,
  Gauge,
  Layers,
  ShoppingBag,
  Repeat,
  Scale,
  PieChart,
  Briefcase,
  Eye,
  ArrowLeftRight,
  Newspaper,
  Wallet,
  Receipt,
  Users
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const financeStore = useFinanceStore()
const ledgerStore = useLedgerStore()
const toast = useToastStore()

const showTelegramModal = ref(false)
const isGeneratingToken = ref(false)
const isMobileMenuOpen = ref(false)
const isCommandPaletteOpen = ref(false)

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPod|iPad/.test(navigator.platform || navigator.userAgent)
const shortcutKey = isMac ? '⌘K' : 'Ctrl+K'

// Accordion Expand/Collapse State
const expandedGroups = ref<Record<string, boolean>>({
  finance: true,
  ledger: true,
  portfolio: true
})

function toggleGroup(key: string) {
  expandedGroups.value[key] = !expandedGroups.value[key]
}

// Auto-expand group when route matches
watch(
  () => route.path,
  (path) => {
    if (path.startsWith('/finance')) {
      expandedGroups.value.finance = true
    }
    if (path.startsWith('/ledger')) {
      expandedGroups.value.ledger = true
    }
    if (path.startsWith('/portfolio')) {
      expandedGroups.value.portfolio = true
    }
  },
  { immediate: true }
)

function isNavActive(path: string): boolean {
  // Root / Overview routes must match exactly to prevent prefix collision with sibling subroutes
  if (path === '/ledger') {
    return route.path === '/ledger' || route.path === '/ledger/'
  }
  if (path === '/finance/overview') {
    return route.path === '/finance/overview' || route.path === '/finance' || route.path === '/finance/'
  }
  if (path === '/portfolio/overview') {
    return route.path === '/portfolio/overview' || route.path === '/portfolio' || route.path === '/portfolio/'
  }

  // All other sub-items: match exact route or nested child route (e.g. /ledger/accounts/123)
  return route.path === path || route.path.startsWith(path + '/')
}

const criticalTrialsCount = computed(() => {
  return financeStore.overview?.critical_trials_count || 0
})

const upcoming7DaysCount = computed(() => {
  return financeStore.overview?.upcoming_7_days_count || 0
})

interface NavSubItem {
  path: string
  label: string
  icon: any
  badge?: () => string | undefined
  badgeClass?: string
}

// Sub-navigation for Financial Radar
const financeNavItems: NavSubItem[] = [
  {
    path: '/finance/overview',
    label: 'Radar Overview',
    icon: Gauge,
    badge: () => upcoming7DaysCount.value > 0 ? `${upcoming7DaysCount.value} due` : undefined,
    badgeClass: 'bg-zinc-900 text-zinc-400 border-zinc-800'
  },
  {
    path: '/finance/installments',
    label: 'Installments & Contracts',
    icon: Layers,
    badge: () => {
      const count = financeStore.obligations.filter(o => o.type === 'INSTALLMENT' && o.subtype !== 'BNPL_ACCOUNT' && !o.parent).length
      return count > 0 ? `${count}` : undefined
    }
  },
  {
    path: '/finance/bnpl',
    label: 'Shopping Credit',
    icon: ShoppingBag,
    badge: () => {
      const count = financeStore.obligations.filter(o => o.subtype === 'BNPL_ACCOUNT').length
      return count > 0 ? `${count}` : undefined
    }
  },
  {
    path: '/finance/subscriptions',
    label: 'Subscriptions & Trials',
    icon: Repeat,
    badge: () => criticalTrialsCount.value > 0 ? 'ALERT' : undefined,
    badgeClass: 'bg-zinc-900 text-rose-400 border-zinc-800'
  },
  {
    path: '/finance/debts',
    label: 'Two-Way Debt Ledger',
    icon: Scale,
    badge: () => {
      const count = financeStore.obligations.filter(o => o.direction === 'INFLOW' && o.status === 'ACTIVE').length
      return count > 0 ? `${count} debtors` : undefined
    },
    badgeClass: 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
]

// Sub-navigation for Cash Flow & Ledger
const ledgerNavItems: NavSubItem[] = [
  {
    path: '/ledger',
    label: 'Cash Flow Radar',
    icon: LayoutDashboard,
  },
  {
    path: '/ledger/transactions',
    label: 'Transaction Ledger',
    icon: Receipt,
  },
  {
    path: '/ledger/accounts',
    label: 'Accounts & Wallets',
    icon: Wallet,
    badge: () => ledgerStore.accounts.length > 0 ? `${ledgerStore.accounts.length}` : undefined,
  },
  {
    path: '/ledger/splits',
    label: 'Shared Bill Splits',
    icon: Users,
    badge: () => ledgerStore.pendingSplits.length > 0 ? `${ledgerStore.pendingSplits.length} pending` : undefined,
    badgeClass: 'bg-zinc-900 text-amber-400 border-zinc-800'
  },
  {
    path: '/ledger/budgets',
    label: 'Category Budgets',
    icon: PieChart,
  }
]

// Sub-navigation for Wealth & Portfolio
const portfolioNavItems: NavSubItem[] = [
  {
    path: '/portfolio/overview',
    label: 'Portfolio Overview',
    icon: PieChart
  },
  {
    path: '/portfolio/accounts',
    label: 'My Portfolios',
    icon: Briefcase
  },
  {
    path: '/portfolio/watchlist',
    label: 'Watchlist',
    icon: Eye
  },
  {
    path: '/portfolio/executions',
    label: 'Executions',
    icon: ArrowLeftRight
  },
  {
    path: '/portfolio/news',
    label: 'Market News',
    icon: Newspaper
  }
]

// Dynamic Breadcrumbs
const currentDomainLabel = computed(() => {
  const p = route.path
  if (p.startsWith('/finance')) return 'Financial Radar'
  if (p.startsWith('/ledger')) return 'Cash Flow & Ledger'
  if (p.startsWith('/portfolio')) return 'Wealth & Portfolio'
  if (p.startsWith('/workspace')) return 'Workspace'
  if (p.startsWith('/settings')) return 'Settings'
  return 'Console'
})

const currentSubdomainLabel = computed(() => {
  const p = route.path
  if (p === '/finance/installments/new') return 'New Contract'
  if (p.startsWith('/finance/installments/')) return 'Contract Dossier'
  if (p === '/finance/bnpl/new') return 'New Credit Facility'
  if (p.includes('/new-order')) return 'New Purchase Order'
  if (p.startsWith('/finance/bnpl/')) return 'Account Dossier'
  if (p === '/finance/debts/new') return 'New Debt Entry'
  if (p.startsWith('/finance/debts/')) return 'Debt Dossier'
  if (p === '/finance/subscriptions/new') return 'New Subscription'
  if (p.startsWith('/finance/subscriptions/')) return 'Subscription Dossier'
  if (p === '/ledger/accounts/new') return 'New Account'
  if (p.startsWith('/ledger/accounts/')) return 'Account Statement'
  if (p === '/portfolio/accounts/new') return 'New Brokerage Basket'
  if (p.startsWith('/portfolio/accounts/')) return 'Account Dossier'
  if (p === '/portfolio/executions/import') return 'Import CSV Statement'
  if (p === '/portfolio/executions/dividends') return 'Dividend Ledger'
  if (p.startsWith('/portfolio/news/')) return 'News Briefing'
  const fMatch = financeNavItems.find(i => i.path === p)
  if (fMatch) return fMatch.label
  const lMatch = ledgerNavItems.find(i => i.path === p)
  if (lMatch) return lMatch.label
  const pMatch = portfolioNavItems.find(i => i.path === p)
  if (pMatch) return pMatch.label
  if (p.includes('/asset/')) return `Asset: ${route.params.ticker || ''}`
  return ''
})

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

const handleKeyDown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    isCommandPaletteOpen.value = !isCommandPaletteOpen.value
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
  // Prefetch finance overview for badges
  financeStore.fetchOverview().catch(() => {})
  financeStore.fetchObligations().catch(() => {})
  // Prefetch ledger accounts & pending splits for badges
  ledgerStore.fetchAccounts().catch(() => {})
  ledgerStore.fetchPendingSplits().catch(() => {})
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>