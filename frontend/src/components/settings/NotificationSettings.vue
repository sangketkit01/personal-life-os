<template>
  <section class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-4 space-y-4">
    <h2 class="text-sm font-semibold text-zinc-200">Telegram · การแจ้งเตือน</h2>
    <p v-if="loading" class="text-xs text-zinc-500">กำลังโหลดการตั้งค่า…</p>
    <form v-else-if="prefs" @submit.prevent="save" class="space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3"><label v-for="item in categories" :key="item.key" class="text-xs text-zinc-300 flex gap-2 items-center"><input type="checkbox" v-model="prefs[item.key]" class="accent-zinc-300" />{{ item.label }}</label></div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <label class="text-xs text-zinc-400">เวลาสรุปเช้า<input v-model="prefs.briefing_time" required type="time" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 p-2 text-zinc-100" /></label>
        <label class="text-xs text-zinc-400">เขตเวลา<input v-model="prefs.timezone" required placeholder="Asia/Bangkok" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 p-2 text-zinc-100" /></label>
        <label class="text-xs text-zinc-400">เริ่มช่วงเงียบ<input v-model="prefs.quiet_start" type="time" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 p-2 text-zinc-100" /></label>
        <label class="text-xs text-zinc-400">สิ้นสุดช่วงเงียบ<input v-model="prefs.quiet_end" type="time" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 p-2 text-zinc-100" /></label>
      </div>
      <p class="text-xs text-zinc-500">ข้อความอัตโนมัติจะรอส่งหลังช่วงเงียบ เงื่อนไขที่หมดอายุหรือรายการที่จัดการแล้วจะถูกข้าม</p>
      <p v-if="error" role="alert" class="text-xs text-rose-400">{{ error }}</p>
      <button :disabled="saving" class="rounded bg-zinc-100 px-3 py-1.5 text-xs text-zinc-950 disabled:opacity-50">{{ saving ? 'กำลังบันทึก…' : 'บันทึกการแจ้งเตือน' }}</button>
    </form>
    <button v-else type="button" @click="load" class="text-xs text-zinc-300">โหลดอีกครั้ง</button>
    <details v-if="deliveries.length" class="border-t border-zinc-800 pt-3"><summary class="text-xs text-zinc-400 cursor-pointer">ประวัติการส่งล่าสุด</summary><div v-for="row in deliveries" :key="row.id" class="flex flex-wrap justify-between gap-2 text-xs text-zinc-400 border-b border-zinc-800 py-2"><span>{{ row.category }} · {{ new Date(row.created_at).toLocaleString() }}</span><span :title="row.error">{{ statuses[row.status] || row.status }}</span></div></details>
  </section>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api/client'
import { useToastStore } from '../../stores/toast'
const toast = useToastStore(), prefs = ref<Record<string, any> | null>(null), deliveries = ref<any[]>([]), loading = ref(true), saving = ref(false), error = ref('')
const categories = [{ key: 'briefing', label: 'สรุปเช้า' }, { key: 'bills', label: 'บิลและรายการครบกำหนด' }, { key: 'tasks', label: 'งานและเอกสาร' }, { key: 'calendar', label: 'นัดหมายล่วงหน้า 30 นาที' }, { key: 'portfolio_news', label: 'ข่าวหุ้นที่ถือในสรุปเช้า' }, { key: 'watchlist_news', label: 'รวมข่าว Watchlist ในสรุปเช้า' }, { key: 'market_close', label: 'สรุปพอร์ตหลังตลาดปิด (SET/US)' }, { key: 'price_alerts', label: 'เงื่อนไขเตือนราคา' }, { key: 'infrastructure', label: 'MA และ Infrastructure' }]
const statuses: Record<string, string> = { PENDING: 'รอส่ง', SENDING: 'กำลังส่ง', SENT: 'ส่งแล้ว', FAILED: 'ส่งไม่สำเร็จ', UNKNOWN: 'ยังยืนยันผลการส่งไม่ได้', SKIPPED: 'ข้ามแล้ว' }
async function load() { loading.value = true; error.value = ''; try { const { data } = await api.get('/bot/notifications/'); prefs.value = data.preferences; deliveries.value = data.deliveries } catch { error.value = 'โหลดการตั้งค่าไม่สำเร็จ' } finally { loading.value = false } }
async function save() { if (saving.value || !prefs.value) return; saving.value = true; error.value = ''; try { const { data } = await api.patch('/bot/notifications/', { ...prefs.value, quiet_start: prefs.value.quiet_start || null, quiet_end: prefs.value.quiet_end || null }); prefs.value = data; toast.success('บันทึกการแจ้งเตือนแล้ว') } catch (e: any) { error.value = e.response?.data?.detail || JSON.stringify(e.response?.data || {}) || 'บันทึกไม่สำเร็จ' } finally { saving.value = false } }
onMounted(load)
</script>
