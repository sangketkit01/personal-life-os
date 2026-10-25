<template>
  <div class="space-y-5">
    <!-- ================= Zone 1: MA Contract & Project Economics ================= -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- MA Contract & SLA -->
      <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
        <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <FileSignature class="w-3.5 h-3.5 text-sky-400" />
            <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('ma.contractTitle') }}</h3>
          </div>
          <button
            type="button"
            @click="maModalOpen = true"
            class="px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-300 hover:text-zinc-100 hover:border-zinc-600 transition-colors flex items-center gap-1.5"
          >
            <Pencil class="w-3 h-3" />
            {{ t('ma.edit.button') }}
          </button>
        </div>

        <div class="p-5 space-y-4">
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-zinc-100 truncate">{{ project.client_name || t('ma.noClient') }}</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border shrink-0"
                  :class="project.project_type === 'MA_CONTRACT' ? 'border-emerald-800/60 text-emerald-400 bg-emerald-950/40' : 'border-zinc-700 text-zinc-400 bg-zinc-900'">
                  {{ t(`ma.types.${project.project_type}`) }}
                </span>
              </div>
              <p v-if="project.client_contact" class="text-[11px] text-zinc-500 mt-0.5 font-mono truncate">{{ project.client_contact }}</p>
            </div>
            <div v-if="contractState" class="text-right shrink-0">
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold border"
                :class="contractState.class">{{ contractState.label }}</span>
              <p v-if="maDaysLeft !== null" class="text-[10px] text-zinc-500 mt-1 font-mono">
                {{ project.ma_end_date ? `${formatLocaleDate(project.ma_end_date, 'short')} · ` : '' }}{{ t('ma.daysLeft', { n: String(maDaysLeft) }) }}
              </p>
            </div>
          </div>

          <!-- contract period bar -->
          <div v-if="project.ma_start_date && project.ma_end_date">
            <div class="flex items-center justify-between text-[10px] font-mono text-zinc-500 mb-1">
              <span>{{ formatLocaleDate(project.ma_start_date, 'short') }}</span>
              <span>{{ formatLocaleDate(project.ma_end_date, 'short') }}</span>
            </div>
            <div class="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
              <div class="h-full rounded-full transition-all" :class="contractState?.bar || 'bg-zinc-600'" :style="{ width: `${contractProgress}%` }" />
            </div>
          </div>

          <!-- SLA grid -->
          <div v-if="hasSla" class="grid grid-cols-2 gap-2 text-[11px]">
            <div v-if="project.sla_details?.uptime_target" class="p-2 rounded bg-zinc-900/60 border border-zinc-800/60">
              <p class="text-[9px] font-mono uppercase text-zinc-500">{{ t('ma.sla.uptime') }}</p>
              <p class="text-zinc-200 font-mono mt-0.5">{{ project.sla_details.uptime_target }}</p>
            </div>
            <div v-if="project.sla_details?.response_time" class="p-2 rounded bg-zinc-900/60 border border-zinc-800/60">
              <p class="text-[9px] font-mono uppercase text-zinc-500">{{ t('ma.sla.response') }}</p>
              <p class="text-zinc-200 font-mono mt-0.5">{{ project.sla_details.response_time }}</p>
            </div>
            <div v-if="project.sla_details?.backup_policy" class="p-2 rounded bg-zinc-900/60 border border-zinc-800/60">
              <p class="text-[9px] font-mono uppercase text-zinc-500">{{ t('ma.sla.backup') }}</p>
              <p class="text-zinc-200 font-mono mt-0.5">{{ project.sla_details.backup_policy }}</p>
            </div>
            <div v-if="project.sla_details?.monthly_hours_quota" class="p-2 rounded bg-zinc-900/60 border border-zinc-800/60">
              <p class="text-[9px] font-mono uppercase text-zinc-500">{{ t('ma.sla.quota') }}</p>
              <p class="text-zinc-200 font-mono mt-0.5">{{ project.sla_details.monthly_hours_quota }}</p>
            </div>
          </div>

          <!-- MA fee summary -->
          <div class="flex items-center justify-between p-2.5 rounded-md bg-zinc-900/60 border border-zinc-800/60">
            <div class="flex items-center gap-2 text-[11px] text-zinc-400">
              <Banknote class="w-3.5 h-3.5 text-emerald-400" />
              <span>{{ t('ma.feePerCycle') }}</span>
            </div>
            <div class="text-right">
              <span class="text-sm font-semibold font-mono text-zinc-100">{{ currencySymbol }}{{ fmt(project.ma_amount) }}</span>
              <span class="text-[10px] text-zinc-500 font-mono ml-1.5">/ {{ cycleLabel(project.ma_billing_cycle) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Project Net Margin & Cashflow Bridge -->
      <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
        <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center gap-2">
          <Scale class="w-3.5 h-3.5 text-amber-400" />
          <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('ma.economicsTitle') }}</h3>
        </div>

        <div class="p-5 space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <div class="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/40">
              <p class="text-[9px] font-mono uppercase text-emerald-500/90">{{ t('ma.revenue') }}</p>
              <p class="text-base font-semibold font-mono text-emerald-400 mt-1 tabular-nums">{{ currencySymbol }}{{ fmt(eco?.monthly_ma_inflow) }}</p>
              <p class="text-[10px] font-mono text-zinc-500 mt-0.5">{{ t('ma.perMonth') }} · {{ t('ma.received') }} {{ currencySymbol }}{{ fmt(eco?.realized_inflow) }}</p>
            </div>
            <div class="p-3 rounded-lg bg-rose-950/20 border border-rose-900/40">
              <p class="text-[9px] font-mono uppercase text-rose-500/90">{{ t('ma.infraCost') }}</p>
              <p class="text-base font-semibold font-mono text-rose-400 mt-1 tabular-nums">{{ currencySymbol }}{{ fmt(eco?.monthly_infra_outflow) }}</p>
              <p class="text-[10px] font-mono text-zinc-500 mt-0.5">{{ t('ma.perMonth') }} · {{ t('ma.selfFunded') }}</p>
              <p class="text-[9px] font-mono text-zinc-600 mt-1">
                {{ t('infra.econServers') }}: ฿{{ fmt(eco?.monthly_server_outflow) }} ·
                {{ t('infra.econServices') }}: ฿{{ fmt(eco?.monthly_service_outflow) }}
                <span v-if="(eco?.shared_assets_count || 0) > 0" class="text-amber-500/90"> · {{ t('infra.proRataActive') }}</span>
              </p>
            </div>
          </div>

          <div class="p-3.5 rounded-lg border" :class="marginPositive ? 'border-emerald-800/50 bg-emerald-950/25' : 'border-rose-800/50 bg-rose-950/25'">
            <div class="flex items-center justify-between">
              <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-400">{{ t('ma.netMargin') }}</p>
              <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold"
                :class="marginPositive ? 'text-emerald-400 bg-emerald-950/60' : 'text-rose-400 bg-rose-950/60'">
                {{ fmt(eco?.margin_pct) }}%
              </span>
            </div>
            <div class="flex items-baseline gap-4 mt-1.5">
              <div>
                <p class="text-[9px] font-mono text-zinc-500">{{ t('ma.projectedMonthly') }}</p>
                <p class="text-lg font-semibold font-mono tabular-nums" :class="marginPositive ? 'text-emerald-400' : 'text-rose-400'">
                  {{ currencySymbol }}{{ fmt(eco?.projected_monthly_margin) }}
                </p>
              </div>
              <div>
                <p class="text-[9px] font-mono text-zinc-500">{{ t('ma.realizedNet') }}</p>
                <p class="text-sm font-semibold font-mono text-zinc-300 tabular-nums">{{ currencySymbol }}{{ fmt(eco?.realized_net_margin) }}</p>
              </div>
            </div>
          </div>

          <p class="text-[10px] font-mono text-zinc-500 leading-relaxed">
            {{ t('ma.bridgeHint') }}
          </p>
        </div>
      </div>
    </div>

    <!-- ================= Zone 2: Server & Infrastructure Fleet ================= -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="px-3.5 sm:px-5 py-3.5 border-b border-zinc-800/80 flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <Server class="w-3.5 h-3.5 text-zinc-400" />
          <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('infra.fleetTitle') }}</h3>
          <span class="text-[10px] font-mono text-zinc-500">{{ serverAssets.length }}</span>
        </div>
        <div class="flex items-center gap-1.5">
          <button
            type="button"
            @click="openLinkModal('server')"
            class="px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-zinc-300 text-[11px] font-medium transition-colors flex items-center gap-1.5"
          >
            <Link2 class="w-3 h-3" />
            {{ t('infra.linkServer') }}
          </button>
          <button
            type="button"
            @click="openAssetForm(null, 'server')"
            class="px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-[11px] font-semibold transition-colors flex items-center gap-1.5"
          >
            <Plus class="w-3 h-3" />
            {{ t('infra.addServer') }}
          </button>
        </div>
      </div>

      <div v-if="workspaceStore.isInfraLoading && assets.length === 0" class="p-4">
          <SkeletonLoader variant="cards" :count="2" />
        </div>

        <div v-else-if="serverAssets.length === 0" class="p-10 text-center">
        <Server class="w-7 h-7 text-zinc-600 mx-auto mb-2.5" />
        <p class="text-xs text-zinc-400">{{ t('infra.emptyFleet') }}</p>
        <p class="text-[11px] text-zinc-600 mt-1 font-mono">{{ t('infra.emptyFleetHint') }}</p>
      </div>

      <div v-else class="p-4 grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div
          v-for="asset in serverAssets"
          :key="asset.id"
          class="rounded-lg bg-zinc-950/60 border border-zinc-800/80 overflow-hidden hover:border-zinc-700/80 transition-colors"
        >
          <!-- Card header -->
          <div class="px-3.5 sm:px-4 py-3 border-b border-zinc-800/70 flex flex-wrap items-start justify-between gap-2">
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-semibold text-zinc-100 truncate">{{ asset.name }}</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border border-zinc-700 text-zinc-400 bg-zinc-900 shrink-0">
                  {{ t(`infra.types.${asset.asset_type}`) }}
                </span>
                <span v-if="asset.provider" class="text-[10px] font-mono text-zinc-500">{{ asset.provider }}</span>
              </div>
              <div class="flex items-center gap-2 mt-1.5 flex-wrap">
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold uppercase border"
                  :class="healthClass(asset.health_status)">
                  <span class="w-1.5 h-1.5 rounded-full" :class="healthDot(asset.health_status)" />
                  {{ asset.health_status }}
                </span>
                <span v-if="asset.is_shared" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold uppercase border border-amber-700/60 text-amber-400 bg-amber-950/40">
                  <Share2 class="w-2.5 h-2.5" />
                  {{ t('infra.sharedBadge', { n: String(asset.share_count || 1) }) }}
                </span>
                <span
                  v-for="lp in (asset.linked_projects || []).slice(0, 4)"
                  :key="lp.id"
                  class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono border border-zinc-700 bg-zinc-900 text-zinc-300"
                >
                  <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ backgroundColor: lp.color }" />
                  {{ lp.name }}
                </span>
                <span v-if="asset.last_telemetry?.uptime_human" class="text-[10px] font-mono text-zinc-500">
                  up {{ asset.last_telemetry.uptime_human }}
                </span>
                <span v-if="asset.next_billing_date && asset.billing_ownership !== 'CLIENT_DIRECT'" class="text-[10px] font-mono text-amber-500/90">
                  {{ t('infra.nextBill') }} {{ formatLocaleDate(asset.next_billing_date, 'short') }}
                </span>
                <span class="text-[10px] font-mono text-zinc-400">
                  <template v-if="asset.is_shared">
                    ฿{{ fmt(asset.allocated_cost_amount) }}/mo (1/{{ asset.share_count }} {{ t('infra.of') }} ฿{{ fmt(asset.cost_amount) }})
                  </template>
                  <template v-else>฿{{ fmt(asset.cost_amount) }}/{{ asset.billing_cycle?.slice(0, 1) === 'M' ? 'mo' : 'cycle' }}</template>
                </span>
                <span v-if="asset.expiry_date" class="text-[10px] font-mono text-rose-400/90">
                  {{ t('infra.expires') }} {{ formatLocaleDate(asset.expiry_date, 'short') }}
                </span>
              </div>
            </div>
            <div class="flex items-center gap-1 shrink-0 ml-auto sm:ml-0">
              <button
                v-if="asset.ip_address"
                type="button"
                @click="copyText(asset.ip_address, t('infra.ipCopied'))"
                class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors font-mono text-[10px]"
                :title="t('infra.copyIp')"
              >{{ asset.ip_address }}</button>
              <button
                type="button"
                @click="openAssetForm(asset)"
                class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
                :title="t('common.edit')"
              ><Pencil class="w-3 h-3" /></button>
              <button
                type="button"
                @click="confirmDeleteAsset = asset"
                class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors"
                :title="t('common.delete')"
              ><Trash2 class="w-3 h-3" /></button>
            </div>
          </div>

          <!-- Telemetry gauges -->
          <div class="px-4 py-3 space-y-2.5 border-b border-zinc-800/70">
            <div class="flex items-center justify-between text-[10px] font-mono">
              <span class="text-zinc-500 flex items-center gap-1.5">
                <Activity class="w-3 h-3" /> {{ t('infra.liveTelemetry') }}
              </span>
              <div class="flex items-center gap-2">
                <span v-if="asset.last_telemetry?.kernel" class="text-zinc-600 hidden sm:inline truncate max-w-[180px]">{{ asset.last_telemetry.kernel }}</span>
                <button
                  type="button"
                  @click="probe(asset)"
                  :disabled="probingId === asset.id"
                  class="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:border-zinc-600 transition-colors flex items-center gap-1 disabled:opacity-50"
                >
                  <Radar class="w-3 h-3" :class="{ 'animate-spin': probingId === asset.id }" />
                  {{ probingId === asset.id ? t('infra.probing') : t('infra.probe') }}
                </button>
              </div>
            </div>

            <template v-if="asset.last_telemetry && asset.last_telemetry.error === null && asset.last_telemetry.ram_total_mb">
              <GaugeBar :label="'CPU'" :pct="asset.last_telemetry.cpu_pct" :detail="`${asset.last_telemetry.load_avg?.toFixed(2) ?? '—'} load`" :threshold="asset.alert_cpu_threshold" />
              <GaugeBar
                :label="'RAM'"
                :pct="asset.last_telemetry.ram_pct"
                :detail="`${Math.round(asset.last_telemetry.ram_used_mb || 0)}/${Math.round(asset.last_telemetry.ram_total_mb || 0)} MB`"
                :threshold="asset.alert_ram_threshold"
              />
              <GaugeBar
                :label="t('infra.form.disk')"
                :pct="asset.last_telemetry.disk_pct"
                :detail="`${asset.last_telemetry.disk_used_gb ?? '—'}/${asset.last_telemetry.disk_total_gb ?? '—'} GB`"
                :threshold="asset.alert_disk_threshold"
              />
            </template>
            <p v-else-if="asset.last_telemetry?.error" class="text-[10px] font-mono text-rose-400/90 break-all">
              {{ asset.last_telemetry.error }}
            </p>
            <p v-else class="text-[10px] font-mono text-zinc-600">
              {{ asset.last_checked_at ? t('infra.lastCheck', { time: formatLocaleDate(asset.last_checked_at, 'datetime') }) : t('infra.neverProbed') }}
            </p>
          </div>

          <!-- Docker containers -->
          <div v-if="dockerContainers(asset).length > 0" class="px-4 py-3 border-b border-zinc-800/70">
            <button type="button" @click="expandedDocker[asset.id] = !expandedDocker[asset.id]"
              class="w-full flex items-center justify-between text-[10px] font-mono uppercase text-zinc-500 hover:text-zinc-300 transition-colors">
              <span class="flex items-center gap-1.5">
                <Container class="w-3 h-3" /> {{ t('infra.docker') }} ({{ dockerContainers(asset).length }})
              </span>
              <ChevronDown class="w-3.5 h-3.5 transition-transform" :class="{ 'rotate-180': expandedDocker[asset.id] }" />
            </button>

            <div v-if="expandedDocker[asset.id]" class="mt-2.5 space-y-1.5">
              <div
                v-for="c in dockerContainers(asset)"
                :key="c.ID || c.Names"
                class="flex items-center justify-between gap-2 px-2.5 py-2 rounded-md bg-zinc-900/60 border border-zinc-800/60"
              >
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="c.State === 'running' ? 'bg-emerald-400' : 'bg-zinc-600'" />
                    <span class="text-[11px] text-zinc-200 font-mono truncate">{{ c.Names }}</span>
                  </div>
                  <p class="text-[9px] font-mono text-zinc-500 truncate mt-0.5">{{ c.Image }} · {{ c.Status }}</p>
                </div>
                <div class="flex items-center gap-1 shrink-0">
                  <button v-if="c.State !== 'running'" type="button" @click="docker(asset, c, 'start')"
                    class="p-1 rounded bg-emerald-950/60 border border-emerald-900/60 text-emerald-400 hover:bg-emerald-900/40 transition-colors"
                    :title="t('infra.dockerStart')"><Play class="w-3 h-3" /></button>
                  <button v-else type="button" @click="docker(asset, c, 'stop')"
                    class="p-1 rounded bg-amber-950/60 border border-amber-900/60 text-amber-400 hover:bg-amber-900/40 transition-colors"
                    :title="t('infra.dockerStop')"><Square class="w-3 h-3" /></button>
                  <button type="button" @click="docker(asset, c, 'restart')"
                    class="p-1 rounded bg-sky-950/60 border border-sky-900/60 text-sky-400 hover:bg-sky-900/40 transition-colors"
                    :title="t('infra.dockerRestart')"><RotateCw class="w-3 h-3" /></button>
                  <button type="button" @click="docker(asset, c, 'logs')"
                    class="p-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
                    :title="t('infra.dockerLogs')"><FileText class="w-3 h-3" /></button>
                </div>
              </div>
            </div>
          </div>

          <!-- Action footer -->
          <div class="px-4 py-3 flex items-center gap-2 flex-wrap">
            <button
              type="button"
              :disabled="asset.ssh_auth_type === 'NONE' || !asset.ip_address"
              @click="terminalAsset = asset"
              class="px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-zinc-200 text-[11px] font-medium transition-colors flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <TerminalSquare class="w-3.5 h-3.5 text-emerald-400" />
              {{ t('infra.webTerminal') }}
            </button>
            <button
              type="button"
              :disabled="asset.ssh_auth_type === 'NONE' || !asset.ip_address"
              @click="runbookAsset = asset"
              class="px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-zinc-200 text-[11px] font-medium transition-colors flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Zap class="w-3.5 h-3.5 text-amber-400" />
              {{ t('infra.runbooks') }} ({{ runbookCount(asset.id) }})
            </button>
            <button
              v-if="asset.is_shared"
              type="button"
              @click="unlinkAsset(asset)"
              class="px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 hover:border-amber-600/60 text-zinc-400 hover:text-amber-400 text-[11px] font-medium transition-colors flex items-center gap-1.5"
            >
              <Share2 class="w-3.5 h-3.5" />
              {{ t('infra.unlinkFromProject') }}
            </button>
            <button
              v-if="asset.console_url"
              type="button"
              @click="copyText(`ssh ${asset.ssh_username}@${asset.ip_address} -p ${asset.ssh_port}`, t('infra.sshCopied'))"
              class="sm:ml-auto max-w-full px-2 py-1 rounded bg-zinc-950/80 border border-zinc-800/80 text-[10px] font-mono text-zinc-500 hover:text-zinc-200 flex items-center gap-1 transition-colors min-w-0"
            >
              <Copy class="w-2.5 h-2.5 shrink-0" /> <span class="truncate">ssh {{ asset.ssh_username }}@{{ asset.ip_address || '—' }} -p {{ asset.ssh_port }}</span>
            </button>
            <a
              v-if="asset.console_url"
              :href="asset.console_url"
              target="_blank"
              rel="noopener noreferrer"
              class="px-2 py-1 rounded text-[10px] font-mono text-zinc-500 hover:text-zinc-200 transition-colors flex items-center gap-1"
            >
              <ExternalLink class="w-3 h-3" /> {{ t('infra.console') }}
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- ================= Zone 3: Project Subscriptions & Cloud Services ================= -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="px-3.5 sm:px-5 py-3.5 border-b border-zinc-800/80 flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <CreditCard class="w-3.5 h-3.5 text-sky-400" />
          <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('infra.servicesTitle') }}</h3>
          <span class="text-[10px] font-mono text-zinc-500">{{ serviceAssets.length }}</span>
        </div>
        <div class="flex items-center gap-1.5">
          <button
            type="button"
            @click="openLinkModal('service')"
            class="px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-zinc-300 text-[11px] font-medium transition-colors flex items-center gap-1.5"
          >
            <Link2 class="w-3 h-3" />
            {{ t('infra.linkService') }}
          </button>
          <button
            type="button"
            @click="openAssetForm(null, 'service')"
            class="px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-[11px] font-semibold transition-colors flex items-center gap-1.5"
          >
            <Plus class="w-3 h-3" />
            {{ t('infra.addService') }}
          </button>
        </div>
      </div>

      <div v-if="serviceAssets.length === 0" class="p-8 text-center">
        <CreditCard class="w-6 h-6 text-zinc-600 mx-auto mb-2" />
        <p class="text-xs text-zinc-500">{{ t('infra.emptyServices') }}</p>
        <p class="text-[11px] text-zinc-600 mt-1 font-mono">{{ t('infra.emptyServicesHint') }}</p>
      </div>

      <div v-else class="divide-y divide-zinc-800/60">
        <div
          v-for="asset in serviceAssets"
          :key="asset.id"
          class="px-3.5 sm:px-5 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-zinc-900/40 transition-colors"
        >
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <div class="w-7 h-7 rounded-md bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0">
              <component :is="serviceIcon(asset.asset_type)" class="w-3.5 h-3.5 text-sky-400" />
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs font-medium text-zinc-100 truncate">{{ asset.name }}</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border border-zinc-700 text-zinc-400 bg-zinc-900 shrink-0">
                  {{ t(`infra.types.${asset.asset_type}`) }}
                </span>
                <span v-if="asset.is_shared" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold uppercase border border-amber-700/60 text-amber-400 bg-amber-950/40 shrink-0">
                  <Share2 class="w-2.5 h-2.5" />
                  {{ t('infra.sharedBadge', { n: String(asset.share_count || 1) }) }}
                </span>
              </div>
              <p class="text-[10px] font-mono text-zinc-500 truncate mt-0.5">
                <span v-if="asset.provider">{{ asset.provider }}</span>
                <span v-if="asset.primary_domain"> · {{ asset.primary_domain }}</span>
                <span v-if="asset.next_billing_date"> · {{ t('infra.nextBill') }} {{ formatLocaleDate(asset.next_billing_date, 'short') }}</span>
                <span v-else-if="asset.expiry_date"> · {{ t('infra.expires') }} {{ formatLocaleDate(asset.expiry_date, 'short') }}</span>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <div class="text-right mr-1">
              <p class="text-[11px] font-mono text-zinc-200">
                <template v-if="asset.is_shared">฿{{ fmt(asset.allocated_cost_amount) }}<span class="text-zinc-600">/{{ t('infra.proRataShort') }}</span></template>
                <template v-else>฿{{ fmt(asset.cost_amount) }}/{{ asset.billing_cycle === 'YEARLY' ? 'yr' : 'mo' }}</template>
              </p>
              <p class="text-[9px] font-mono text-zinc-600">
                {{ t(`infra.ownership.${asset.billing_ownership}`) }}
                <span v-if="asset.sync_to_radar" class="text-emerald-500/80">· Radar</span>
              </p>
            </div>
            <button
              v-if="asset.is_shared"
              type="button"
              @click="unlinkAsset(asset)"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-amber-400 transition-colors"
              :title="t('infra.unlinkFromProject')"
            ><Share2 class="w-3.5 h-3.5" /></button>
            <a
              v-if="asset.console_url"
              :href="asset.console_url"
              target="_blank"
              rel="noopener noreferrer"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
              :title="t('infra.console')"
            ><ExternalLink class="w-3.5 h-3.5" /></a>
            <button
              type="button"
              @click="openAssetForm(asset, 'service')"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
              :title="t('common.edit')"
            ><Pencil class="w-3.5 h-3.5" /></button>
            <button
              type="button"
              @click="confirmDeleteAsset = asset"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors"
              :title="t('common.delete')"
            ><Trash2 class="w-3.5 h-3.5" /></button>
          </div>
        </div>
      </div>
    </div>

    <!-- ================= Zone 4: Encrypted Credentials Vault ================= -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <ShieldCheck class="w-3.5 h-3.5 text-emerald-400" />
          <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('cred.title') }}</h3>
        </div>
        <button
          type="button"
          @click="openCredForm(null)"
          class="px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-[11px] font-semibold transition-colors flex items-center gap-1.5"
        >
          <Plus class="w-3 h-3" />
          {{ t('cred.add') }}
        </button>
      </div>

      <div v-if="workspaceStore.isInfraLoading && credentials.length === 0" class="p-4">
          <SkeletonLoader variant="list" :count="2" />
        </div>

        <div v-else-if="credentials.length === 0" class="p-8 text-center">
        <KeyRound class="w-6 h-6 text-zinc-600 mx-auto mb-2" />
        <p class="text-xs text-zinc-500">{{ t('cred.empty') }}</p>
      </div>

      <div v-else class="divide-y divide-zinc-800/60">
        <div
          v-for="cred in credentials"
          :key="cred.id"
          class="px-3.5 sm:px-5 py-3 space-y-2 hover:bg-zinc-900/40 transition-colors"
        >
          <div class="flex items-start sm:items-center justify-between gap-2">
          <div class="min-w-0 flex-1 flex items-center gap-3">
            <div class="w-7 h-7 rounded-md bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0">
              <component :is="credIcon(cred.category)" class="w-3.5 h-3.5 text-zinc-400" />
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-xs font-medium text-zinc-100 truncate">{{ cred.title }}</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border border-zinc-700 text-zinc-500 shrink-0">
                  {{ t(`cred.categories.${cred.category}`) }}
                </span>
              </div>
              <p class="text-[10px] font-mono text-zinc-500 truncate mt-0.5">
                <span v-if="cred.username">{{ cred.username }}@</span>{{ cred.host_or_url || assetName(cred.asset) }}
                <span v-if="cred.has_secret && !revealed[cred.id]" class="text-zinc-600"> · ••••••••••••</span>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-1 shrink-0">
            <button
              v-if="cred.has_secret && !revealed[cred.id]"
              type="button"
              @click="reveal(cred)"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-amber-400 transition-colors"
              :title="t('cred.reveal')"
            ><Eye class="w-3.5 h-3.5" /></button>
            <button
              v-if="revealed[cred.id]"
              type="button"
              @click="copyText(revealed[cred.id], t('cred.copied'))"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-emerald-400 transition-colors"
              :title="t('cred.copySecret')"
            ><Copy class="w-3.5 h-3.5" /></button>
            <button
              type="button"
              @click="openCredForm(cred)"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
              :title="t('common.edit')"
            ><Pencil class="w-3.5 h-3.5" /></button>
            <button
              type="button"
              @click="confirmDeleteCred = cred"
              class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors"
              :title="t('common.delete')"
            ><Trash2 class="w-3.5 h-3.5" /></button>
          </div>
          </div>

          <pre
            v-if="revealed[cred.id]"
            class="p-2.5 rounded-md bg-zinc-950 border border-zinc-800 text-[11px] font-mono text-amber-300 break-all whitespace-pre-wrap max-h-40 overflow-y-auto select-all"
          >{{ revealed[cred.id] }}</pre>
        </div>
      </div>
    </div>

    <!-- ================= Modals ================= -->
    <MaBillingEditModal :is-open="maModalOpen" :project="project" @close="maModalOpen = false" @saved="reloadProject" />
    <InfraAssetFormModal
      :is-open="assetFormOpen"
      :project-id="project.id"
      :asset="editingAsset"
      :default-mode="assetFormMode"
      :projects="linkableProjects"
      @close="assetFormOpen = false"
      @saved="reloadFleet"
    />
    <CredentialFormModal
      :is-open="credFormOpen"
      :project-id="project.id"
      :credential="editingCredential"
      :assets="assets"
      @close="credFormOpen = false"
      @saved="reloadCredentials"
    />
    <SshTerminalModal
      v-if="terminalAsset"
      :is-open="!!terminalAsset"
      :asset="terminalAsset"
      :runbooks="runbooksByAsset(terminalAsset.id)"
      @close="terminalAsset = null"
    />
    <ServerRunbooksModal
      v-if="runbookAsset"
      :is-open="!!runbookAsset"
      :asset="runbookAsset"
      :project-id="project.id"
      @close="runbookAsset = null"
    />

    <!-- Docker logs viewer -->
    <Teleport to="body">
      <div v-if="logsViewer.open" class="fixed inset-0 z-[68] flex items-center justify-center p-4 font-sans">
        <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" @click="logsViewer.open = false" />
        <div class="relative w-full max-w-3xl h-[70vh] flex flex-col rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden shadow-2xl">
          <div class="px-4 py-3 border-b border-zinc-800 flex items-center justify-between shrink-0">
            <div class="flex items-center gap-2">
              <FileText class="w-4 h-4 text-sky-400" />
              <span class="text-xs font-mono text-zinc-200">{{ logsViewer.title }}</span>
            </div>
            <button type="button" @click="logsViewer.open = false" class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-100 transition-colors">
              <X class="w-4 h-4" />
            </button>
          </div>
          <pre class="flex-1 overflow-auto p-4 bg-[#0d0f14] text-[11px] font-mono text-zinc-300 whitespace-pre-wrap break-all m-0">{{ logsViewer.content || t('infra.noLogs') }}</pre>
        </div>
      </div>
    </Teleport>

    <!-- Link Existing Server / Service modal -->
    <Teleport to="body">
      <div v-if="linkModal.open" class="fixed inset-0 z-[66] flex items-center justify-center p-4 font-sans">
        <div class="absolute inset-0 bg-black/75 backdrop-blur-sm" @click="linkModal.open = false" />

        <div class="relative w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden">
          <div class="flex items-center justify-between px-5 py-3.5 border-b border-zinc-800">
            <div class="flex items-center gap-2">
              <Link2 class="w-4 h-4 text-sky-400" />
              <h3 class="text-sm font-semibold text-zinc-100">
                {{ linkModal.mode === 'server' ? t('infra.linkServer') : t('infra.linkService') }}
              </h3>
            </div>
            <button type="button" @click="linkModal.open = false" class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-100 transition-colors">
              <X class="w-4 h-4" />
            </button>
          </div>
          <div class="p-4 max-h-[60dvh] overflow-y-auto space-y-1.5">
            <p v-if="linkModal.loading" class="text-xs text-zinc-500 font-mono text-center py-6">{{ t('common.loading') }}</p>
            <p v-else-if="linkModal.candidates.length === 0" class="text-xs text-zinc-500 font-mono text-center py-6">{{ t('infra.noLinkCandidates') }}</p>
            <button
              v-for="candidate in linkModal.candidates"
              :key="candidate.id"
              type="button"
              @click="linkAsset(candidate)"
              class="w-full text-left p-3 rounded-lg bg-zinc-900/50 border border-zinc-800 hover:border-zinc-600 transition-colors flex items-center justify-between gap-3"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-medium text-zinc-100 truncate">{{ candidate.name }}</span>
                  <span class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border border-zinc-700 text-zinc-500 shrink-0">
                    {{ t(`infra.types.${candidate.asset_type}`) }}
                  </span>
                </div>
                <p class="text-[10px] font-mono text-zinc-500 truncate mt-0.5">
                  {{ candidate.project_name || t('infra.noPrimaryProject') }}
                  <span v-if="candidate.is_shared"> · {{ t('infra.sharedBadge', { n: String(candidate.share_count || 1) }) }}</span>
                </p>
              </div>
              <div class="text-right shrink-0">
                <p class="text-[11px] font-mono text-zinc-300">฿{{ fmt(candidate.cost_amount) }}</p>
                <p class="text-[9px] font-mono text-emerald-400/80 flex items-center gap-1 justify-end"><Plus class="w-2.5 h-2.5" /> {{ t('infra.linkAction') }}</p>
              </div>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <ConfirmModal
      :is-open="!!confirmDeleteAsset"
      :title="t('infra.deleteTitle')"
      :message="t('infra.deleteMessage', { name: confirmDeleteAsset?.name || '' })"
      :confirm-text="t('common.delete')"
      :cancel-text="t('common.cancel')"
      @confirm="doDeleteAsset"
      @cancel="confirmDeleteAsset = null"
    />
    <ConfirmModal
      :is-open="!!confirmDeleteCred"
      :title="t('cred.deleteTitle')"
      :message="t('cred.deleteMessage', { title: confirmDeleteCred?.title || '' })"
      :confirm-text="t('common.delete')"
      :cancel-text="t('common.cancel')"
      @confirm="doDeleteCred"
      @cancel="confirmDeleteCred = null"
    />
  </div>
