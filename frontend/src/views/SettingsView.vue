<template>
  <div class="space-y-6 max-w-4xl mx-auto font-sans">
    <div class="pb-4 border-b border-zinc-800/80">
      <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Settings & Security</h1>
      <p class="text-xs text-zinc-500 mt-0.5">Manage active device sessions, Telegram Butler webhook authorization, and membership invite codes</p>
    </div>

    <!-- 1. Telegram Butler Connection -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-md bg-zinc-900 text-zinc-200 flex items-center justify-center border border-zinc-800">
            <Bot class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Telegram Butler Bot</h2>
            <p class="text-xs text-zinc-500">10:00 AM daily alert with interactive settlement actions</p>
          </div>
        </div>

        <span
          class="text-[10px] font-mono px-2 py-0.5 rounded border uppercase"
          :class="[
            authStore.user?.is_telegram_connected
              ? 'bg-zinc-900 text-emerald-400 border-zinc-800'
              : 'bg-zinc-900 text-zinc-500 border-zinc-800'
          ]"
        >
          {{ authStore.user?.is_telegram_connected ? 'CONNECTED' : 'DISCONNECTED' }}
        </span>
      </div>

      <div class="p-4">
        <div v-if="authStore.user?.is_telegram_connected" class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono flex items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <span class="text-zinc-400">Linked Chat ID: <strong class="text-zinc-100 font-semibold">{{ authStore.user.telegram_chat_id }}</strong></span>
            <span class="text-[11px] text-emerald-400">• Active</span>
          </div>
          <button
            @click="handleDisconnectTelegram"
            :disabled="isDisconnectingTelegram"
            type="button"
            class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-rose-400 text-xs font-sans transition-colors disabled:opacity-50"
          >
            {{ isDisconnectingTelegram ? 'Disconnecting...' : 'Disconnect' }}
          </button>
        </div>

        <div v-else class="flex items-center justify-between p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
          <span class="text-xs text-zinc-400">Authorize @brandy_personal_os_bot to receive private 1-on-1 notifications</span>
          <button
            @click="handleConnectTelegram"
            :disabled="isGeneratingToken"
            class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {{ isGeneratingToken ? 'Generating...' : 'Connect Telegram' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 2. Google Drive Cloud Storage (Zero-Disk Storage Backend) -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-md bg-zinc-900 text-zinc-200 flex items-center justify-center border border-zinc-800">
            <HardDrive class="w-4 h-4 text-zinc-400" />
          </div>
          <div>
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Google Drive Cloud Storage</h2>
            <p class="text-xs text-zinc-500 mt-0.5">Exclusive cloud storage for transaction slips, contracts, and documents (Zero-Disk Architecture)</p>
          </div>
        </div>

        <span
          class="text-[10px] font-mono px-2 py-0.5 rounded border uppercase"
          :class="[
            storageStore.isConnected
              ? 'bg-zinc-900 text-zinc-100 border-zinc-700 font-semibold'
              : 'bg-zinc-900 text-zinc-500 border-zinc-800'
          ]"
        >
          {{ storageStore.isConnected ? 'CONNECTED' : 'DISCONNECTED' }}
        </span>
      </div>

      <div class="p-4">
        <div v-if="storageStore.isConnected" class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="space-y-0.5">
            <div class="text-zinc-300">
              Connected Account: <strong class="text-zinc-100 font-semibold">{{ storageStore.googleEmail }}</strong>
            </div>
            <div class="text-[11px] text-zinc-500">
              Cloud Directory: Personal Life OS (Ledger, Finance, Portfolio, Workspace)
            </div>
          </div>
          <div class="flex items-center gap-2">
            <a
              v-if="storageStore.rootFolderId"
              :href="`https://drive.google.com/drive/folders/${storageStore.rootFolderId}`"
              target="_blank"
              class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-sans transition-colors flex items-center gap-1.5"
            >
              <span>Open in Drive</span>
              <ExternalLink class="w-3.5 h-3.5 text-zinc-400" />
            </a>
            <button
              @click="handleDisconnectDrive"
              :disabled="storageStore.isLoading"
              type="button"
              class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 text-xs font-sans transition-colors"
            >
              Disconnect
            </button>
          </div>
        </div>

        <div v-else class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
          <div>
            <div class="text-xs text-zinc-200 font-medium">Google Drive connection is required for file storage</div>
            <p class="text-[11px] text-zinc-500 mt-0.5">Connect your Google Drive account to enable receipt uploads and contract attachments</p>
          </div>
          <button
            @click="storageStore.startConnect"
            :disabled="storageStore.isConnecting"
            type="button"
            class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm shrink-0"
          >
            <CloudUpload class="w-3.5 h-3.5 text-zinc-950" />
            <span>{{ storageStore.isConnecting ? 'Opening...' : 'Connect Google Drive' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 3. Password & Account Security -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div>
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Password & Account Credentials</h2>
          <p class="text-xs text-zinc-500 mt-0.5">Rotate your account password and automatically revoke all other device sessions</p>
        </div>
      </div>

      <form @submit.prevent="handleChangePassword" class="p-4 space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Current Password</label>
            <input
              v-model="passwordForm.current_password"
              type="password"
              required
              autocomplete="current-password"
              placeholder="••••••••"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">New Password</label>
            <input
              v-model="passwordForm.new_password"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              placeholder="Minimum 8 characters"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>
        </div>
        <div class="flex justify-end">
          <button
            type="submit"
            :disabled="isChangingPassword"
            class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {{ isChangingPassword ? 'Updating...' : 'Update Password' }}
          </button>
        </div>
      </form>
    </div>

    <!-- 4. Active Devices & Sessions -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between gap-2">
        <div>
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Active Sessions & Devices</h2>
          <p class="text-xs text-zinc-500 mt-0.5">Track hardware fingerprints and revoke unauthorized sessions</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="sessions.length > 1"
            @click="revokeOtherSessions"
            type="button"
            class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-rose-950/20 text-zinc-400 hover:text-rose-400 border border-zinc-800 hover:border-rose-500/30 text-[11px] font-mono transition-colors"
          >
            Revoke All Others
          </button>
          <button
            @click="fetchSessions"
            type="button"
            class="text-xs text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1 font-mono"
          >
            <RefreshCw class="w-3 h-3" />
            <span>Sync</span>
          </button>
        </div>
      </div>

      <div class="p-4 space-y-2">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 flex items-center justify-between gap-4 font-mono text-xs"
        >
          <div class="flex items-center gap-3">
            <div class="w-7 h-7 rounded bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400">
              <Laptop class="w-3.5 h-3.5" />
            </div>
            <div>
              <div class="text-xs font-medium text-zinc-200 flex items-center gap-2">
                <span>{{ session.device_name }}</span>
                <span
                  v-if="session.is_current"
                  class="text-[9px] font-mono px-1 py-0.2 rounded bg-zinc-800 text-zinc-300 border border-zinc-700/60"
                >
                  CURRENT
                </span>
              </div>
              <div class="text-[10px] text-zinc-500 mt-0.5">
                IP: {{ session.ip_address || 'Internal' }} • Last active: {{ new Date(session.last_active_at).toLocaleDateString('en-GB') }}
              </div>
            </div>
          </div>

          <button
            v-if="!session.is_current"
            @click="revokeSession(session.id)"
            class="px-2 py-1 rounded bg-zinc-900 hover:bg-rose-950/20 text-zinc-400 hover:text-rose-400 border border-zinc-800 hover:border-rose-500/30 text-[11px] transition-colors"
          >
            Revoke
          </button>
        </div>
      </div>
    </div>

    <!-- 5. Invite Codes for Friends (1 Code = 1 User) -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div>
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Invitation Access Codes</h2>
          <p class="text-xs text-zinc-500 mt-0.5">Generate single-use invite codes (1 Code = 1 User) to onboard trusted peers</p>
        </div>
        <button
          @click="createInviteCode"
          class="px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1"
        >
          <Plus class="w-3 h-3 text-zinc-950" />
          <span>New Invite Code</span>
        </button>
      </div>

      <div class="p-4">
        <div v-if="invites.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500">
          No invite codes generated yet.
        </div>

        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <div
            v-for="inv in invites"
            :key="inv.id"
            class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 flex items-center justify-between gap-2 font-mono"
          >
            <div>
              <div class="text-xs font-bold text-zinc-200 tracking-wider">{{ inv.code }}</div>
              <div class="text-[10px] text-zinc-500 mt-0.5">
                <span v-if="inv.used_by_username" class="text-zinc-400">Used by @{{ inv.used_by_username }} (1/1)</span>
                <span v-else-if="inv.is_active" class="text-emerald-400">Available (1 User)</span>
                <span v-else>Exhausted ({{ inv.uses_count }}/1)</span>
              </div>
            </div>
            <div class="flex items-center gap-1.5">
              <button
                v-if="inv.is_active"
                @click="copyCode(inv.code)"
                type="button"
                class="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-[10px] transition-colors flex items-center gap-1"
              >
                <Copy class="w-3 h-3" />
                <span>Copy</span>
              </button>
              <button
                @click="deleteInviteCode(inv.id, inv.code)"
                type="button"
                title="Delete invite code"
                class="p-1.5 rounded bg-zinc-900 hover:bg-rose-950/20 border border-zinc-800 hover:border-rose-500/30 text-zinc-400 hover:text-rose-400 transition-colors"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 4. Security & Activity Audit Log -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-md bg-zinc-900 text-zinc-200 flex items-center justify-center border border-zinc-800">
            <ShieldCheck class="w-4 h-4 text-zinc-400" />
          </div>
          <div>
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Security & Activity Audit Log</h2>
            <p class="text-xs text-zinc-500 mt-0.5">Immutable audit trail of authentication events, financial operations, and portfolio executions</p>
          </div>
        </div>
        <button
          @click="fetchAuditLogs"
          :disabled="isLoadingLogs"
          class="text-xs text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1 font-mono disabled:opacity-50"
        >
          <RefreshCw class="w-3 h-3" :class="{ 'animate-spin': isLoadingLogs }" />
          <span>Sync</span>
        </button>
      </div>

      <div class="p-4">
        <div v-if="auditLogs.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500">
          No security activity recorded yet.
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">
                <th class="pb-2.5">Timestamp</th>
                <th class="pb-2.5">Domain</th>
                <th class="pb-2.5">Action</th>
                <th class="pb-2.5">Description</th>
                <th class="pb-2.5">Origin / Device</th>
                <th class="pb-2.5 text-right">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr
                v-for="log in auditLogs"
                :key="log.id"
                class="hover:bg-zinc-900/40 transition-colors"
              >
                <!-- Timestamp -->
                <td class="py-2.5 text-zinc-400 whitespace-nowrap text-[11px]">
                  {{ formatLogTime(log.created_at) }}
                </td>

                <!-- Domain Category -->
                <td class="py-2.5">
                  <span
                    class="px-1.5 py-0.2 rounded text-[9px] font-mono border uppercase"
                    :class="getCategoryClass(log.category)"
                  >
                    {{ log.category }}
                  </span>
                </td>

                <!-- Action -->
                <td class="py-2.5 font-bold text-zinc-200 whitespace-nowrap">
                  {{ log.action }}
                </td>

                <!-- Description -->
                <td class="py-2.5 text-zinc-300 font-sans text-xs max-w-xs truncate" :title="log.description">
                  {{ log.description }}
                </td>

                <!-- Origin / Device -->
                <td class="py-2.5 text-zinc-500 text-[11px] whitespace-nowrap">
                  <span>{{ log.device_name || 'System' }}</span>
                  <span v-if="log.ip_address" class="text-zinc-600 ml-1">({{ log.ip_address }})</span>
                </td>

                <!-- Status Indicator -->
                <td class="py-2.5 text-right whitespace-nowrap">
                  <span
                    class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium border"
                    :class="getStatusClass(log.status)"
                  >
                    <span
                      class="w-1.5 h-1.5 rounded-full"
                      :class="log.status === 'SUCCESS' ? 'bg-emerald-400' : (log.status === 'WARNING' ? 'bg-amber-400' : 'bg-rose-400')"
                    />
                    {{ log.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      @confirm="executeConfirmModal"
      @cancel="confirmModal.isOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useStorageStore } from '../stores/storage'
import { useToastStore } from '../stores/toast'
import apiClient from '../api/client'
import type { UserDeviceSession, InviteCode, ActivityLog } from '../types'
import ConfirmModal from '../components/common/ConfirmModal.vue'
import {
  Bot,
  Laptop,
  Plus,
  RefreshCw,
  Copy,
  Trash2,
  ShieldCheck,
  HardDrive,
  ExternalLink,
  CloudUpload
} from 'lucide-vue-next'

const authStore = useAuthStore()
const storageStore = useStorageStore()
const toast = useToastStore()

const isGeneratingToken = ref(false)
const isDisconnectingTelegram = ref(false)
const isChangingPassword = ref(false)
const passwordForm = ref({
  current_password: '',
  new_password: '',
})
const sessions = ref<UserDeviceSession[]>([])
const invites = ref<InviteCode[]>([])
const auditLogs = ref<ActivityLog[]>([])
const isLoadingLogs = ref(false)

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Confirm',
  isDanger: true,
  action: () => {}
})

function executeConfirmModal() {
  confirmModal.isOpen = false
  confirmModal.action()
}

async function handleConnectTelegram() {
  isGeneratingToken.value = true
  try {
    const data = await authStore.generateTelegramConnect()
    window.open(data.deep_link, '_blank')
  } catch (err) {
    toast.error('Failed to generate connection link')
  } finally {
    isGeneratingToken.value = false
  }
}

function handleDisconnectTelegram() {
  confirmModal.title = 'Disconnect Telegram Bot'
  confirmModal.message = 'Are you sure you want to disconnect Telegram Bot? You will no longer receive daily notifications until reconnected.'
  confirmModal.confirmText = 'Disconnect'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    isDisconnectingTelegram.value = true
    try {
      await authStore.disconnectTelegram()
      await fetchAuditLogs()
      toast.info('Telegram account disconnected')
    } catch (err) {
      toast.error('Failed to disconnect Telegram account')
    } finally {
      isDisconnectingTelegram.value = false
    }
  }
  confirmModal.isOpen = true
}

async function handleChangePassword() {
  isChangingPassword.value = true
  try {
    const res = await authStore.changePassword(passwordForm.value)
    passwordForm.value.current_password = ''
    passwordForm.value.new_password = ''
    await fetchSessions()
    await fetchAuditLogs()
    toast.success(res.message || 'Password updated successfully')
  } catch (err: any) {
    const errorData = err.response?.data
    let msg = 'Failed to update password'
    if (errorData) {
      if (typeof errorData.detail === 'string') msg = errorData.detail
      else {
        const firstKey = Object.keys(errorData)[0]
        if (firstKey) {
          const val = errorData[firstKey]
          msg = Array.isArray(val) ? val[0] : String(val)
        }
      }
    }
    toast.error(msg)
  } finally {
    isChangingPassword.value = false
  }
}

async function fetchSessions() {
  try {
    const res = await apiClient.get<UserDeviceSession[]>('/auth/sessions/')
    sessions.value = res.data
  } catch (err) {
    console.error('Failed to load sessions', err)
  }
}

async function revokeSession(id: string) {
  try {
    await apiClient.post(`/auth/sessions/${id}/revoke/`)
    await fetchSessions()
    await fetchAuditLogs()
    toast.info('Session revoked successfully')
  } catch (err) {
    toast.error('Failed to revoke session')
  }
}

function revokeOtherSessions() {
  confirmModal.title = 'Revoke All Other Sessions'
  confirmModal.message = 'Are you sure you want to revoke all other active device sessions? Other logged-in devices will be signed out immediately.'
  confirmModal.confirmText = 'Revoke All Others'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      const res = await apiClient.post<{ message: string; revoked_count: number }>('/auth/sessions/revoke-others/')
      await fetchSessions()
      await fetchAuditLogs()
      toast.info(res.data.message || 'Other sessions revoked')
    } catch (err) {
      toast.error('Failed to revoke other sessions')
    }
  }
  confirmModal.isOpen = true
}

