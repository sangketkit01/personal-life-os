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
            <Server class="w-4 h-4 text-sky-400" />
            <h3 class="text-sm font-semibold text-zinc-100">
              {{ editing ? t('infra.form.editTitle') : t('infra.form.createTitle') }}
            </h3>
          </div>
          <button type="button" @click="emit('close')" class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-100 transition-colors">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-5">
          <!-- General -->
          <section class="space-y-3">
            <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800/70 pb-1.5">{{ t('infra.form.general') }}</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.name') }} *</span>
                <input v-model="form.name" type="text" required maxlength="150"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.type') }}</span>
                <select v-model="form.asset_type"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                  <option v-for="at in ASSET_TYPES" :key="at" :value="at">{{ t(`infra.types.${at}`) }}</option>
                </select>
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.provider') }}</span>
                <input v-model="form.provider" type="text" placeholder="e.g. AWS, DigitalOcean, Hetzner"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label v-if="!isServiceType" class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.region') }}</span>
                <input v-model="form.region" type="text" placeholder="e.g. ap-southeast-1, us-east-1"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label v-if="!isServiceType" class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.os') }}</span>
                <input v-model="form.os_name" type="text" placeholder="e.g. Ubuntu 24.04 LTS, Debian 12"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label v-if="isServiceType" class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.domain') }}</span>
                <input v-model="form.primary_domain" type="text" placeholder="e.g. app.mydomain.com"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label v-if="isServiceType" class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.consoleUrl') }}</span>
                <input v-model="form.console_url" type="url" placeholder="https://..."
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label v-if="isServiceType" class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.expiry') }}</span>
                <input v-model="form.expiry_date" type="date"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
            </div>
            <div v-if="!isServiceType" class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">vCPU</span>
                <input v-model.number="specs.vcpu" type="number" min="1"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">RAM (GB)</span>
                <input v-model.number="specs.ram_gb" type="number" min="1"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.disk') }} (GB)</span>
                <input v-model.number="specs.disk_gb" type="number" min="1"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
            </div>
          </section>

          <!-- Network & SSH -->
          <section v-if="!isServiceType" class="space-y-3">
            <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800/70 pb-1.5">{{ t('infra.form.networkSsh') }}</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.ip') }}</span>
                <input v-model="form.ip_address" type="text" placeholder="e.g. 1.2.3.4"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.sshPort') }}</span>
                <input v-model.number="form.ssh_port" type="number" min="1" max="65535"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.domain') }}</span>
                <input v-model="form.primary_domain" type="text" placeholder="e.g. app.mydomain.com"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.consoleUrl') }}</span>
                <input v-model="form.console_url" type="url" placeholder="https://..."
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.sshAuth') }}</span>
                <select v-model="form.ssh_auth_type"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                  <option value="PASSWORD">{{ t('infra.auth.password') }}</option>
                  <option value="PRIVATE_KEY">{{ t('infra.auth.privateKey') }}</option>
                  <option value="NONE">{{ t('infra.auth.none') }}</option>
                </select>
              </label>
              <label v-if="form.ssh_auth_type !== 'NONE'" class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.sshUser') }}</span>
                <input v-model="form.ssh_username" type="text" placeholder="e.g. root, ubuntu, debian"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
              </label>
            </div>

            <template v-if="form.ssh_auth_type === 'PASSWORD'">
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">
                  {{ t('infra.form.sshPassword') }}
                  <span v-if="editing && asset?.has_ssh_password" class="text-emerald-500/80">· {{ t('infra.form.stored') }}</span>
                </span>
                <input v-model="secrets.ssh_password" type="password" autocomplete="new-password"
                  :placeholder="editing ? t('infra.form.keepPlaceholder') : ''"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
              </label>
            </template>

            <template v-if="form.ssh_auth_type === 'PRIVATE_KEY'">
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">
                  {{ t('infra.form.privateKey') }}
                  <span v-if="editing && asset?.has_ssh_key" class="text-emerald-500/80">· {{ t('infra.form.stored') }}</span>
                </span>
                <textarea v-model="secrets.ssh_private_key" rows="4"
                  :placeholder="editing ? t('infra.form.keepPlaceholder') : '-----BEGIN OPENSSH PRIVATE KEY-----'"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.passphrase') }}</span>
                <input v-model="secrets.ssh_passphrase" type="password" autocomplete="new-password"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
              </label>
            </template>
          </section>

          <!-- Billing -->
          <section class="space-y-3">
            <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800/70 pb-1.5">{{ t('infra.form.billing') }}</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="block sm:col-span-2">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.ownership') }}</span>
                <select v-model="form.billing_ownership"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                  <option v-for="bo in OWNERSHIPS" :key="bo" :value="bo">{{ t(`infra.ownership.${bo}`) }}</option>
                </select>
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.cost') }}</span>
                <input v-model="form.cost_amount" type="number" step="0.01" min="0"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.currency') }}</span>
                <select v-model="form.cost_currency"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                  <option value="" disabled>Select currency</option>
                  <option>THB</option>
                  <option>USD</option>
                </select>
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.cycle') }}</span>
                <select v-model="form.billing_cycle"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600">
                  <option value="" disabled>Select billing cycle</option>
                  <option>MONTHLY</option>
                  <option>QUARTERLY</option>
                  <option>YEARLY</option>
                </select>
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.nextBilling') }}</span>
                <input v-model="form.next_billing_date" type="date"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
            </div>

            <label class="flex items-start gap-2.5 p-2.5 rounded-md bg-zinc-900/60 border border-zinc-800 cursor-pointer">
              <input v-model="form.sync_to_radar" type="checkbox" class="mt-0.5 accent-emerald-500" />
              <span>
                <span class="text-xs text-zinc-200 font-medium">{{ t('infra.form.syncRadar') }}</span>
                <span class="block text-[10px] text-zinc-500 mt-0.5">{{ t('infra.form.syncRadarHint') }}</span>
              </span>
            </label>
          </section>

          <!-- Watchdog -->
          <section v-if="!isServiceType" class="space-y-3">
            <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800/70 pb-1.5">{{ t('infra.form.watchdog') }}</p>
            <label class="flex items-start gap-2.5 p-2.5 rounded-md bg-zinc-900/60 border border-zinc-800 cursor-pointer">
              <input v-model="form.watchdog_enabled" type="checkbox" class="mt-0.5 accent-amber-500" />
              <span>
                <span class="text-xs text-zinc-200 font-medium">{{ t('infra.form.watchdogEnable') }}</span>
                <span class="block text-[10px] text-zinc-500 mt-0.5">{{ t('infra.form.watchdogHint') }}</span>
              </span>
            </label>
            <div v-if="form.watchdog_enabled" class="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">CPU %</span>
                <input v-model.number="form.alert_cpu_threshold" type="number" min="1" max="100"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">RAM %</span>
                <input v-model.number="form.alert_ram_threshold" type="number" min="1" max="100"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.disk') }} %</span>
                <input v-model.number="form.alert_disk_threshold" type="number" min="1" max="100"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
            </div>
          </section>

          <!-- Shared projects pill picker -->
          <section v-if="otherProjects.length > 0" class="space-y-2">
            <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800/70 pb-1.5">{{ t('infra.form.sharedProjects') }}</p>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="p in otherProjects"
                :key="p.id"
                type="button"
                @click="toggleSharedProject(p.id)"
                class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors"
                :class="form.shared_projects.includes(p.id)
                  ? 'bg-zinc-800 border-zinc-600 text-zinc-100'
                  : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-600'"
              >
                <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ backgroundColor: p.color }" />
                {{ p.name }}
                <Check v-if="form.shared_projects.includes(p.id)" class="w-3 h-3 text-emerald-400" />
              </button>
            </div>
            <p class="text-[10px] text-zinc-500 font-mono flex items-start gap-1.5">
              <Info class="w-3 h-3 mt-0.5 shrink-0 text-sky-400/80" />
              {{ t('infra.form.sharedProjectsHint') }}
            </p>
          </section>

          <label class="block">
            <span class="text-[11px] text-zinc-400 font-mono">{{ t('infra.form.notes') }}</span>
            <textarea v-model="form.notes" rows="2"
              class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
          </label>
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
import { ref, reactive, watch, computed } from 'vue'
import { Server, X, Save, Check, Info } from 'lucide-vue-next'
import { t } from '../../i18n'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import type { InfrastructureAsset, InfraAssetType, BillingOwnership } from '../../types/workspace'