</template>

<script setup lang="ts">
import SkeletonLoader from '../common/SkeletonLoader.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import {
  FileSignature, Pencil, Banknote, Scale, Server, Plus, Trash2, Activity, Radar,
  Container, ChevronDown, Play, Square, RotateCw, FileText, TerminalSquare, Zap,
  Share2, Link2, CreditCard, Globe, Mail, HardDrive, Code2,
  Copy, ExternalLink, ShieldCheck, KeyRound, Eye, X,
  Database, Lock
} from 'lucide-vue-next'
import { t, formatLocaleDate } from '../../i18n'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import ConfirmModal from '../common/ConfirmModal.vue'
import MaBillingEditModal from './MaBillingEditModal.vue'
import InfraAssetFormModal from './InfraAssetFormModal.vue'
import CredentialFormModal from './CredentialFormModal.vue'
import SshTerminalModal from './SshTerminalModal.vue'
import ServerRunbooksModal from './ServerRunbooksModal.vue'
import GaugeBar from './GaugeBar.vue'
import type {
  WorkspaceProject, InfrastructureAsset, ServerCredential, ServerRunbook,
  DockerContainerInfo, InfraHealthStatus
} from '../../types/workspace'

const props = defineProps<{ project: WorkspaceProject }>()

const emit = defineEmits<{ (e: 'project-updated'): void }>()

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const assets = computed(() => workspaceStore.infraAssets)
const credentials = computed(() => workspaceStore.serverCredentials)
const allRunbooks = ref<ServerRunbook[]>([])

