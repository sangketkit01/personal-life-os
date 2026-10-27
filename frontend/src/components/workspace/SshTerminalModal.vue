<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[70] flex items-center justify-center p-2 sm:p-4 font-sans"
      :class="isMaximized ? 'p-0' : ''"
    >
      <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" @click="requestClose" />

      <div
        class="relative flex flex-col rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden shadow-2xl"
        :class="isMaximized ? 'w-full h-full rounded-none' : 'w-full max-w-5xl h-[calc(100dvh-1rem)] sm:h-[76vh]'"
      >
        <!-- Header -->
        <div class="px-3 sm:px-4 py-2 border-b border-zinc-800 bg-zinc-900/80 flex items-center justify-between gap-2 shrink-0">
          <div class="flex items-center gap-2 min-w-0 flex-1">
            <TerminalSquare class="w-4 h-4 text-emerald-400 shrink-0" />
            <span class="text-xs font-mono text-zinc-200 truncate min-w-0">
              {{ asset.ssh_username }}@{{ asset.ip_address || asset.hostname }}:{{ asset.ssh_port }}
            </span>
            <span
              class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border shrink-0"
              :class="statusClass"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="statusDotClass" />
              {{ statusLabel }}
            </span>
          </div>

          <div class="flex items-center gap-1 shrink-0">
            <button
              type="button"
              @click="reconnect"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors cursor-pointer"
              :title="t('term.reconnect')"
            >
              <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': wsStatus === 'connecting' }" />
            </button>
            <button
              type="button"
              @click="clearScreen"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors cursor-pointer"
              :title="t('term.clear')"
            >
              <Eraser class="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              @click="toggleRunbookBar"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors flex items-center cursor-pointer"
              :class="{ 'text-sky-400 border-sky-700/60': showRunbookBar }"
              :title="t('term.runbookBar')"
            >
              <ScrollText class="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              @click="isMaximized = !isMaximized"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors cursor-pointer"
              :title="t('term.maximize')"
            >
              <component :is="isMaximized ? Minimize2 : Maximize2" class="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              @click="requestClose"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors cursor-pointer"
              :title="t('term.close')"
            >
              <X class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Host Key verification banner -->
        <div
          v-if="hostKeyInfo.isHostKeyError"
          class="px-4 py-2.5 border-b text-left flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shrink-0"
          :class="hostKeyInfo.isMismatch ? 'bg-rose-950/90 border-rose-800' : 'bg-amber-950/90 border-amber-800'"
        >
          <div class="flex items-start gap-2.5 min-w-0">
            <AlertTriangle v-if="hostKeyInfo.isMismatch" class="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <ShieldAlert v-else class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div class="min-w-0">
              <p class="text-xs font-semibold" :class="hostKeyInfo.isMismatch ? 'text-rose-200' : 'text-amber-200'">
                {{ hostKeyInfo.isMismatch ? t('infra.hostKey.mismatchTitle') : t('infra.hostKey.verifyRequired') }}
              </p>
              <p class="text-[11px] font-mono text-zinc-300 truncate">
                {{ t('infra.hostKey.fingerprint') }}: <span class="font-bold text-white">{{ hostKeyInfo.remoteFingerprint }}</span>
              </p>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button
              type="button"
              @click="trustAndReconnect"
              :disabled="isTrustingHostKey"
              class="px-3 py-1 rounded text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50 cursor-pointer"
              :class="hostKeyInfo.isMismatch ? 'bg-rose-600 hover:bg-rose-500 text-white' : 'bg-amber-600 hover:bg-amber-500 text-zinc-950'"
            >
              <ShieldCheck class="w-3.5 h-3.5" :class="{ 'animate-spin': isTrustingHostKey }" />
              <span>{{ hostKeyInfo.isMismatch ? t('infra.hostKey.overrideTrust') : t('infra.hostKey.confirmTrust') }}</span>
            </button>
          </div>
        </div>

        <!-- Body: terminal + quick runbooks sidebar -->
        <div class="flex-1 min-h-0 flex relative">
          <div ref="terminalHost" class="flex-1 min-w-0 p-2 bg-[#0d0f14]" />

          <div
            v-if="showRunbookBar"
            class="absolute inset-y-0 right-0 z-20 md:static flex w-64 sm:w-60 max-w-[85vw] shrink-0 border-l border-zinc-800 bg-zinc-950/95 md:bg-zinc-900/40 backdrop-blur-md md:backdrop-blur-none flex-col"
          >
            <div class="px-3 py-2 border-b border-zinc-800/80 flex items-center justify-between gap-1.5 shrink-0">
              <div class="flex items-center gap-1.5 min-w-0">
                <Zap class="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-400 truncate">{{ t('term.quickRunbooks') }}</span>
              </div>
              <button
                type="button"
                @click="showRunbookBar = false"
                class="md:hidden p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors cursor-pointer shrink-0"
                title="Close runbooks"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>
            <div class="flex-1 overflow-y-auto overscroll-contain p-2 space-y-1.5">
              <p v-if="runbooks.length === 0" class="text-[11px] text-zinc-500 font-mono px-1 py-2">
                {{ t('term.noRunbooks') }}
              </p>
              <button
                v-for="rb in runbooks"
                :key="rb.id"
                type="button"
                @click="handleRunbookClick(rb)"
                class="w-full text-left px-2.5 py-2 rounded-md bg-zinc-900/60 border border-zinc-800 hover:border-zinc-600 transition-colors group cursor-pointer"
              >
                <div class="flex items-center gap-1.5">
                  <ChevronRight class="w-3 h-3 text-zinc-500 group-hover:text-emerald-400 transition-colors" />
                  <span class="text-[11px] text-zinc-200 font-medium truncate">{{ rb.title }}</span>
                </div>
                <p v-if="rb.description" class="text-[10px] text-zinc-500 mt-0.5 truncate pl-4.5">{{ rb.description }}</p>
              </button>
            </div>
          </div>
        </div>
      </div>
      <ConfirmModal
        :is-open="!!confirmRunbook"
        :title="t('term.confirmRunbookTitle') || 'Confirm Runbook Execution'"
        :message="`'${confirmRunbook?.title}':\n${confirmRunbook?.command}\nExecute on server '${asset.name}'?`"
        :confirm-text="t('term.execute') || 'Execute'"
        :cancel-text="t('common.cancel')"
        :is-danger="false"
        @confirm="doSendConfirmedRunbook"
        @cancel="confirmRunbook = null"
      />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import {
  TerminalSquare, RefreshCw, Eraser, ScrollText, Maximize2, Minimize2, X, Zap, ChevronRight,
  ShieldCheck, ShieldAlert, AlertTriangle
} from 'lucide-vue-next'
import { t } from '../../i18n'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import { parseSshHostKeyError } from '../../utils/sshSafety'
import ConfirmModal from '../common/ConfirmModal.vue'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import type { InfrastructureAsset, ServerRunbook } from '../../types/workspace'