const props = defineProps<{
  isOpen: boolean
  projectId: string
  asset: InfrastructureAsset | null
  defaultMode?: 'server' | 'service'
  projects?: Array<{ id: string; name: string; color: string }>
}>()

const emit = defineEmits<{ (e: 'close'): void; (e: 'saved'): void }>()

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const ASSET_TYPES: InfraAssetType[] = [
  'VPS', 'DEDICATED', 'MANAGED_DB', 'PAAS',
  'SAAS', 'API_SERVICE', 'DOMAIN', 'CDN_DNS', 'SSL_CERT',
  'STORAGE', 'EMAIL_SMTP', 'LICENSE', 'OTHER'
]
const OWNERSHIPS: BillingOwnership[] = ['SELF_FUNDED', 'CLIENT_REIMBURSED', 'CLIENT_DIRECT']

const editing = computed(() => !!props.asset)

// Service/subscription asset types hide SSH, specs and watchdog sections.
const SERVICE_TYPES: InfraAssetType[] = [
  'SAAS', 'API_SERVICE', 'DOMAIN', 'CDN_DNS', 'SSL_CERT',
  'STORAGE', 'EMAIL_SMTP', 'LICENSE', 'OTHER'
]
const isServiceType = computed(() => SERVICE_TYPES.includes(form.value.asset_type))
const primaryProjectId = computed(() => props.asset?.project || props.projectId)
const otherProjects = computed(() =>
  (props.projects || []).filter(p => p.id !== primaryProjectId.value)
)