const maModalOpen = ref(false)
const assetFormOpen = ref(false)
const editingAsset = ref<InfrastructureAsset | null>(null)
const credFormOpen = ref(false)
const editingCredential = ref<ServerCredential | null>(null)
const terminalAsset = ref<InfrastructureAsset | null>(null)
const runbookAsset = ref<InfrastructureAsset | null>(null)
const confirmDeleteAsset = ref<InfrastructureAsset | null>(null)
const confirmDeleteCred = ref<ServerCredential | null>(null)
const probingId = ref<string | null>(null)
const revealed = ref<Record<string, string>>({})
const expandedDocker = reactive<Record<string, boolean>>({})
const logsViewer = reactive({ open: false, title: '', content: '' })

const COMPUTE_TYPES: string[] = ['VPS', 'DEDICATED', 'MANAGED_DB', 'PAAS']

const serverAssets = computed(() =>
  assets.value.filter(a => COMPUTE_TYPES.includes(a.asset_type))
)
const serviceAssets = computed(() =>
  assets.value.filter(a => !COMPUTE_TYPES.includes(a.asset_type))
)

type LinkMode = 'server' | 'service'
const linkModal = reactive({
  open: false,
  mode: 'server' as LinkMode,
  loading: false,
  candidates: [] as InfrastructureAsset[]
})