async function fetchInvites() {
  try {
    const res = await apiClient.get<InviteCode[]>('/auth/invites/')
    invites.value = res.data
  } catch (err) {
    console.error('Failed to load invites', err)
  }
}

async function createInviteCode() {
  try {
    await apiClient.post('/auth/invites/')
    await fetchInvites()
    await fetchAuditLogs()
    toast.success('Generated new single-use invite code (1 User)')
  } catch (err) {
    toast.error('Failed to create invite code')
  }
}

function deleteInviteCode(id: string, code: string) {
  confirmModal.title = 'Delete Invite Code'
  confirmModal.message = `Are you sure you want to delete invite code "${code}"? This action cannot be undone.`
  confirmModal.confirmText = 'Delete Code'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await apiClient.delete(`/auth/invites/${id}/`)
      await fetchInvites()
      await fetchAuditLogs()
      toast.info(`Deleted invite code ${code}`)
    } catch (err) {
      toast.error('Failed to delete invite code')
    }
  }
  confirmModal.isOpen = true
}

function copyCode(code: string) {
  navigator.clipboard.writeText(code)
  toast.success(`Copied invite code ${code} to clipboard`)
}

async function fetchAuditLogs() {
  isLoadingLogs.value = true
  try {
    const res = await apiClient.get<ActivityLog[]>('/auth/audit-logs/')
    auditLogs.value = res.data
  } catch (err) {
    console.error('Failed to load audit logs', err)
  } finally {
    isLoadingLogs.value = false
  }
}

function formatLogTime(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getCategoryClass(_category: string) {
  return 'bg-zinc-900 text-zinc-400 border-zinc-800'
}

function getStatusClass(status: string) {
  switch (status) {
    case 'SUCCESS':
      return 'bg-zinc-900 text-emerald-400 border-zinc-800'
    case 'WARNING':
      return 'bg-zinc-900 text-zinc-300 border-zinc-800'
    case 'FAILED':
      return 'bg-zinc-900 text-rose-400 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

function handleDisconnectDrive() {
  confirmModal.title = 'Disconnect Google Drive'
  confirmModal.message = 'Are you sure you want to disconnect Google Drive? Uploading new files will be disabled until you reconnect.'
  confirmModal.confirmText = 'Disconnect'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    await storageStore.disconnect()
  }
  confirmModal.isOpen = true
}

onMounted(() => {
  fetchSessions()
  fetchInvites()
  fetchAuditLogs()
  storageStore.fetchStatus()
})
</script>