const isSaving = ref(false)
const specs = reactive({ vcpu: undefined as number | undefined, ram_gb: undefined as number | undefined, disk_gb: undefined as number | undefined })
const secrets = reactive({ ssh_password: '', ssh_private_key: '', ssh_passphrase: '' })

const emptyForm = () => ({
  name: '',
  asset_type: 'VPS' as InfraAssetType,
  shared_projects: [] as string[],
  provider: '',
  region: '',
  os_name: '',
  expiry_date: '',
  ip_address: '',
  hostname: '',
  ssh_port: 22,
  primary_domain: '',
  console_url: '',
  ssh_auth_type: 'PASSWORD' as 'PASSWORD' | 'PRIVATE_KEY' | 'NONE',
  ssh_username: '',
  billing_ownership: 'SELF_FUNDED' as BillingOwnership,
  cost_amount: '' as string | number,
  cost_currency: '',
  billing_cycle: '',
  next_billing_date: '',
  sync_to_radar: false,
  watchdog_enabled: false,
  alert_cpu_threshold: 90,
  alert_ram_threshold: 90,
  alert_disk_threshold: 85,
  notes: ''
})
const form = ref(emptyForm())

watch(() => props.isOpen, (open) => {
  if (!open) return
  secrets.ssh_password = ''
  secrets.ssh_private_key = ''
  secrets.ssh_passphrase = ''
  if (props.asset) {
    const a = props.asset
    form.value = {
      name: a.name,
      asset_type: a.asset_type,
      shared_projects: (a.shared_projects || []).slice(),
      provider: a.provider,
      region: a.region,
      os_name: a.os_name,
      expiry_date: a.expiry_date || '',
      ip_address: a.ip_address,
      hostname: a.hostname,
      ssh_port: a.ssh_port,
      primary_domain: a.primary_domain,
      console_url: a.console_url,
      ssh_auth_type: a.ssh_auth_type,
      ssh_username: a.ssh_username,
      billing_ownership: a.billing_ownership,
      cost_amount: a.cost_amount,
      cost_currency: a.cost_currency,
      billing_cycle: a.billing_cycle,
      next_billing_date: a.next_billing_date || '',
      sync_to_radar: a.sync_to_radar,
      watchdog_enabled: a.watchdog_enabled,
      alert_cpu_threshold: a.alert_cpu_threshold,
      alert_ram_threshold: a.alert_ram_threshold,
      alert_disk_threshold: a.alert_disk_threshold,
      notes: a.notes
    }
    specs.vcpu = a.specs?.vcpu
    specs.ram_gb = a.specs?.ram_gb
    specs.disk_gb = a.specs?.disk_gb
  } else {
    form.value = emptyForm()
    if (props.defaultMode === 'service') {
      form.value.asset_type = 'SAAS'
    }
    specs.vcpu = undefined
    specs.ram_gb = undefined
    specs.disk_gb = undefined
  }
})

function toggleSharedProject(projectId: string) {
  const idx = form.value.shared_projects.indexOf(projectId)
  if (idx === -1) {
    form.value.shared_projects.push(projectId)
  } else {
    form.value.shared_projects.splice(idx, 1)
  }
}

async function save() {
  if (!form.value.name.trim()) return
  isSaving.value = true
  try {
    const payload: Record<string, any> = {
      project: props.asset ? (props.asset.project ?? props.projectId) : props.projectId,
      ...form.value,
      shared_projects: form.value.shared_projects,
      expiry_date: form.value.expiry_date || null,
      next_billing_date: form.value.next_billing_date || null,
      cost_amount: form.value.cost_amount === '' ? '0' : String(form.value.cost_amount),
      specs: {
        ...(specs.vcpu != null && { vcpu: specs.vcpu }),
        ...(specs.ram_gb != null && { ram_gb: specs.ram_gb }),
        ...(specs.disk_gb != null && { disk_gb: specs.disk_gb })
      }
    }
    // Secrets are write-only: send them only when the user typed a value so
    // an untouched field keeps the stored credential intact.
    for (const [key, value] of Object.entries(secrets)) {
      if (value) payload[key] = value
    }

    if (props.asset) {
      await workspaceStore.updateInfraAsset(props.asset.id, payload)
      toast.success(t('infra.toast.updated'))
    } else {
      await workspaceStore.createInfraAsset(payload)
      toast.success(t('infra.toast.created'))
    }
    emit('saved')
    emit('close')
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('infra.toast.saveFailed'))
  } finally {
    isSaving.value = false
  }
}
</script>