function openLinkModal(mode: LinkMode) {
  linkModal.open = true
  linkModal.mode = mode
  linkModal.loading = true
  linkModal.candidates = []
  workspaceStore.fetchAllUserInfraAssets().then(all => {
    linkModal.candidates = all.filter(a => {
      const isCompute = COMPUTE_TYPES.includes(a.asset_type)
      const bucketOk = mode === 'server' ? isCompute : !isCompute
      if (!bucketOk) return false
      const alreadyLinked = (a.linked_projects || []).some(
        lp => lp.id === props.project.id
      ) || a.project === props.project.id
      return !alreadyLinked
    })
  }).finally(() => {
    linkModal.loading = false
  })
}

async function linkAsset(asset: InfrastructureAsset) {
  try {
    await workspaceStore.linkInfraAssetProject(asset.id, props.project.id)
    toast.success(t('infra.linkSuccess'))
    linkModal.open = false
    await reloadFleet()
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('infra.linkFailed'))
  }
}

async function unlinkAsset(asset: InfrastructureAsset) {
  try {
    await workspaceStore.unlinkInfraAssetProject(asset.id, props.project.id)
    toast.success(t('infra.unlinkSuccess'))
    await reloadFleet()
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('infra.unlinkFailed'))
  }
}

const eco = computed(() => props.project.economics || null)