const props = defineProps<{
  isOpen: boolean
  asset: InfrastructureAsset
  runbooks: ServerRunbook[]
}>()

const emit = defineEmits<{ (e: 'close'): void }>()

useBodyScrollLock(() => props.isOpen)

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

type WsStatus = 'connecting' | 'connected' | 'disconnected'
const wsStatus = ref<WsStatus>('disconnected')
const lastErrorMessage = ref('')
const isMaximized = ref(false)
const showRunbookBar = ref(typeof window !== 'undefined' ? window.innerWidth >= 768 : true)
const confirmRunbook = ref<ServerRunbook | null>(null)
const hostKeyInfo = computed(() => parseSshHostKeyError(lastErrorMessage.value))
const isTrustingHostKey = ref(false)

watch(isMaximized, () => {
  nextTick(() => {
    try { fitAddon?.fit() } catch { /* noop */ }
  })
})

async function trustAndReconnect() {
  if (hostKeyInfo.value.isMismatch) {
    if (!confirm(t('infra.hostKey.overrideConfirm'))) return
  }
  isTrustingHostKey.value = true
  try {
    await workspaceStore.trustInfraAssetHostKey(props.asset.id, hostKeyInfo.value.remoteFingerprint)
    toast.success(t('infra.hostKey.trustSuccess'))
    lastErrorMessage.value = ''
    reconnect()
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('infra.hostKey.trustFailed'))
  } finally {
    isTrustingHostKey.value = false
  }
}

