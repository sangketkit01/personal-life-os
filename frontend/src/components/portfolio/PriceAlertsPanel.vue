<template>
  <section class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-4 space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div><h2 class="text-sm font-semibold text-zinc-200">เตือนราคา</h2><p class="text-xs text-zinc-500 mt-1">แจ้งครั้งเดียวเมื่อราคาเข้าเงื่อนไขในช่วงซื้อขายปกติ · Crypto ตรวจได้ตลอดวัน</p></div>
      <button type="button" @click="begin()" class="rounded bg-zinc-100 text-zinc-950 px-3 py-1.5 text-xs">เพิ่มเงื่อนไข</button>
    </div>
    <p class="text-xs text-zinc-500">ส่งผ่าน Telegram · <RouterLink to="/settings" class="underline text-zinc-400">เชื่อมต่อและตั้งค่าการแจ้งเตือน</RouterLink></p>
    <form v-if="editing" @submit.prevent="save" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 p-3 border border-zinc-800 rounded-lg">
      <label class="text-xs text-zinc-400">Ticker<input v-model="form.ticker" required placeholder="Ticker" class="mt-1 w-full min-w-0 bg-zinc-950 border border-zinc-700 rounded p-2 text-zinc-100" /></label>
      <label class="text-xs text-zinc-400">สกุลเงิน<select v-model="form.currency" required class="mt-1 w-full bg-zinc-950 border border-zinc-700 rounded p-2 text-zinc-100"><option value="" disabled>เลือกสกุลเงิน</option><option>THB</option><option>USD</option></select></label>
      <label class="text-xs text-zinc-400">เงื่อนไข<select v-model="form.condition" required class="mt-1 w-full bg-zinc-950 border border-zinc-700 rounded p-2 text-zinc-100"><option value="" disabled>เลือกเงื่อนไข</option><option value="GTE">ราคา ≥ เป้าหมาย</option><option value="LTE">ราคา ≤ เป้าหมาย</option></select></label>
      <label class="text-xs text-zinc-400">ราคาเป้าหมาย<input v-model="form.target_price" required type="number" min="0.00000001" step="0.00000001" placeholder="ราคา" class="mt-1 w-full bg-zinc-950 border border-zinc-700 rounded p-2 text-zinc-100" /></label>
      <div class="flex items-end gap-2"><button :disabled="busy" class="rounded bg-zinc-100 text-zinc-950 px-3 py-2 text-xs disabled:opacity-50">{{ busy ? 'กำลังบันทึก…' : 'บันทึก' }}</button><button type="button" :disabled="busy" @click="editing = false" class="text-xs text-zinc-400 p-2">ยกเลิก</button></div>
    </form>
    <p v-if="error" role="alert" class="text-xs text-rose-400">{{ error }}</p>
    <p v-if="loading" class="text-xs text-zinc-500">กำลังโหลดเงื่อนไข…</p>
    <p v-else-if="!rules.length" class="text-xs text-zinc-500">ยังไม่มีเงื่อนไขเตือนราคา</p>
    <div v-for="rule in rules" :key="rule.id" class="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-800 pt-3 text-xs">
      <div><RouterLink :to="`/portfolio/asset/${encodeURIComponent(rule.ticker)}`" class="text-zinc-100 font-semibold">{{ rule.ticker }}</RouterLink><span class="text-zinc-400 ml-2">{{ rule.condition === 'GTE' ? '≥' : '≤' }} {{ rule.currency }} {{ Number(rule.target_price).toLocaleString(undefined, { maximumFractionDigits: 8 }) }}</span><span class="ml-2" :class="rule.is_active ? 'text-emerald-400' : 'text-zinc-500'">{{ rule.is_active ? 'รอตรวจราคา' : rule.triggered_at ? 'แจ้งแล้ว' : 'พักอยู่' }}</span></div>
      <div class="flex flex-wrap gap-3"><button :disabled="busy" @click="begin(rule)" class="text-zinc-300">แก้ไข</button><button :disabled="busy" @click="toggle(rule)" class="text-zinc-300">{{ rule.is_active ? 'พัก' : 'เปิดใช้งานใหม่' }}</button><button :disabled="busy" @click="deleting = rule" class="text-rose-400">ลบ</button></div>
    </div>
    <ConfirmModal :is-open="!!deleting" title="ลบเงื่อนไขเตือนราคา" :message="`ลบเงื่อนไขของ ${deleting?.ticker || ''}?`" confirm-text="ลบ" :is-danger="true" :is-loading="busy" :error-message="error" @cancel="deleting = null" @confirm="remove" />
  </section>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import api from '../../api/client'
import ConfirmModal from '../common/ConfirmModal.vue'
import { useToastStore } from '../../stores/toast'
type Rule = { id: string; ticker: string; currency: string; condition: string; target_price: string; is_active: boolean; triggered_at: string | null }
const props = defineProps<{ ticker?: string; currency?: string }>()
const toast = useToastStore()
const rules = ref<Rule[]>([]), loading = ref(false), busy = ref(false), editing = ref(false), error = ref('')
const editingId = ref(''), deleting = ref<Rule | null>(null)
const form = ref({ ticker: '', currency: '', condition: '', target_price: '' })
let generation = 0
async function load() {
  const request = ++generation; loading.value = true; error.value = ''
  try { const res = await api.get('/portfolio/price-alerts/', { params: props.ticker ? { ticker: props.ticker } : {} }); if (request === generation) rules.value = res.data }
  catch { if (request === generation) error.value = 'โหลดเงื่อนไขไม่สำเร็จ' }
  finally { if (request === generation) loading.value = false }
}
function begin(rule?: Rule) { editingId.value = rule?.id || ''; form.value = { ticker: rule?.ticker || props.ticker || '', currency: rule?.currency || props.currency || '', condition: rule?.condition || '', target_price: rule?.target_price || '' }; error.value = ''; editing.value = true }
async function mutate(action: () => Promise<unknown>) {
  if (busy.value) return; busy.value = true; error.value = ''
  try { await action(); toast.success('บันทึกเงื่อนไขแล้ว'); await load(); return true }
  catch (e: any) { error.value = e.response?.data?.detail || JSON.stringify(e.response?.data || {}) || 'บันทึกไม่สำเร็จ'; return false }
  finally { busy.value = false }
}
async function save() { const data = { ...form.value, ticker: form.value.ticker.trim().toUpperCase() }; if (await mutate(() => editingId.value ? api.patch(`/portfolio/price-alerts/${editingId.value}/`, data) : api.post('/portfolio/price-alerts/', data))) editing.value = false }
async function toggle(rule: Rule) { await mutate(() => api.patch(`/portfolio/price-alerts/${rule.id}/`, { is_active: !rule.is_active })) }
async function remove() { if (deleting.value && await mutate(() => api.delete(`/portfolio/price-alerts/${deleting.value!.id}/`))) deleting.value = null }
watch(() => props.ticker, () => { editing.value = false; void load() }, { immediate: true })
</script>