const linkableProjects = computed(() => {
  const own = workspaceStore.projects.map(p => ({ id: p.id, name: p.name, color: p.color }))
  const seen = new Set(own.map(p => p.id))
  for (const a of assets.value) {
    for (const lp of a.linked_projects || []) {
      if (!seen.has(lp.id)) {
        own.push(lp)
        seen.add(lp.id)
      }
    }
  }
  return own
})
const currencySymbol = computed(() => (props.project.ma_currency === 'USD' ? '$' : '฿'))
const marginPositive = computed(() => Number(eco.value?.projected_monthly_margin || 0) >= 0)
const hasSla = computed(() => {
  const s = props.project.sla_details || {}
  return !!(s.uptime_target || s.response_time || s.backup_policy || s.monthly_hours_quota)
})

const maDaysLeft = computed(() => {
  if (!props.project.ma_end_date) return null
  const diff = new Date(props.project.ma_end_date).getTime() - new Date(new Date().toDateString()).getTime()
  return Math.ceil(diff / 86400000)
})

const contractState = computed(() => {
  if (!props.project.ma_end_date) return null
  const d = maDaysLeft.value ?? 0
  if (d < 0) return { label: t('ma.state.expired'), class: 'border-rose-800/60 text-rose-400 bg-rose-950/40', bar: 'bg-rose-500' }
  if (d <= 14) return { label: t('ma.state.expiringSoon'), class: 'border-amber-800/60 text-amber-400 bg-amber-950/40', bar: 'bg-amber-500' }
  if (props.project.project_type === 'MA_CONTRACT' || props.project.ma_start_date)
    return { label: t('ma.state.active'), class: 'border-emerald-800/60 text-emerald-400 bg-emerald-950/40', bar: 'bg-emerald-500' }
  return null
})

