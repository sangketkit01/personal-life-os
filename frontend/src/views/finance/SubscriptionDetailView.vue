<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans pb-12">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2 mb-2">
          <RouterLink
            to="/finance/subscriptions"
            class="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft class="w-3.5 h-3.5" />
            <span>Subscriptions & Trials</span>
          </RouterLink>
          <span class="text-zinc-600">/</span>
          <span class="text-xs font-mono text-zinc-300">{{ subscription?.title || 'Dossier' }}</span>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">
            {{ subscription?.title || 'Loading Service...' }}
          </h1>
          <span
            v-if="subscription?.metadata?.plan_name"
            class="text-[10px] font-mono px-2 py-0.5 rounded border border-zinc-800 bg-zinc-900 text-zinc-300"
          >
            {{ subscription.metadata.plan_name }}
          </span>
          <span
            v-if="subscription?.summary?.is_terminated || subscription?.metadata?.termination?.status === 'TERMINATED'"
            class="text-[10px] font-mono px-2 py-0.5 rounded border font-semibold"
            :class="subscription.status === 'ACTIVE' ? 'border-amber-800/60 text-amber-400 bg-amber-950/40' : 'border-zinc-700 text-zinc-500 bg-zinc-900'"
          >
            {{ subscription?.summary?.termination_label || (subscription?.status === 'ACTIVE' ? 'สิ้นสุดแล้ว · มีบิลค้าง' : 'สิ้นสุดแล้ว') }}
          </span>
          <span
            v-else
            class="text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-semibold"
            :class="getStatusBadgeClass(subscription?.status)"
          >
            {{ subscription?.status || 'ACTIVE' }}
          </span>
          <span
            v-if="subscription?.type === 'FREE_TRIAL'"
            class="text-[10px] font-mono uppercase px-2 py-0.5 rounded border bg-rose-500/10 text-rose-400 border-rose-500/20 font-semibold"
          >
            FREE TRIAL WATCHDOG
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Detailed subscription lifecycle dossier, automated billing rollover, and cancellation guide
        </p>
      </div>

      <!-- Action Buttons -->
      <div class="flex flex-wrap items-center gap-2 self-start sm:self-auto">
        <!-- Direct Cancel Web Link -->
        <a
          v-if="subscription?.metadata?.cancel_url"
          :href="subscription.metadata.cancel_url"
          target="_blank"
          rel="noopener noreferrer"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <ExternalLink class="w-3.5 h-3.5 text-zinc-400" />
          <span>Cancellation URL</span>
        </a>

        <!-- Mark Trial Cancelled (if FREE_TRIAL and not cancelled) -->
        <button
          v-if="subscription?.type === 'FREE_TRIAL' && subscription?.status !== 'CANCELLED'"
          @click="handleCancelTrial"
          :disabled="isActionLoading"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <ShieldAlert class="w-3.5 h-3.5 text-zinc-400" />
          <span>Mark Cancelled</span>
        </button>

        <!-- Convert Free Trial to Recurring Subscription -->
        <button
          v-if="subscription?.type === 'FREE_TRIAL'"
          @click="showConvertModal = true"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-200 text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <Repeat class="w-3.5 h-3.5 text-zinc-400" />
          <span>Keep & Convert</span>
        </button>

        <!-- Record Renewal / Pay Bill -->
        <button
          v-if="subscription?.status === 'ACTIVE'"
          @click="showPayModal = true"
          type="button"
          class="px-3.5 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
          :class="subscription?.summary?.is_terminated
            ? 'bg-amber-500 hover:bg-amber-400 text-zinc-950 font-bold'
            : (subscription?.metadata?.is_itemized && (subscription?.summary?.pending_dynamic_count ?? 0) > 0
              ? 'bg-zinc-100 hover:bg-white text-zinc-950 border border-amber-300/40'
              : 'bg-zinc-100 hover:bg-white text-zinc-950')"
        >
          <Receipt class="w-3.5 h-3.5" />
          <span>{{ payButtonLabel }}</span>
        </button>

        <!-- Terminate Subscription -->
        <button
          v-if="subscription?.type === 'SUBSCRIPTION' && subscription?.status === 'ACTIVE' && !subscription?.summary?.is_terminated && !isWorkspace"
          @click="showTerminateModal = true"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-amber-900/50 text-amber-400 hover:text-amber-300 text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <XCircle class="w-3.5 h-3.5" />
          <span>ยุติรายการประจำ</span>
        </button>

        <!-- Edit Subscription / Free Trial -->
        <button
          @click="showEditModal = true"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <Edit2 class="w-3.5 h-3.5 text-zinc-400" />
          <span>Edit</span>
        </button>

        <!-- Delete / Retire -->
        <button
          @click="confirmDelete"
          type="button"
          class="p-1.5 rounded-md hover:bg-zinc-900 text-zinc-500 hover:text-rose-400 border border-transparent hover:border-zinc-800 transition-colors"
          title="Delete Subscription"
        >
          <Trash2 class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Trial Countdown Alert Banner (if FREE_TRIAL) -->
    <div
      v-if="subscription?.type === 'FREE_TRIAL'"
      class="p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      :class="[
        daysRemaining !== null && daysRemaining <= 1
          ? 'bg-rose-500/10 border-rose-500/30 text-rose-200'
          : (daysRemaining !== null && daysRemaining <= 3 ? 'bg-amber-500/10 border-amber-500/30 text-amber-200' : 'bg-zinc-900/40 border-zinc-800/80 text-zinc-300')
      ]"
    >
      <div class="flex items-start gap-3">
        <div class="w-9 h-9 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0">
          <ShieldAlert class="w-4 h-4 text-zinc-400" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h3 class="text-xs font-semibold font-mono uppercase tracking-wide">
              Free Trial Countdown Watchdog
            </h3>
            <span
              class="text-[9px] font-mono px-1.5 py-0.2 rounded border font-semibold uppercase"
              :class="daysRemaining !== null && daysRemaining <= 1 ? 'bg-rose-950 text-rose-400 border-rose-800' : 'bg-zinc-900 text-zinc-400 border-zinc-800'"
            >
              {{ daysRemaining !== null && daysRemaining <= 0 ? 'EXPIRED' : `${daysRemaining ?? 0} DAYS LEFT` }}
            </span>
          </div>
          <p class="text-xs mt-0.5 opacity-90">
            {{ subscription?.status === 'CANCELLED'
              ? 'This trial has been marked as cancelled. No surprise recurring debits expected.'
              : `Cancel before ${subscription?.due_date || 'renewal date'} to prevent an automatic charge of ${subscriptionCurrencySymbol}${formatNumber(subscription?.amount)}.` }}
          </p>
        </div>
      </div>

      <div v-if="subscription?.status !== 'CANCELLED'" class="flex items-center gap-2 shrink-0">
        <a
          v-if="subscription?.metadata?.cancel_url"
          :href="subscription.metadata.cancel_url"
          target="_blank"
          class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5"
        >
          <span>Cancel on Site</span>
          <ExternalLink class="w-3.5 h-3.5 text-zinc-950" />
        </a>
        <button
          @click="handleCancelTrial"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs font-medium transition-colors"
        >
          Mark Cancelled
        </button>
      </div>
    </div>

    <!-- KPI Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- 1. Next Renewal / Due Date -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">
            {{ subscription?.summary?.is_terminated ? 'Final Billing Date' : 'Next Billing Date' }}
          </span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
            <Calendar class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2">
          {{ formatDate(subscription?.due_date) || `Day ${subscription?.billing_day || '-'}` }}
        </div>
        <p class="text-[11px] font-mono mt-1" :class="subscription?.summary?.is_terminated ? 'text-amber-400' : (daysRemaining !== null && daysRemaining <= 3 ? 'text-rose-400' : 'text-zinc-500')">
          {{ subscription?.summary?.is_terminated ? 'สิ้นสุดสัญญาแล้ว (บิลสุดท้าย)' : (daysRemaining !== null ? (daysRemaining < 0 ? `${Math.abs(daysRemaining)} days ago` : `${daysRemaining} days remaining`) : 'Not scheduled') }}
        </p>
      </div>

      <!-- 2. Cost per Billing Period -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">
            {{ subscription?.type === 'FREE_TRIAL' ? 'Auto-Renew Cost' : 'Period Fee' }}
          </span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-300 flex items-center justify-center">
            <CreditCard class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2">
          <template v-if="subscription?.summary?.is_pure_dynamic && (subscription?.summary?.pending_dynamic_count ?? 0) > 0">
            <span class="text-amber-400 text-base">รอกรอก {{ subscription.summary.pending_dynamic_count }} รายการ</span>
          </template>
          <template v-else-if="subscription?.metadata?.is_itemized && (subscription?.summary?.pending_dynamic_count ?? 0) > 0">
            <span>{{ subscriptionCurrencySymbol }}{{ formatNumber(subscription?.summary?.fixed_total ?? subscription?.amount) }}</span>
          </template>
          <template v-else>
            {{ subscriptionCurrencySymbol }}{{ formatNumber(subscription?.summary?.total_bill_amount ?? subscription?.amount) }}
          </template>
        </div>
        <p v-if="subscription?.metadata?.is_itemized && (subscription?.summary?.pending_dynamic_count ?? 0) > 0" class="text-[10px] text-amber-400 mt-1 font-mono leading-tight">
          + รอกรอก {{ subscription.summary?.pending_dynamic_count }} รายการ
        </p>
        <p v-else class="text-[11px] text-zinc-500 mt-1 font-mono uppercase">
          Billed {{ subscription?.metadata?.billing_cycle || 'Monthly' }}
        </p>
      </div>

      <!-- 3. Normalized Monthly Equivalent -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">Monthly Equivalent</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
            <Calculator class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-200 mt-2">
          <span v-if="subscription?.summary?.is_pure_dynamic && (subscription?.summary?.pending_dynamic_count ?? 0) > 0" class="text-amber-400 text-base font-medium">
            ยังไม่ทราบยอด
          </span>
          <span v-else>
            {{ subscriptionCurrencySymbol }}{{ formatNumber(monthlyEquivalent) }}
          </span>
        </div>
        <p v-if="subscription?.metadata?.is_itemized && (subscription?.summary?.pending_dynamic_count ?? 0) > 0" class="text-[10px] text-amber-400 mt-1 font-mono leading-tight">
          * คิดจากส่วนคงที่ (ยังไม่รวมรายการรอกรอก)
        </p>
        <p v-else class="text-[11px] text-zinc-500 mt-1 font-mono">
          Monthly normalized cost
        </p>
      </div>

      <!-- 4. Annualized Burn -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">Annualized Burn</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
            <Clock class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2">
          <span v-if="subscription?.summary?.is_pure_dynamic && (subscription?.summary?.pending_dynamic_count ?? 0) > 0" class="text-amber-400 text-base font-medium">
            ยังไม่ทราบยอด
          </span>
          <span v-else>
            {{ subscriptionCurrencySymbol }}{{ formatNumber(monthlyEquivalent * 12) }}
          </span>
        </div>
        <p v-if="subscription?.metadata?.is_itemized && (subscription?.summary?.pending_dynamic_count ?? 0) > 0" class="text-[10px] text-amber-400 mt-1 font-mono leading-tight">
          * ไม่รวมรายการที่ต้องกรอกยอดแต่ละรอบ
        </p>
        <p v-else class="text-[11px] text-zinc-500 mt-1 font-mono">
          Projected 12-month spend
        </p>
      </div>
    </div>

    <!-- Itemized Breakdown Card (If is_itemized) -->
    <div v-if="subscription?.metadata?.is_itemized" class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 p-5 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-zinc-800/80 gap-3">
        <div class="flex items-center gap-2">
          <Layers class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            รายการค่าใช้จ่าย (Line Items Breakdown)
          </h2>
        </div>

        <!-- Tabs switcher -->
        <div class="flex items-center bg-zinc-950 p-0.5 rounded-lg border border-zinc-800 text-[11px] font-mono">
          <button
            type="button"
            @click="itemizedViewTab = 'current'"
            class="px-2.5 py-1 rounded transition-colors"
            :class="itemizedViewTab === 'current' ? 'bg-zinc-800 text-zinc-100 font-semibold shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
          >
            บิลรอบปัจจุบัน (Current Cycle Draft)
          </button>
          <button
            type="button"
            @click="itemizedViewTab = 'plan'"
            class="px-2.5 py-1 rounded transition-colors"
            :class="itemizedViewTab === 'plan' ? 'bg-zinc-800 text-zinc-100 font-semibold shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
          >
            รายการแผน (Plan Spec)
          </button>
        </div>
      </div>

      <!-- Tab 1: Current Billing Cycle Draft -->
      <div v-if="itemizedViewTab === 'current'" class="space-y-4">
        <div class="flex items-center justify-between text-xs font-mono text-zinc-400">
          <span>รอบบิล: <strong class="text-zinc-200">{{ subscription?.summary?.current_cycle_key || subscription?.metadata?.current_cycle?.cycle_key || 'Current Cycle' }}</strong></span>
          <span v-if="(subscription?.summary?.pending_dynamic_count ?? 0) > 0" class="text-amber-400">
            รอกรอก {{ subscription.summary?.pending_dynamic_count }} รายการ
          </span>
          <span v-else class="text-emerald-400">
            กรอกยอดครบถ้วนแล้ว
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[10px] text-zinc-500 uppercase">
                <th class="py-2 px-3 font-semibold">ชื่อรายการ</th>
                <th class="py-2 px-3 font-semibold">ชนิด</th>
                <th class="py-2 px-3 font-semibold text-right">ยอดรอบนี้</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr
                v-for="item in currentCycleItems"
                :key="item.id"
                class="hover:bg-zinc-900/50 transition-colors"
              >
                <td class="py-2.5 px-3 text-zinc-200 font-medium">
                  {{ item.name }}
                </td>
                <td class="py-2.5 px-3">
                  <span
                    class="text-[9px] font-mono px-1.5 py-0.5 rounded border"
                    :class="item.type === 'DYNAMIC' ? 'border-amber-900/60 text-amber-400 bg-amber-950/30' : 'border-zinc-800 text-zinc-400 bg-zinc-900'"
                  >
                    {{ item.type === 'DYNAMIC' ? 'DYNAMIC (แปรผัน)' : 'FIXED (คงที่)' }}
                  </span>
                </td>
                <td class="py-2.5 px-3 text-right tabular-nums">
                  <template v-if="item.type === 'DYNAMIC' && (item.amount === null || item.amount === undefined || item.amount === '')">
                    <span class="text-amber-400 font-mono text-[11px]">รอกรอก</span>
                  </template>
                  <template v-else>
                    <span class="text-zinc-100 font-mono">{{ subscriptionCurrencySymbol }}{{ formatNumber(item.amount) }}</span>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Summary footer -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-zinc-950/60 rounded-lg border border-zinc-800/80 text-xs font-mono">
          <div>
            <span class="text-[10px] text-zinc-500 block">ยอดรวมคงที่ (Fixed Total)</span>
            <span class="text-zinc-200 font-semibold">{{ subscriptionCurrencySymbol }}{{ formatNumber(subscription?.summary?.fixed_total ?? 0) }}</span>
          </div>
          <div>
            <span class="text-[10px] text-zinc-500 block">ยอดรวมแปรผัน (Dynamic Total)</span>
            <span class="text-zinc-200 font-semibold">
              {{ (subscription?.summary?.current_cycle?.dynamic_total !== null && subscription?.summary?.current_cycle?.dynamic_total !== undefined)
                ? `${subscriptionCurrencySymbol}${formatNumber(subscription?.summary?.current_cycle?.dynamic_total)}`
                : ((subscription?.summary?.dynamic_total !== null && subscription?.summary?.dynamic_total !== undefined)
                  ? `${subscriptionCurrencySymbol}${formatNumber(subscription?.summary?.dynamic_total)}`
                  : 'ยังไม่ครบ') }}
            </span>
          </div>
          <div>
            <span class="text-[10px] text-zinc-500 block">ยอดรวมทั้งบิล (Total Bill)</span>
            <span class="font-bold" :class="(subscription?.summary?.pending_dynamic_count ?? 0) > 0 ? 'text-amber-400' : 'text-emerald-400'">
              {{ (subscription?.summary?.pending_dynamic_count ?? 0) > 0 ? 'รอระบุยอดแปรผัน' : `${subscriptionCurrencySymbol}${formatNumber(subscription?.summary?.total_bill_amount ?? 0)}` }}
            </span>
          </div>
        </div>
      </div>

      <!-- Tab 2: Plan Specification -->
      <div v-else class="space-y-4">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[10px] text-zinc-500 uppercase">
                <th class="py-2 px-3 font-semibold">ชื่อรายการในแผน</th>
                <th class="py-2 px-3 font-semibold">ประเภท</th>
                <th class="py-2 px-3 font-semibold text-right">ยอดในแผน</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr
                v-for="item in planLineItems"
                :key="item.id"
                class="hover:bg-zinc-900/50 transition-colors"
              >
                <td class="py-2.5 px-3 text-zinc-200 font-medium">
                  {{ item.name }}
                </td>
                <td class="py-2.5 px-3">
                  <span
                    class="text-[9px] font-mono px-1.5 py-0.5 rounded border"
                    :class="item.type === 'DYNAMIC' ? 'border-amber-900/60 text-amber-400 bg-amber-950/30' : 'border-zinc-800 text-zinc-400 bg-zinc-900'"
                  >
                    {{ item.type === 'DYNAMIC' ? 'DYNAMIC (กรอกแต่ละรอบ)' : 'FIXED (ยอดคงที่)' }}
                  </span>
                </td>
                <td class="py-2.5 px-3 text-right tabular-nums">
                  <span v-if="item.type === 'DYNAMIC'" class="text-zinc-500 italic text-[11px]">กรอกตามบิลจริง</span>
                  <span v-else class="text-zinc-100">{{ subscriptionCurrencySymbol }}{{ formatNumber(item.amount) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="p-3 bg-zinc-950/60 rounded-lg border border-zinc-800/80 flex items-center justify-between text-xs font-mono">
          <span class="text-zinc-400">ยอดคงที่รวมในสัญญา (Base Fixed Total):</span>
          <span class="text-zinc-100 font-bold">{{ subscriptionCurrencySymbol }}{{ formatNumber(subscription?.summary?.fixed_total ?? subscription?.amount) }}</span>
        </div>
      </div>
    </div>

    <!-- Main Grid: Service Specs & Invoices Vault -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Column: Specs & Cancellation Guide (2 cols) -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Service Specs Dossier -->
        <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 p-5 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80">
            <div class="flex items-center gap-2">
              <FileText class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Subscription Parameters
              </h2>
            </div>
            <span class="text-[11px] font-mono text-zinc-500">ID: {{ subscription?.id?.slice(0, 8) }}</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            <div>
              <span class="text-[10px] uppercase text-zinc-500 block">Category</span>
              <span class="text-zinc-200 font-sans mt-0.5 block">{{ subscription?.metadata?.category || 'General' }}</span>
            </div>

            <div>
              <span class="text-[10px] uppercase text-zinc-500 block">Subscribed Email / Account</span>
              <span class="text-zinc-200 mt-0.5 block truncate">{{ subscription?.metadata?.account_email || '-' }}</span>
            </div>

            <div>
              <span class="text-[10px] uppercase text-zinc-500 block">Linked Payment Method</span>
              <span class="text-zinc-200 font-sans mt-0.5 block">{{ subscription?.metadata?.payment_method || '-' }}</span>
            </div>

            <div>
              <span class="text-[10px] uppercase text-zinc-500 block">Early Alert Notification</span>
              <span class="text-zinc-200 mt-0.5 block">{{ subscription?.metadata?.alert_days_before || 3 }} days prior to billing</span>
            </div>
          </div>

          <!-- Cancellation URL & Instructions Guide -->
          <div class="pt-3 border-t border-zinc-800/80 space-y-2">
            <span class="text-[10px] font-mono uppercase text-zinc-500 block">Cancellation Guide & Direct Links</span>
            <div v-if="subscription?.metadata?.cancel_url" class="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-between gap-3">
              <div class="truncate text-xs font-mono text-zinc-300">
                <span class="text-zinc-500 mr-2">URL:</span>
                <a :href="subscription.metadata.cancel_url" target="_blank" class="hover:underline text-zinc-200">{{ subscription.metadata.cancel_url }}</a>
              </div>
              <a
                :href="subscription.metadata.cancel_url"
                target="_blank"
                class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs font-medium transition-colors shrink-0 flex items-center gap-1"
              >
                <span>Open URL</span>
                <ExternalLink class="w-3 h-3 text-zinc-400" />
              </a>
            </div>

            <div v-if="subscription?.metadata?.cancel_steps" class="p-3 rounded-lg bg-zinc-950/60 border border-zinc-800 text-xs text-zinc-300 leading-relaxed font-sans">
              <div class="font-semibold text-zinc-200 mb-1 font-mono text-[11px] uppercase text-zinc-400">Steps to Cancel:</div>
              {{ subscription.metadata.cancel_steps }}
            </div>

            <div v-if="!subscription?.metadata?.cancel_url && !subscription?.metadata?.cancel_steps" class="text-xs text-zinc-500 italic">
              No cancellation instructions recorded for this service.
            </div>
          </div>
        </div>

        <!-- Payment & Renewal History Ledger -->
        <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
          <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <History class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Renewal & Payment Ledger
              </h2>
            </div>
            <span class="text-[11px] font-mono text-zinc-500">{{ paymentHistories.length }} Payments Recorded</span>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs font-mono">
              <thead>
                <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[10px] text-zinc-500 uppercase">
                  <th class="py-2.5 px-4 font-semibold">Payment Date</th>
                  <th class="py-2.5 px-4 font-semibold text-right">Amount Paid</th>
                  <th class="py-2.5 px-4 font-semibold">Note / Remarks</th>
                  <th class="py-2.5 px-4 font-semibold text-right">Details</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/50">
                <template v-for="p in paymentHistories" :key="p.id">
                  <tr class="hover:bg-zinc-900/50 transition-colors">
                    <td class="py-3 px-4 text-zinc-300">
                      {{ formatDate(p.paid_at) }}
                    </td>
                    <td class="py-3 px-4 text-right font-semibold text-emerald-400 tabular-nums">
                      {{ subscriptionCurrencySymbol }}{{ formatNumber(p.paid_amount) }}
                    </td>
                    <td class="py-3 px-4 text-zinc-400 text-[11px]">
                      {{ p.note || 'Subscription renewal payment' }}
                    </td>
                    <td class="py-3 px-4 text-right">
                      <button
                        v-if="p.metadata?.cycle_items && p.metadata.cycle_items.length > 0"
                        @click="togglePaymentExpanded(p.id)"
                        type="button"
                        class="inline-flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors"
                      >
                        <span>{{ expandedPaymentIds.has(p.id) ? 'ซ่อน' : 'ดูรายละเอียด' }}</span>
                        <ChevronDown class="w-3 h-3 transition-transform" :class="{ 'rotate-180': expandedPaymentIds.has(p.id) }" />
                      </button>
                      <span v-else class="text-[10px] text-zinc-600">-</span>
                    </td>
                  </tr>

                  <!-- Expanded Cycle Items Sub-row -->
                  <tr v-if="expandedPaymentIds.has(p.id)" class="bg-zinc-950/70 border-b border-zinc-800/60">
                    <td colspan="4" class="p-3 pl-8">
                      <div class="text-[11px] font-mono text-zinc-400 mb-1.5 font-semibold flex items-center justify-between max-w-lg">
                        <span>รอบบิล: {{ p.metadata?.cycle_key || 'Billing Cycle' }}</span>
                        <span class="text-zinc-500 font-normal">{{ p.metadata?.cycle_items?.length ?? 0 }} รายการ</span>
                      </div>
                      <table class="w-full max-w-lg text-left text-xs font-mono bg-zinc-900/40 rounded border border-zinc-800/60">
                        <thead>
                          <tr class="border-b border-zinc-800/60 text-[9px] text-zinc-500 uppercase bg-zinc-950/40">
                            <th class="py-1.5 px-3">รายการ</th>
                            <th class="py-1.5 px-3">ประเภท</th>
                            <th class="py-1.5 px-3 text-right">ยอดเงิน</th>
                          </tr>
                        </thead>
                        <tbody class="divide-y divide-zinc-800/40">
                          <tr v-for="(item, idx) in p.metadata?.cycle_items" :key="idx">
                            <td class="py-1.5 px-3 text-zinc-300">{{ item.name }}</td>
                            <td class="py-1.5 px-3 text-zinc-500 text-[10px]">{{ item.type }}</td>
                            <td class="py-1.5 px-3 text-right text-zinc-200 tabular-nums">
                              {{ subscriptionCurrencySymbol }}{{ formatNumber(item.amount) }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                </template>

                <tr v-if="paymentHistories.length === 0">
                  <td colspan="4" class="py-8 text-center text-xs text-zinc-500">
                    No payment history recorded yet for this service
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Right Column: Document Vault & Quick Attachments (1 col) -->
      <div class="space-y-6">
        <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 p-5 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80">
            <div class="flex items-center gap-2">
              <FolderArchive class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Document Vault
              </h2>
            </div>
            <label
              v-if="storageStore.isConnected"
              class="text-xs font-mono text-zinc-300 hover:text-white cursor-pointer transition-colors"
            >
              <span>+ Upload</span>
              <input
                type="file"
                class="hidden"
                @change="handleFileUpload"
              />
            </label>
            <router-link
              v-else
              to="/settings"
              class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 underline"
            >
              Connect Drive
            </router-link>
          </div>

          <p class="text-xs text-zinc-500">
            Archive renewal invoices, payment slips, or cancellation proof receipts
          </p>

          <!-- Upload Status Indicator -->
          <div v-if="isUploading" class="p-2.5 rounded bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-400 text-center space-y-1.5">
            <div>Uploading document to Google Drive...</div>
            <div v-if="storageStore.uploadProgress !== null" class="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
              <div
                class="bg-zinc-200 h-1 transition-all duration-150"
                :style="{ width: `${storageStore.uploadProgress}%` }"
              ></div>
            </div>
          </div>

          <!-- Attachments List -->
          <div v-if="attachments.length > 0" class="space-y-2">
            <div
              v-for="att in attachments"
              :key="att.id"
              class="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80 flex items-center justify-between gap-2"
            >
              <div class="flex items-center gap-2 truncate">
                <FileText class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <div class="truncate text-xs font-mono">
                  <a
                    :href="att.drive_view_link || att.file_url || att.file"
                    target="_blank"
                    class="text-zinc-200 hover:text-white hover:underline truncate block"
                  >
                    {{ att.file_name }}
                  </a>
                  <span class="text-[10px] text-zinc-500 block">{{ formatFileSize(att.file_size) }} · {{ att.file_type }}</span>
                </div>
              </div>
              <a
                :href="att.drive_download_link || att.drive_view_link || att.file_url || att.file"
                download
                target="_blank"
                class="p-1 text-zinc-400 hover:text-zinc-100"
                title="Download / Open"
              >
                <Download class="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          <div v-else class="text-xs text-zinc-500 font-mono py-4 text-center">
            No invoices or slips stored
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <!-- Pay Modal -->
    <PayModal
      :is-open="showPayModal"
      :obligation="subscription"
      @close="showPayModal = false"
      @paid="handlePaySuccess"
    />

    <!-- Terminate Modal -->
    <TerminateSubscriptionModal
      :is-open="showTerminateModal"
      :obligation="subscription"
      @close="showTerminateModal = false"
      @terminated="handleTerminateSuccess"
    />

    <!-- Convert Trial Modal -->
    <div v-if="showConvertModal" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-hidden">
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md shadow-2xl relative flex flex-col max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] overflow-hidden">
        <!-- Header -->
        <div class="p-4 sm:p-5 pb-3 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
          <div>
            <h3 class="text-sm font-semibold text-zinc-100">Convert Trial to Recurring Subscription</h3>
            <p class="text-xs text-zinc-400 mt-0.5">
              Keep this service active and establish a recurring billing cycle.
            </p>
          </div>
          <button
            type="button"
            @click="showConvertModal = false"
            class="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <form @submit.prevent="submitConvertTrial" class="flex flex-col flex-1 min-h-0 overflow-hidden text-xs font-mono">
          <div class="p-4 sm:p-5 space-y-4 overflow-y-auto overscroll-contain flex-1 min-h-0">
            <div>
              <label class="block text-zinc-400 mb-1">Billing Cycle</label>
              <select
                v-model="convertCycle"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-100 focus:border-zinc-700 outline-none"
              >
                <option value="MONTHLY">Monthly</option>
                <option value="YEARLY">Yearly</option>
                <option value="QUARTERLY">Quarterly</option>
              </select>
            </div>

            <div>
              <label class="block text-zinc-400 mb-1">Recurring Cost</label>
              <input
                v-model.number="convertAmount"
                type="number"
                step="0.01"
                required
                class="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-100 focus:border-zinc-700 outline-none"
              />
            </div>
          </div>

          <div class="flex items-center justify-end gap-2 p-4 border-t border-zinc-800/80 shrink-0 bg-zinc-950/90">
            <button
              type="button"
              @click="showConvertModal = false"
              class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isConverting"
              class="px-4 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 font-semibold transition-colors disabled:opacity-50"
            >
              {{ isConverting ? 'Converting...' : 'Convert to Active' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Obligation Modal -->
    <EditObligationModal
      :is-open="showEditModal"
      :obligation="subscription"
      @close="showEditModal = false"
      @updated="handleSubscriptionUpdated"
    />

    <!-- Confirm Modal -->
    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      :is-loading="confirmModal.isLoading"
      :error-message="confirmModal.errorMessage"
      @confirm="handleConfirmAction"
      @cancel="confirmModal.isOpen = false; confirmModal.errorMessage = ''"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSubscriptions } from '../../composables/finance/useSubscriptions'
import { useStorageStore } from '../../stores/storage'
import { useToastStore } from '../../stores/toast'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import EditObligationModal from '../../components/finance/EditObligationModal.vue'
import PayModal from '../../components/finance/PayModal.vue'
import TerminateSubscriptionModal from '../../components/finance/TerminateSubscriptionModal.vue'
import {
  ArrowLeft,
  ExternalLink,
  ShieldAlert,
  Repeat,
  Receipt,
  Trash2,
  Calendar,
  CreditCard,
  Calculator,
  Clock,
  FileText,
  History,
  FolderArchive,
  Download,
  Edit2,
  Layers,
  ChevronDown,
  XCircle
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const {
  currentSubscription,
  paymentHistories,
  attachments,
  isActionLoading,
  fetchSubscription,
  cancelTrial,
  convertToSubscription,
  deleteSubscription
} = useSubscriptions()

const toast = useToastStore()
const storageStore = useStorageStore()
const subscriptionId = computed(() => route.params.id as string)
const subscription = computed(() => currentSubscription.value)

const showPayModal = ref(false)
const showTerminateModal = ref(false)
const itemizedViewTab = ref<'current' | 'plan'>('current')
const expandedPaymentIds = ref<Set<string>>(new Set())

function togglePaymentExpanded(id: string) {
  const next = new Set(expandedPaymentIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedPaymentIds.value = next
}

const showConvertModal = ref(false)
const convertCycle = ref('MONTHLY')
const convertAmount = ref(0)
const isConverting = ref(false)

const showEditModal = ref(false)

async function handleSubscriptionUpdated() {
  const subId = route.params.id as string
  if (subId) {
    await fetchSubscription(subId)
    toast.success('Subscription details updated')
  }
}

async function handlePaySuccess() {
  await fetchSubscription(subscriptionId.value)
  toast.success('บันทึกการชำระเงินเรียบร้อยแล้ว')
}

async function handleTerminateSuccess() {
  await fetchSubscription(subscriptionId.value)
  toast.success('ยุติรายการประจำเรียบร้อยแล้ว')
}

const isWorkspace = computed(() => !!subscription.value?.metadata?.workspace_managed)

const payButtonLabel = computed(() => {
  if (subscription.value?.summary?.is_terminated || subscription.value?.metadata?.termination?.status === 'TERMINATED') {
    return 'ชำระบิลสุดท้าย'
  }
  if (subscription.value?.metadata?.is_itemized && (subscription.value?.summary?.pending_dynamic_count ?? 0) > 0) {
    return 'กรอกยอดและชำระ'
  }
  return 'บันทึกการชำระ'
})

const currentCycleItems = computed(() => {
  return subscription.value?.metadata?.current_cycle?.items || []
})

const planLineItems = computed(() => {
  return subscription.value?.metadata?.line_items || []
})

const isUploading = ref(false)

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  isLoading: false,
  errorMessage: '',
  action: async () => {}
})

useBodyScrollLock(() => showPayModal.value || showTerminateModal.value || showConvertModal.value || showEditModal.value || confirmModal.isOpen)

async function handleConfirmAction() {
  confirmModal.isLoading = true
  confirmModal.errorMessage = ''
  try {
    await confirmModal.action()
    confirmModal.isOpen = false
  } catch (err: any) {
    confirmModal.errorMessage = err?.response?.data?.detail || err?.response?.data?.error || err?.message || 'Operation failed'
  } finally {
    confirmModal.isLoading = false
  }
}

const subscriptionCurrencySymbol = computed(() => {
  return subscription.value?.currency === 'USD' ? '$' : '฿'
})

const daysRemaining = computed(() => {
  if (!subscription.value?.due_date) return null
  const target = new Date(subscription.value.due_date).getTime()
  const now = new Date(new Date().toISOString().split('T')[0]).getTime()
  return Math.round((target - now) / (1000 * 60 * 60 * 24))
})

const monthlyEquivalent = computed(() => {
  if (subscription.value?.summary?.monthly_equivalent !== undefined && subscription.value?.summary?.monthly_equivalent !== null) {
    return Number(subscription.value.summary.monthly_equivalent)
  }
  let amt = Number(subscription.value?.amount || 0)
  if (subscription.value?.summary?.is_itemized) {
    if (subscription.value?.summary?.total_bill_amount !== undefined && subscription.value?.summary?.total_bill_amount !== null) {
      amt = Number(subscription.value.summary.total_bill_amount)
    } else if (subscription.value?.summary?.fixed_total !== undefined && subscription.value?.summary?.fixed_total !== null) {
      amt = Number(subscription.value.summary.fixed_total)
    }
  }
  const cycle = subscription.value?.metadata?.billing_cycle || 'MONTHLY'
  if (cycle === 'YEARLY') return amt / 12
  if (cycle === 'QUARTERLY') return amt / 3
  if (cycle === 'WEEKLY') return amt * 4.333
  return amt
})

function getStatusBadgeClass(status?: string) {
  switch (status) {
    case 'ACTIVE':
      return 'bg-zinc-900 text-emerald-400 border-zinc-800'
    case 'CANCELLED':
      return 'bg-zinc-900 text-zinc-500 border-zinc-800'
    case 'PAUSED':
      return 'bg-zinc-900 text-amber-400 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

function formatDate(dateStr?: string | null) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

function formatNumber(val: any): string {
  const num = Number(val || 0)
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '0 KB'
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(0)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

async function handleCancelTrial() {
  try {
    await cancelTrial(subscriptionId.value)
    toast.success('Free trial marked as cancelled')
  } catch {
    toast.error('Failed to cancel trial')
  }
}

async function submitConvertTrial() {
  isConverting.value = true
  try {
    await convertToSubscription(subscriptionId.value, {
      billing_cycle: convertCycle.value,
      amount: convertAmount.value
    })
    toast.success('Converted trial to recurring subscription')
    showConvertModal.value = false
  } catch {
    toast.error('Failed to convert trial')
  } finally {
    isConverting.value = false
  }
}

async function handleFileUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  if (!storageStore.isConnected) {
    toast.error('Google Drive connection is required')
    return
  }

  isUploading.value = true
  try {
    await storageStore.uploadDirect(file, 'finance', subscriptionId.value)
    toast.success('Document uploaded to Google Drive vault')
    target.value = ''
    await fetchSubscription(subscriptionId.value)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to upload document')
  } finally {
    isUploading.value = false
  }
}

function confirmDelete() {
  confirmModal.title = 'Delete Subscription'
  confirmModal.message = 'Are you sure you want to delete this subscription dossier? All payment records and alarms will be removed.'
  confirmModal.confirmText = 'Delete Subscription'
  confirmModal.isDanger = true
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    await deleteSubscription(subscriptionId.value)
    toast.info('Deleted subscription record')
    router.push('/finance/subscriptions')
  }
  confirmModal.isOpen = true
}

onMounted(async () => {
  try {
    const data = await fetchSubscription(subscriptionId.value)
    if (data) {
      convertAmount.value = Number(data.amount || 0)
    }
  } catch {
    toast.error('Failed to load subscription dossier')
    router.push('/finance/subscriptions')
  }
})
</script>
