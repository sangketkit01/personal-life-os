<template>
  <div class="space-y-6 max-w-4xl mx-auto font-sans">
    <div class="pb-4 border-b border-zinc-800/80">
      <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">{{ t('st.title') }}</h1>
      <p class="text-xs text-zinc-500 mt-0.5">{{ t('st.subtitle') }}</p>
    </div>

    <!-- Theme & Appearance -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-md bg-zinc-900 text-zinc-200 flex items-center justify-center border border-zinc-800">
            <component :is="themeMode === 'light' ? Sun : themeMode === 'system' ? Monitor : Moon" class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('st.theme.title') }}</h2>
          </div>
        </div>
        <span class="text-[10px] font-mono px-2 py-0.5 rounded border uppercase bg-zinc-900 text-zinc-300 border-zinc-800">
          {{ themeMode === 'dark' ? t('st.theme.badge') : themeMode === 'light' ? 'LIGHT' : 'SYSTEM' }}
        </span>
      </div>
      <div class="p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <button type="button" @click="switchTheme('dark')"
          class="p-3.5 rounded-lg border text-left transition-all"
          :class="themeMode === 'dark' ? 'bg-zinc-900 border-zinc-600 shadow-sm' : 'bg-zinc-950/40 border-zinc-800/80 hover:border-zinc-700'">
          <div class="flex items-center justify-between">
            <Moon class="w-4 h-4" :class="themeMode === 'dark' ? 'text-indigo-400' : 'text-zinc-500'" />
            <CheckCircle2 v-if="themeMode === 'dark'" class="w-4 h-4 text-emerald-400" />
          </div>
          <span class="text-sm font-semibold block mt-1.5" :class="themeMode === 'dark' ? 'text-zinc-100' : 'text-zinc-300'">{{ t('st.theme.dark') }}</span>
          <p class="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">{{ t('st.theme.darkSub') }}</p>
        </button>
        <button type="button" @click="switchTheme('light')"
          class="p-3.5 rounded-lg border text-left transition-all"
          :class="themeMode === 'light' ? 'bg-zinc-900 border-zinc-600 shadow-sm' : 'bg-zinc-950/40 border-zinc-800/80 hover:border-zinc-700'">
          <div class="flex items-center justify-between">
            <Sun class="w-4 h-4" :class="themeMode === 'light' ? 'text-amber-400' : 'text-zinc-500'" />
            <CheckCircle2 v-if="themeMode === 'light'" class="w-4 h-4 text-emerald-400" />
          </div>
          <span class="text-sm font-semibold block mt-1.5" :class="themeMode === 'light' ? 'text-zinc-100' : 'text-zinc-300'">{{ t('st.theme.light') }}</span>
          <p class="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">{{ t('st.theme.lightSub') }}</p>
        </button>
        <button type="button" @click="switchTheme('system')"
          class="p-3.5 rounded-lg border text-left transition-all"
          :class="themeMode === 'system' ? 'bg-zinc-900 border-zinc-600 shadow-sm' : 'bg-zinc-950/40 border-zinc-800/80 hover:border-zinc-700'">
          <div class="flex items-center justify-between">
            <Monitor class="w-4 h-4" :class="themeMode === 'system' ? 'text-sky-400' : 'text-zinc-500'" />
            <CheckCircle2 v-if="themeMode === 'system'" class="w-4 h-4 text-emerald-400" />
          </div>
          <span class="text-sm font-semibold block mt-1.5" :class="themeMode === 'system' ? 'text-zinc-100' : 'text-zinc-300'">{{ t('st.theme.system') }}</span>
          <p class="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">{{ t('st.theme.systemSub') }}</p>
        </button>
      </div>
    </div>

    <!-- 0. Language & Localization -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-md bg-zinc-900 text-zinc-200 flex items-center justify-center border border-zinc-800">
            <Languages class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('st.lang.title') }}</h2>
            <p class="text-xs text-zinc-500">{{ t('st.lang.subtitle') }}</p>
          </div>
        </div>

        <span class="text-[10px] font-mono px-2 py-0.5 rounded border uppercase bg-zinc-900 text-zinc-300 border-zinc-800">
          {{ locale === 'th' ? 'TH' : 'EN' }}
        </span>
      </div>

      <div class="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
          type="button"
          @click="switchLanguage('en')"
          class="p-3.5 rounded-lg border text-left transition-all group"
          :class="locale === 'en'
            ? 'bg-zinc-900 border-zinc-600 shadow-sm'
            : 'bg-zinc-950/40 border-zinc-800/80 hover:border-zinc-700'"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold" :class="locale === 'en' ? 'text-zinc-100' : 'text-zinc-300'">English (EN)</span>
            <CheckCircle2 v-if="locale === 'en'" class="w-4 h-4 text-emerald-400" />
          </div>
          <p class="text-[11px] text-zinc-500 mt-1 leading-relaxed">{{ t('st.lang.enSub') }}</p>
        </button>

        <button
          type="button"
          @click="switchLanguage('th')"
          class="p-3.5 rounded-lg border text-left transition-all group"
          :class="locale === 'th'
            ? 'bg-zinc-900 border-zinc-600 shadow-sm'
            : 'bg-zinc-950/40 border-zinc-800/80 hover:border-zinc-700'"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold" :class="locale === 'th' ? 'text-zinc-100' : 'text-zinc-300'">ภาษาไทย (TH)</span>
            <CheckCircle2 v-if="locale === 'th'" class="w-4 h-4 text-emerald-400" />
          </div>
          <p class="text-[11px] text-zinc-500 mt-1 leading-relaxed">เมนูและป้ายกำกับภาษาไทย พร้อมสรุปข่าวหุ้นแปลไทยอัตโนมัติ</p>
        </button>
      </div>
    </div>

    <!-- 1. Telegram Butler Connection -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-md bg-zinc-900 text-zinc-200 flex items-center justify-center border border-zinc-800">
            <Bot class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('st.tg.title') }}</h2>
            <p class="text-xs text-zinc-500">{{ t('st.tg.subtitle') }}</p>
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
          {{ authStore.user?.is_telegram_connected ? t('st.tg.connected') : t('st.tg.disconnected') }}
        </span>
      </div>

      <div class="p-4">
        <div v-if="authStore.user?.is_telegram_connected" class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono flex items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <span class="text-zinc-400">{{ t('st.tg.linkedChat') }} <strong class="text-zinc-100 font-semibold">{{ authStore.user.telegram_chat_id }}</strong></span>
            <span class="text-[11px] text-emerald-400">{{ t('st.tg.active') }}</span>
          </div>
          <button
            @click="handleDisconnectTelegram"
            :disabled="isDisconnectingTelegram"
            type="button"
            class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-rose-400 text-xs font-sans transition-colors disabled:opacity-50"
          >
            {{ isDisconnectingTelegram ? t('st.tg.disconnecting') : t('st.tg.disconnect') }}
          </button>
        </div>

        <div v-else class="flex items-center justify-between p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
          <span class="text-xs text-zinc-400">{{ t('st.tg.authorizeBot') }}</span>
          <button
            @click="handleConnectTelegram"
            :disabled="isGeneratingToken"
            class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {{ isGeneratingToken ? t('st.tg.generating') : t('st.tg.connect') }}
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
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('st.drive.title') }}</h2>
            <p class="text-xs text-zinc-500 mt-0.5">{{ t('st.drive.subtitle') }}</p>
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
          {{ storageStore.isConnected ? t('st.tg.connected') : t('st.tg.disconnected') }}
        </span>
      </div>

      <div class="p-4">
        <div v-if="storageStore.isConnected" class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="space-y-0.5">
            <div class="text-zinc-300">
              {{ t('st.drive.connectedAccount') }} <strong class="text-zinc-100 font-semibold">{{ storageStore.googleEmail }}</strong>
            </div>
            <div class="text-[11px] text-zinc-500">
              {{ t('st.drive.cloudDir') }}
            </div>
          </div>
          <div class="flex items-center gap-2">
            <a
              v-if="storageStore.rootFolderId"
              :href="`https://drive.google.com/drive/folders/${storageStore.rootFolderId}`"
              target="_blank"
              class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-sans transition-colors flex items-center gap-1.5"
            >
              <span>{{ t('st.drive.openInDrive') }}</span>
              <ExternalLink class="w-3.5 h-3.5 text-zinc-400" />
            </a>
            <button
              @click="handleDisconnectDrive"
              :disabled="storageStore.isLoading"
              type="button"
              class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 text-xs font-sans transition-colors"
            >
              {{ t('st.tg.disconnect') }}
            </button>
          </div>
        </div>

        <div v-else class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
          <div>
            <div class="text-xs text-zinc-200 font-medium">{{ t('st.drive.required') }}</div>
            <p class="text-[11px] text-zinc-500 mt-0.5">{{ t('st.drive.requiredSub') }}</p>
          </div>
          <button
            @click="storageStore.startConnect"
            :disabled="storageStore.isConnecting"
            type="button"
            class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm shrink-0"
          >
            <CloudUpload class="w-3.5 h-3.5 text-zinc-950" />
            <span>{{ storageStore.isConnecting ? t('st.drive.opening') : t('st.drive.connect') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 3. Password & Account Security -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div>
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('st.pw.title') }}</h2>
          <p class="text-xs text-zinc-500 mt-0.5">{{ t('st.pw.subtitle') }}</p>
        </div>
      </div>

      <form @submit.prevent="handleChangePassword" class="p-4 space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">{{ t('st.pw.current') }}</label>
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
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">{{ t('st.pw.new') }}</label>
            <input
              v-model="passwordForm.new_password"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              :placeholder="t('st.pw.minChars')"
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
            {{ isChangingPassword ? t('st.pw.updating') : t('st.pw.update') }}
          </button>
        </div>
      </form>
    </div>

    <!-- 4. Active Devices & Sessions -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between gap-2">
        <div>
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('st.sess.title') }}</h2>
          <p class="text-xs text-zinc-500 mt-0.5">{{ t('st.sess.subtitle') }}</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="sessions.length > 1"
            @click="revokeOtherSessions"
            type="button"
            class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-rose-950/20 text-zinc-400 hover:text-rose-400 border border-zinc-800 hover:border-rose-500/30 text-[11px] font-mono transition-colors"
          >
            {{ t('st.sess.revokeAll') }}
          </button>
          <button
            @click="fetchSessions"
            type="button"
            class="text-xs text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1 font-mono"
          >
            <RefreshCw class="w-3 h-3" />
            <span>{{ t('st.sess.sync') }}</span>
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
                  {{ t('st.sess.current') }}
                </span>
              </div>
              <div class="text-[10px] text-zinc-500 mt-0.5">
                IP: {{ session.ip_address || t('st.sess.internal') }} • {{ t('st.sess.lastActive') }} {{ formatLocaleDate(session.last_active_at) }}
              </div>
            </div>
          </div>

          <button
            v-if="!session.is_current"
            @click="revokeSession(session.id)"
            class="px-2 py-1 rounded bg-zinc-900 hover:bg-rose-950/20 text-zinc-400 hover:text-rose-400 border border-zinc-800 hover:border-rose-500/30 text-[11px] transition-colors"
          >
            {{ t('st.sess.revoke') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 5. Invite Codes for Friends (1 Code = 1 User) -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div>
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('st.inv.title') }}</h2>
          <p class="text-xs text-zinc-500 mt-0.5">{{ t('st.inv.subtitle') }}</p>
        </div>
        <button
          @click="createInviteCode"
          class="px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1"
        >
          <Plus class="w-3 h-3 text-zinc-950" />
          <span>{{ t('st.inv.new') }}</span>
        </button>
      </div>

      <div class="p-4">
        <div v-if="invites.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500">
          {{ t('st.inv.empty') }}
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
                <span v-if="inv.used_by_username" class="text-zinc-400">{{ t('st.inv.usedBy') }} @{{ inv.used_by_username }} (1/1)</span>
                <span v-else-if="inv.is_active" class="text-emerald-400">{{ t('st.inv.available') }}</span>
                <span v-else>{{ t('st.inv.exhausted') }} ({{ inv.uses_count }}/1)</span>
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
                <span>{{ t('st.inv.copy') }}</span>
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
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ t('st.log.title') }}</h2>
            <p class="text-xs text-zinc-500 mt-0.5">{{ t('st.log.subtitle') }}</p>
          </div>
        </div>
        <button
          @click="fetchAuditLogs"
          :disabled="isLoadingLogs"
          class="text-xs text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1 font-mono disabled:opacity-50"
        >
          <RefreshCw class="w-3 h-3" :class="{ 'animate-spin': isLoadingLogs }" />
          <span>{{ t('st.sess.sync') }}</span>
        </button>
      </div>

      <div class="p-4">
        <div v-if="auditLogs.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500">
          {{ t('st.log.empty') }}
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">
                <th class="pb-2.5">{{ t('st.log.timestamp') }}</th>
                <th class="pb-2.5">{{ t('st.log.domain') }}</th>
                <th class="pb-2.5">{{ t('st.log.action') }}</th>
                <th class="pb-2.5">{{ t('st.log.description') }}</th>
                <th class="pb-2.5">{{ t('st.log.origin') }}</th>
                <th class="pb-2.5 text-right">{{ t('st.log.status') }}</th>
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
                  <span>{{ log.device_name || t('st.log.system') }}</span>
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
import { locale, setLocale, t, formatLocaleDate } from '../i18n'
import { themeMode, setThemeMode, type ThemeMode } from '../theme'
import type { AppLocale } from '../i18n'
import { useStorageStore } from '../stores/storage'
import { useToastStore } from '../stores/toast'
import apiClient from '../api/client'
import type { UserDeviceSession, InviteCode, ActivityLog } from '../types'
import ConfirmModal from '../components/common/ConfirmModal.vue'
import {
  Languages,
  Moon,
  Sun,
  Monitor,
  CheckCircle2,
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

async function switchTheme(mode: ThemeMode) {
  if (themeMode.value === mode) return
  setThemeMode(mode, { syncBackend: false })
  try {
    await authStore.updatePreferences({ preferred_theme: mode })
    const toastKey = mode === 'dark' ? 'st.theme.switchedDark' : mode === 'light' ? 'st.theme.switchedLight' : 'st.theme.switchedSystem'
    toast.success(t(toastKey))
  } catch {
    toast.error(t('st.theme.saveFailed'))
  }
}

async function switchLanguage(next: AppLocale) {
  if (locale.value === next) return
  // UI reacts instantly; persist to backend without double-patching
  setLocale(next, { syncBackend: false })
  try {
    await authStore.updatePreferences({ preferred_language: next })
    toast.success(next === 'th' ? t('st.lang.switchedTh') : t('st.lang.switchedEn'))
  } catch {
    toast.error(t('st.lang.saveFailed'))
  }
}

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
  confirmText: t('common.confirm'),
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
    toast.error(t('st.tg.linkFailed'))
  } finally {
    isGeneratingToken.value = false
  }
}