const contractProgress = computed(() => {
  const { ma_start_date, ma_end_date } = props.project
  if (!ma_start_date || !ma_end_date) return 0
  const start = new Date(ma_start_date).getTime()
  const end = new Date(ma_end_date).getTime()
  const now = Date.now()
  if (end <= start) return 100
  return Math.min(100, Math.max(0, ((now - start) / (end - start)) * 100))
})

function fmt(value: string | number | null | undefined): string {
  const n = Number(value || 0)
  return n.toLocaleString(n % 1 === 0 ? 'en-US' : 'en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function cycleLabel(cycle: string): string {
  return t(`ma.cycles.${cycle}`)
}

function healthClass(status: InfraHealthStatus): string {
  switch (status) {
    case 'ONLINE': return 'border-emerald-800/60 text-emerald-400 bg-emerald-950/40'
    case 'WARNING': return 'border-amber-800/60 text-amber-400 bg-amber-950/40'
    case 'OFFLINE': return 'border-rose-800/60 text-rose-400 bg-rose-950/40'
    default: return 'border-zinc-700 text-zinc-400 bg-zinc-900'
  }
}

function healthDot(status: InfraHealthStatus): string {
  switch (status) {
    case 'ONLINE': return 'bg-emerald-400'
    case 'WARNING': return 'bg-amber-400'
    case 'OFFLINE': return 'bg-rose-400'
    default: return 'bg-zinc-500'
  }
}

function dockerContainers(asset: InfrastructureAsset): DockerContainerInfo[] {
  const tel = asset.last_telemetry as any
  return Array.isArray(tel?.containers) ? tel.containers : []
}

function runbooksByAsset(assetId: string): ServerRunbook[] {
  return allRunbooks.value.filter(rb => rb.asset === assetId)
}

function runbookCount(assetId: string): number {
  return runbooksByAsset(assetId).length
}

function assetName(assetId: string | null): string {
  if (!assetId) return ''
  return assets.value.find(a => a.id === assetId)?.name || ''
}

function serviceIcon(assetType: string) {
  switch (assetType) {
    case 'DOMAIN': return Globe
    case 'EMAIL_SMTP': return Mail
    case 'STORAGE': return HardDrive
    case 'API_SERVICE': return Code2
    case 'LICENSE': return FileText
    default: return CreditCard
  }
}

function credIcon(category: string) {
  switch (category) {
    case 'DATABASE': return Database
    case 'API_KEY': return Code2
    case 'ADMIN_PANEL': return Lock
    case 'SSH': return TerminalSquare
    case 'ENV_VARS': return FileText
    default: return KeyRound
  }
}

const assetFormMode = ref<'server' | 'service'>('server')

function openAssetForm(asset: InfrastructureAsset | null, mode: 'server' | 'service' = 'server') {
  editingAsset.value = asset
  assetFormMode.value = mode
  assetFormOpen.value = true
}

function openCredForm(cred: ServerCredential | null) {
  editingCredential.value = cred
  credFormOpen.value = true
}

async function copyText(text: string, successMsg: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success(successMsg)
  } catch {
    toast.error(t('infra.copyFailed'))
  }
}