const terminalHost = ref<HTMLElement | null>(null)

let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null
let reconnectTimer: number | null = null

const statusLabel = computed(() =>
  wsStatus.value === 'connected' ? t('term.connected')
    : wsStatus.value === 'connecting' ? t('term.connecting')
    : t('term.disconnected')
)

const statusClass = computed(() =>
  wsStatus.value === 'connected' ? 'border-emerald-800/60 text-emerald-400 bg-emerald-950/40'
    : wsStatus.value === 'connecting' ? 'border-amber-800/60 text-amber-400 bg-amber-950/40'
    : 'border-zinc-700 text-zinc-400 bg-zinc-900'
)

const statusDotClass = computed(() =>
  wsStatus.value === 'connected' ? 'bg-emerald-400'
    : wsStatus.value === 'connecting' ? 'bg-amber-400 animate-pulse'
    : 'bg-zinc-500'
)

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/ws/workspace/ssh/${props.asset.id}/`
}

function ensureTerminal() {
  if (term || !terminalHost.value) return
  // Terminal canvas stays dark in BOTH themes so ANSI colors read correctly.
  term = new Terminal({
    fontFamily: '"Cascadia Mono", "Fira Code", Menlo, Consolas, monospace',
    fontSize: 13,
    cursorBlink: true,
    convertEol: false,
    theme: {
      background: '#0d0f14',
      foreground: '#d4d4d8',
      cursor: '#34d399',
      selectionBackground: 'rgba(56, 189, 248, 0.28)'
    }
  })
  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalHost.value)
  fitAddon.fit()

  term.onData((data) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'input', data }))
    }
  })
  term.onResize(({ cols, rows }) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'resize', cols, rows }))
    }
  })

  resizeObserver?.disconnect()
  resizeObserver = new ResizeObserver(() => {
    try { fitAddon?.fit() } catch { /* host hidden */ }
  })
  resizeObserver.observe(terminalHost.value)
}

function connect() {
  if (ws) {
    ws.onclose = null
    ws.onerror = null
    ws.onmessage = null
    ws.close()
    ws = null
  }
  wsStatus.value = 'connecting'
  lastErrorMessage.value = ''
  term?.writeln(`\x1b[38;5;245m${t('term.connectingTo')} ${props.asset.ip_address || props.asset.hostname}...\x1b[0m`)

  const socket = new WebSocket(wsUrl())
  ws = socket

  socket.onopen = () => {
    if (socket !== ws) return
    // Stay CONNECTING (amber) here: the WebSocket transport is up but the
    // SSH handshake has not finished. Green CONNECTED only after the
    // server's 'ready' frame confirms the PTY is alive.
    const dims = term ? { cols: term.cols, rows: term.rows } : { cols: 120, rows: 30 }
    socket.send(JSON.stringify({ type: 'resize', ...dims }))
  }

  socket.onmessage = (event) => {
    if (socket !== ws) return
    try {
      const payload = JSON.parse(event.data)
      if (payload.type === 'ready') {
        wsStatus.value = 'connected'
      } else if (payload.type === 'output' && typeof payload.data === 'string') {
        term?.write(payload.data)
      } else if (payload.type === 'error' && typeof payload.message === 'string') {
        lastErrorMessage.value = payload.message
        wsStatus.value = 'disconnected'
        term?.writeln(`\r\n\x1b[38;2;251;113;133m✗ ${payload.message}\x1b[0m`)
      } else if (payload.type === 'closed') {
        wsStatus.value = 'disconnected'
        term?.writeln(`\r\n\x1b[38;5;245m${t('term.sessionClosed')}\x1b[0m`)
      }
    } catch { /* ignore malformed frame */ }
  }

  socket.onerror = () => {
    if (socket !== ws) return
    wsStatus.value = 'disconnected'
  }

  socket.onclose = (event) => {
    if (socket !== ws) return
    wsStatus.value = 'disconnected'
    if (event.code === 4401) term?.writeln(`\r\n\x1b[38;2;251;113;133m${t('term.authFailed')}\x1b[0m`)
    else if (event.code === 4403) term?.writeln(`\r\n\x1b[38;2;251;113;133m${t('term.forbidden')}\x1b[0m`)
    else if (event.code === 1011 && !lastErrorMessage.value) term?.writeln(`\r\n\x1b[38;2;251;113;133m${t('term.sshFailed')}\x1b[0m`)
    else if (!lastErrorMessage.value) term?.writeln(`\r\n\x1b[38;5;245m${t('term.disconnected')}\x1b[0m`)
  }
}

function reconnect() {
  term?.clear()
  connect()
}

function clearScreen() {
  term?.clear()
}

function toggleRunbookBar() {
  showRunbookBar.value = !showRunbookBar.value
  nextTick(() => {
    try { fitAddon?.fit() } catch { /* noop */ }
  })
}

function handleRunbookClick(rb: ServerRunbook) {
  confirmRunbook.value = rb
}

function doSendConfirmedRunbook() {
  const rb = confirmRunbook.value
  if (!rb) return
  confirmRunbook.value = null
  sendRunbook(rb)
}

function sendRunbook(rb: ServerRunbook) {
  if (ws?.readyState !== WebSocket.OPEN) return
  const cd = rb.working_dir ? `cd ${rb.working_dir} && ` : ''
  ws.send(JSON.stringify({ type: 'input', data: `${cd}${rb.command}\n` }))
}

function requestClose() {
  emit('close')
}

let isMounted = false
let startId = 0

function teardown() {
  startId++
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.onclose = null
    ws.onerror = null
    ws.onmessage = null
    ws.close()
    ws = null
  }
  wsStatus.value = 'disconnected'
  resizeObserver?.disconnect()
  resizeObserver = null
  term?.dispose()
  term = null
  fitAddon = null
}

function handleWindowResize() {
  try { fitAddon?.fit() } catch { /* noop */ }
}

async function start() {
  if (!props.isOpen || !isMounted) return
  const currentStartId = ++startId

  if (typeof window !== 'undefined' && window.innerWidth < 768) {
    showRunbookBar.value = false
  }

  await nextTick()
  if (currentStartId !== startId || !props.isOpen || !isMounted) return

  if (!terminalHost.value) {
    await nextTick()
    if (currentStartId !== startId || !props.isOpen || !isMounted) return
  }

  ensureTerminal()
  if (currentStartId !== startId || !props.isOpen || !isMounted) return

  connect()
  nextTick(() => {
    if (currentStartId === startId && props.isOpen && isMounted) {
      try { fitAddon?.fit() } catch { /* noop */ }
    }
  })
}

onMounted(() => {
  isMounted = true
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', handleWindowResize)
    window.addEventListener('orientationchange', handleWindowResize)
  }
  if (props.isOpen) {
    start()
  }
})

watch(() => props.isOpen, (open) => {
  if (open) {
    start()
  } else {
    teardown()
  }
})

watch(() => props.asset.id, () => {
  if (props.isOpen) {
    if (!term) {
      start()
    } else {
      term.clear()
      connect()
    }
  }
})

onBeforeUnmount(() => {
  isMounted = false
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleWindowResize)
    window.removeEventListener('orientationchange', handleWindowResize)
  }
  teardown()
})
</script>