function handleDisconnectTelegram() {
  confirmModal.title = t('st.tg.disconnectTitle')
  confirmModal.message = t('st.tg.disconnectMsg')
  confirmModal.confirmText = t('st.tg.disconnect')
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    isDisconnectingTelegram.value = true
    try {
      await authStore.disconnectTelegram()
      await fetchAuditLogs()
      toast.info(t('st.tg.disconnectedToast'))
    } catch (err) {
      toast.error(t('st.tg.disconnectFailed'))
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
    toast.success(res.message || t('st.pw.success'))
  } catch (err: any) {
    const errorData = err.response?.data
    let msg = t('st.pw.failed')
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
    toast.info(t('st.sess.revokedToast'))
  } catch (err) {
    toast.error(t('st.sess.revokeFailed'))
  }
}

function revokeOtherSessions() {
  confirmModal.title = t('st.sess.revokeAllTitle')
  confirmModal.message = t('st.sess.revokeAllMsg')
  confirmModal.confirmText = t('st.sess.revokeAll')
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      const res = await apiClient.post<{ message: string; revoked_count: number }>('/auth/sessions/revoke-others/')
      await fetchSessions()
      await fetchAuditLogs()
      toast.info(res.data.message || 'Other sessions revoked')
    } catch (err) {
      toast.error(t('st.sess.revokeFailed'))
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
    toast.success(t('st.inv.createdToast'))
  } catch (err) {
    toast.error('Failed to create invite code')
  }
}

function deleteInviteCode(id: string, code: string) {
  confirmModal.title = t('st.inv.deleteTitle')
  confirmModal.message = t('st.inv.deleteMsg', { code })
  confirmModal.confirmText = t('st.inv.deleteConfirm')
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await apiClient.delete(`/auth/invites/${id}/`)
      await fetchInvites()
      await fetchAuditLogs()
      toast.info(t('st.inv.deletedToast', { code }))
    } catch (err) {
      toast.error(t('st.inv.createFailed'))
    }
  }
  confirmModal.isOpen = true
}

function copyCode(code: string) {
  navigator.clipboard.writeText(code)
  toast.success(t('st.inv.copiedToast', { code }))
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
  return formatLocaleDate(d, 'datetime')
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
  confirmModal.title = t('st.drive.disconnectTitle')
  confirmModal.message = t('st.drive.disconnectMsg')
  confirmModal.confirmText = t('st.tg.disconnect')
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