async function probe(asset: InfrastructureAsset) {
  probingId.value = asset.id
  try {
    const res = await workspaceStore.probeInfraAsset(asset.id)
    if (res.health_status === 'ONLINE') toast.success(t('infra.probeOnline'))
    else if (res.health_status === 'WARNING') toast.error(t('infra.probeWarning'))
    else toast.error(t('infra.probeOffline'))
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('infra.probeFailed'))
  } finally {
    probingId.value = null
  }
}

async function docker(asset: InfrastructureAsset, container: DockerContainerInfo, action: string) {
  const containerId = String(container.ID || container.Names || '')
  try {
    const res = await workspaceStore.dockerAction(asset.id, containerId, action, 100)
    if (action === 'logs') {
      logsViewer.title = `docker logs · ${container.Names} @ ${asset.name}`
      logsViewer.content = res.output || res.stdout || ''
      logsViewer.open = true
    } else {
      toast.success(t(`infra.dockerDone.${action}`))
      await probe(asset)
    }
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('infra.dockerFailed'))
  }
}

async function reveal(cred: ServerCredential) {
  try {
    const secret = await workspaceStore.revealServerCredential(cred.id)
    revealed.value[cred.id] = secret
    window.setTimeout(() => { delete revealed.value[cred.id] }, 30000)
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('cred.revealFailed'))
  }
}

async function doDeleteAsset() {
  if (!confirmDeleteAsset.value) return
  try {
    await workspaceStore.deleteInfraAsset(confirmDeleteAsset.value.id)
    toast.success(t('infra.deleted'))
    confirmDeleteAsset.value = null
    await reloadFleet()
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('infra.deleteFailed'))
  }
}

async function doDeleteCred() {
  if (!confirmDeleteCred.value) return
  try {
    await workspaceStore.deleteServerCredential(confirmDeleteCred.value.id)
    toast.success(t('cred.deleted'))
    confirmDeleteCred.value = null
    await reloadCredentials()
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('cred.deleteFailed'))
  }
}

async function reloadFleet() {
  try {
    await workspaceStore.fetchInfraAssets(props.project.id)
    await workspaceStore.fetchServerRunbooks(props.project.id).then(rbs => { allRunbooks.value = rbs })
    // Server add/edit/delete changes economics (infra cost, net margin) -
    // ask the parent to refetch the project so the numbers refresh now.
    emit('project-updated')
  } catch { /* toast already raised by caller paths */ }
}

async function reloadCredentials() {
  try {
    await workspaceStore.fetchServerCredentials(props.project.id)
  } catch { /* noop */ }
}

function reloadProject() {
  emit('project-updated')
}

onMounted(() => {
  reloadFleet()
  reloadCredentials()
  // Projects list powers the Shared Projects picker in the asset form
  if (workspaceStore.projects.length === 0) {
    workspaceStore.fetchProjects().catch(() => { /* picker stays empty */ })
  }
})
</script>
