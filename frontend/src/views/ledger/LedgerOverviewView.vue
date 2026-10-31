<template>
  <div class="max-w-7xl mx-auto space-y-6 pb-16">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-zinc-800 pb-5">
      <div><h1 class="text-lg font-semibold text-zinc-100">รายรับและรายจ่าย</h1><p class="text-xs text-zinc-500 mt-1">ดูรายรับ ค่าใช้จ่ายส่วนตัว และเงินพร้อมใช้ พร้อมกดดูที่มาของทุกยอด</p></div>
      <div class="flex flex-wrap items-end gap-2">
        <label class="text-[10px] text-zinc-400">เดือน<input v-model="month" type="month" min="1900-01" max="9998-12" class="block mt-1 rounded border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-100" /></label>
        <label class="text-[10px] text-zinc-400">สกุลเงิน<select v-model="currency" class="block mt-1 rounded border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-100"><option v-for="code in currencies" :key="code">{{ code }}</option></select></label>
        <button type="button" @click="showTransfer = true" class="rounded border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300">โอนเงิน</button>
        <button type="button" @click="editing = null; showTransaction = true" class="rounded bg-zinc-100 text-zinc-950 px-3 py-1.5 text-xs font-semibold">+ บันทึกรายการ</button>
      </div>
    </header>

    <div v-if="error" role="alert" class="rounded-lg border border-rose-500/30 p-4 text-xs text-rose-300 flex flex-wrap justify-between gap-3"><span>{{ error }}</span><button type="button" @click="load" class="underline">ลองอีกครั้ง</button></div>
    <div v-if="loading && !data" role="status" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"><span class="sr-only">กำลังโหลดรายงาน</span><div v-for="n in 4" :key="n" class="h-32 rounded-xl bg-zinc-900 animate-pulse"></div></div>

    <template v-if="data">
      <div class="flex flex-wrap justify-between gap-2 text-[11px] text-zinc-500"><span>รายการที่เกิดขึ้น {{ data.period.start }} ถึง {{ data.period.end < data.period.start ? 'ยังไม่เริ่มช่วงเวลา' : data.period.end }} · {{ data.currency }} แยกจากสกุลอื่น</span><span role="status">{{ loading ? 'กำลังอัปเดต…' : `อัปเดต ${new Date(data.as_of).toLocaleString('th-TH')}` }}</span></div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <RouterLink v-for="card in metricCards" :key="card.key" :to="transactionsLink(card.kind)" class="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 hover:border-zinc-600 focus-visible:outline focus-visible:outline-emerald-400">
          <span class="block text-xs text-zinc-400">{{ card.label }} ↗</span><strong class="block mt-3 text-xl font-mono tabular-nums break-words" :class="card.key === 'expense' ? 'text-amber-300' : Number(data.metrics[card.key]) < 0 ? 'text-rose-300' : 'text-zinc-100'">{{ money(data.metrics[card.key]) }}</strong>
          <span class="block mt-3 text-[10px] text-zinc-500">{{ comparison(card.key) }}</span>
        </RouterLink>
        <button type="button" @click="accountsSection?.scrollIntoView({ behavior: 'smooth', block: 'center' })" class="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 text-left hover:border-zinc-600"><span class="block text-xs text-zinc-400">เงินพร้อมใช้ตอนนี้ ↓</span><strong class="block mt-3 text-xl text-zinc-100 font-mono tabular-nums break-words">{{ money(data.liquid_balance) }}</strong><span class="block mt-3 text-[10px] text-zinc-500">ธนาคาร เงินสด และ E-wallet ที่ใช้งานอยู่ · ณ ปัจจุบัน</span></button>
      </div>

      <section class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 space-y-4">
        <div class="flex flex-wrap justify-between gap-3 items-center"><h2 class="text-sm font-semibold text-zinc-100">แนวโน้มรายรับและรายจ่าย</h2><div class="flex flex-wrap gap-2 text-xs"><button v-for="mode in chartModes" :key="mode.key" type="button" @click="chartMode = mode.key" :aria-pressed="chartMode === mode.key" class="rounded px-2 py-1 border" :class="chartMode === mode.key ? 'border-zinc-500 text-zinc-100' : 'border-zinc-800 text-zinc-500'">{{ mode.label }}</button></div></div>
        <DashboardChart :points="chartPoints" :currency="data.currency" @select="openChartPeriod" />
        <p class="text-[10px] text-zinc-500">กดแท่งกราฟเพื่อดูรายการ · เดือนปัจจุบันแสดงถึงวันนี้ และเทียบเดือนก่อนตามจำนวนวันที่เท่ากัน</p>
      </section>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DashboardCategories title="รายรับมาจากไหน" :groups="data.income_sources" :currency="data.currency" income @select="id => openCategory('INCOME', id)" />
        <DashboardCategories title="ใช้จ่ายกับอะไร" :groups="data.expense_categories" :currency="data.currency" @select="id => openCategory('EXPENSE', id)" />
      </div>

      <section class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 space-y-4">
        <div class="flex flex-wrap justify-between gap-2"><div><h2 class="text-sm text-zinc-100 font-semibold">เงินเข้าออกจากบัญชีที่พร้อมใช้</h2><p class="text-[11px] text-zinc-500 mt-1">รวมเงินกู้ เงินรับคืน เงินลงทุน และชำระบัตร · เงินโอนระหว่างบัญชีที่พร้อมใช้หักล้างกัน</p></div><RouterLink :to="transactionsLink('CASH')" class="text-xs text-zinc-300 underline">ดูรายการ</RouterLink></div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs"><p class="text-zinc-400">เงินเข้า<strong class="block text-lg text-emerald-300 mt-1 font-mono">{{ money(data.metrics.cash_in) }}</strong></p><p class="text-zinc-400">เงินออก<strong class="block text-lg text-amber-300 mt-1 font-mono">{{ money(data.metrics.cash_out) }}</strong></p><p class="text-zinc-400">กระแสเงินสดสุทธิ<strong class="block text-lg mt-1 font-mono" :class="Number(data.metrics.cash_flow) < 0 ? 'text-rose-300' : 'text-zinc-100'">{{ money(data.metrics.cash_flow) }}</strong></p></div>
        <details class="text-xs text-zinc-400"><summary class="cursor-pointer">วิธีนับยอด</summary><ul class="list-disc pl-5 mt-2 space-y-1"><li>ค่าใช้จ่ายใช้เฉพาะส่วนของเรา เงินที่สำรองให้เพื่อนแสดงในเงินออกเต็มจำนวน</li><li>เงินคืนจาก split และเงินต้นเงินกู้แยกจากรายได้</li><li>ซื้อผ่านบัตรเป็นค่าใช้จ่ายตอนซื้อ ชำระบัตรด้วยการโอนระหว่างบัญชีจึงไม่เป็นรายจ่ายซ้ำ</li><li>เงินลงทุนแยกจากรายรับรายจ่าย เลือกวิธีนับได้ตอนบันทึกหรือแก้ไขรายการ</li><li>รายงานอิงรายการ Ledger ที่บันทึกไว้ และไม่รวมธุรกรรมที่ลงวันที่ในอนาคต</li></ul></details>
      </section>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 space-y-4">
          <div><h2 class="text-sm text-zinc-100 font-semibold">บิลที่กำลังจะถึงและเงินหลังบิล</h2><p class="text-[11px] text-zinc-500 mt-1">ณ {{ data.forecast.as_of }} · รวมบิลค้าง · ประมาณการจากภาระที่บันทึก ไม่รวมรายรับอนาคต</p></div>
          <div class="flex gap-2"><button v-for="days in ['7','30']" :key="days" type="button" @click="forecastDays = days" :aria-pressed="forecastDays === days" class="rounded border px-3 py-1 text-xs" :class="forecastDays === days ? 'border-zinc-500 text-zinc-100' : 'border-zinc-800 text-zinc-500'">{{ days }} วัน</button></div>
          <div class="rounded-lg bg-zinc-950/60 p-3 text-xs text-zinc-400">บิลที่รู้ยอด {{ money(forecastWindow?.known_due || 0) }}<strong class="block text-lg mt-1 font-mono" :class="Number(forecastWindow?.remaining) < 0 ? 'text-rose-300' : 'text-zinc-100'">เหลือ {{ money(forecastWindow?.remaining || 0) }}</strong><p v-if="forecastWindow?.pending_dynamic_count" class="mt-2 text-amber-300">ยังไม่รวมยอด Dynamic ที่รอกรอก {{ forecastWindow.pending_dynamic_count }} รายการ</p><p v-if="Number(forecastWindow?.conditional_amount)" class="mt-2 text-amber-300">Free trial อาจเรียกเก็บเพิ่ม {{ money(forecastWindow?.conditional_amount || 0) }} หากไม่ยกเลิก</p></div>
          <p v-if="!forecastBills.length" class="text-xs text-zinc-500">ไม่มีบิลที่บันทึกไว้ในช่วงนี้</p>
          <ul class="max-h-72 overflow-y-auto divide-y divide-zinc-800"><li v-for="bill in forecastBills" :key="`${bill.id}:${bill.due_date}`"><RouterLink :to="bill.path" class="block py-3 hover:bg-zinc-800/40 rounded"><span class="flex justify-between gap-2 text-xs text-zinc-200"><span class="min-w-0 break-words">{{ bill.title }}</span><span class="shrink-0">{{ money(bill.known_amount) }}{{ bill.pending_dynamic_count ? ' + รอกรอก' : '' }}</span></span><span class="block mt-1 text-[10px] text-zinc-500">{{ bill.due_date }}{{ bill.projected ? ' · รอบถัดไปประมาณการ' : '' }}{{ bill.conditional ? ' · หากไม่ยกเลิก' : '' }}</span></RouterLink></li></ul>
          <p class="text-[10px] text-zinc-500">ภาระที่ยังไม่มีวันครบกำหนดไม่รวมในประมาณการ · บิลที่ค้างนับเฉพาะรอบค้างที่บันทึกไว้</p>
        </section>
        <section class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 space-y-4">
          <div class="flex justify-between gap-2"><h2 class="text-sm text-zinc-100 font-semibold">งบประมาณ {{ month }}</h2><RouterLink :to="{ path:'/ledger/budgets', query:{month,currency} }" class="text-xs text-zinc-300 underline">จัดการงบ</RouterLink></div>
          <div v-if="!data.budgets.length" class="py-8 text-center text-xs text-zinc-500">ยังไม่ได้ตั้งงบในเดือนและสกุลเงินนี้<RouterLink :to="{ path:'/ledger/budgets', query:{month,currency} }" class="block mt-3 text-zinc-200 underline">ตั้งงบประมาณ</RouterLink></div>
          <button v-for="budget in data.budgets" :key="budget.id" type="button" @click="openCategory('EXPENSE',budget.category)" class="block w-full text-left rounded hover:bg-zinc-800/40 py-1"><span class="flex justify-between gap-2 text-xs text-zinc-200"><span>{{ budget.name }}</span><span>{{ money(budget.spent) }} / {{ money(budget.limit) }}</span></span><span class="block h-1.5 bg-zinc-800 rounded mt-2 overflow-hidden"><span class="block h-full" :class="budget.usage_pct > 100 ? 'bg-rose-400' : 'bg-zinc-400'" :style="{width:`${Math.min(100,budget.usage_pct)}%`}"></span></span><span class="block text-[10px] mt-1" :class="budget.usage_pct > 100 ? 'text-rose-300' : 'text-zinc-500'">{{ budget.usage_pct.toFixed(1) }}% · {{ Number(budget.remaining) < 0 ? 'เกินงบ' : 'เหลือ' }} {{ money(Math.abs(Number(budget.remaining))) }}</span></button>
          <p v-if="data.budgets.length" class="text-[10px] text-zinc-500">งบหมวดหลักรวมหมวดย่อย · ไม่รวมยอดทุกงบเข้าด้วยกัน เพื่อไม่ให้งบที่ซ้อนกันถูกนับซ้ำ</p>
        </section>
      </div>

      <section ref="accountsSection" class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 space-y-4">
        <div class="flex justify-between gap-2"><h2 class="text-sm text-zinc-100 font-semibold">บัญชี ณ ปัจจุบัน · {{ data.currency }}</h2><RouterLink to="/ledger/accounts" class="text-xs text-zinc-300 underline">จัดการบัญชี</RouterLink></div>
        <div class="flex flex-wrap gap-4 text-xs text-zinc-400"><span>หนี้บัตร {{ money(data.credit_debt) }}</span><RouterLink to="/ledger/splits" class="underline">เงินรอคืนจาก split {{ money(data.pending_split_amount) }}</RouterLink></div>
        <p v-if="!data.accounts.length" class="text-xs text-zinc-500">ยังไม่มีบัญชีในสกุลเงินนี้</p><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"><RouterLink v-for="account in data.accounts" :key="account.id" :to="`/ledger/accounts/${account.id}`" class="rounded-lg border border-zinc-800 p-3 hover:border-zinc-600"><span class="block text-xs text-zinc-200 truncate">{{ account.name }}</span><span class="block text-[10px] mt-1 text-zinc-500">{{ account.type }}</span><strong class="block mt-3 font-mono text-sm text-zinc-100">{{ money(account.balance) }}</strong></RouterLink></div>
      </section>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 space-y-3"><h2 class="text-sm text-zinc-100 font-semibold">รายการที่ควรตรวจ</h2><RouterLink v-if="data.uncategorized_count" :to="transactionsLink(undefined, {uncategorized:'true'})" class="block text-xs text-amber-300 underline">ยังไม่จัดหมวด {{ data.uncategorized_count }} รายการ</RouterLink><h3 class="text-xs text-zinc-400">ค่าใช้จ่ายส่วนตัวสูงสุดในช่วงนี้</h3><p v-if="!data.largest_expenses.length" class="text-xs text-zinc-500">ไม่มีค่าใช้จ่ายในช่วงนี้</p><button v-for="tx in data.largest_expenses" :key="tx.id" type="button" :disabled="!!opening" @click="editTransaction(tx.id)" class="flex w-full justify-between gap-3 text-left text-xs py-2 rounded hover:bg-zinc-800/40 disabled:opacity-50"><span class="text-zinc-200 break-words">{{ tx.title }}<span class="block text-[10px] text-zinc-500 mt-1">{{ tx.date }} · {{ tx.category_name }}</span></span><span class="text-amber-300 shrink-0">{{ money(tx.amount) }}</span></button></section>
        <section class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 space-y-3"><div class="flex justify-between gap-2"><h2 class="text-sm text-zinc-100 font-semibold">รายการล่าสุดในช่วงนี้</h2><RouterLink :to="transactionsLink()" class="text-xs text-zinc-300 underline">ดูทั้งหมด</RouterLink></div><p v-if="!data.recent.length" class="text-xs text-zinc-500 py-8">ยังไม่มีรายการที่บันทึกในช่วงนี้</p><button v-for="tx in data.recent" :key="tx.id" type="button" :disabled="!!opening" @click="editTransaction(tx.id)" class="flex w-full justify-between gap-3 text-left text-xs py-2 rounded hover:bg-zinc-800/40 disabled:opacity-50"><span class="text-zinc-200 break-words">{{ tx.title }}<span class="block text-[10px] text-zinc-500 mt-1">{{ tx.date }} · {{ tx.account_name }} · {{ kindLabels[tx.kind] || tx.kind }}</span></span><span class="text-zinc-300 shrink-0">{{ tx.transaction_type === 'INFLOW' ? '+' : '−' }}{{ money(tx.gross_amount) }}</span></button><p v-if="opening" role="status" class="text-xs text-zinc-500">กำลังเปิดรายการ…</p></section>
      </div>
    </template>
    <TransactionModal :is-open="showTransaction" :transaction-to-edit="editing" @close="showTransaction = false; editing = null" @created="refresh" @updated="refresh" />
    <TransferModal :is-open="showTransfer" @close="showTransfer = false" @transferred="refresh" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ledgerApi } from '../../api/ledger'
import { useLedgerStore } from '../../stores/ledger'
import { useToastStore } from '../../stores/toast'
import type { LedgerDashboard, LedgerTransaction } from '../../types/ledger'
import TransactionModal from '../../components/ledger/TransactionModal.vue'
import TransferModal from '../../components/ledger/TransferModal.vue'
import DashboardChart from '../../components/ledger/DashboardChart.vue'
import DashboardCategories from '../../components/ledger/DashboardCategories.vue'
const router = useRouter(), store = useLedgerStore(), toast = useToastStore()
const now = new Date()
const month = ref(`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`), currency = ref('THB')
const data = ref<LedgerDashboard | null>(null), loading = ref(false), error = ref(''), chartMode = ref('daily'), forecastDays = ref('7')
const showTransaction = ref(false), showTransfer = ref(false), editing = ref<LedgerTransaction | null>(null), opening = ref(''), accountsSection = ref<HTMLElement | null>(null)
const currencies = computed(() => [...new Set([currency.value, ...(data.value?.currencies || []), ...store.accounts.map(a => a.currency)])].sort())
const kindLabels: Record<string,string> = { INCOME:'รายรับ', EXPENSE:'ค่าใช้จ่าย', TRANSFER:'โอนเงิน', LOAN:'เงินต้นเงินกู้', INVESTMENT:'เงินลงทุน', REIMBURSEMENT:'เงินรับคืน', CARD_PAYMENT:'ชำระบัตร' }
const metricCards = [{key:'income',kind:'INCOME',label:'รายรับจริง'}, {key:'expense',kind:'EXPENSE',label:'ค่าใช้จ่ายส่วนตัว'}, {key:'surplus',kind:'SURPLUS',label:'ส่วนต่างรายรับ–รายจ่าย'}] as const
const chartModes = [{ key:'daily',label:'รายวัน' },{ key:'6',label:'6 เดือน' },{ key:'12',label:'12 เดือน' }]
const chartPoints = computed(() => !data.value ? [] : chartMode.value === 'daily' ? data.value.daily.map(p => ({...p,label:p.date.slice(8)})) : data.value.history.slice(-Number(chartMode.value)).map(p => ({...p,label:p.month})))
const forecastWindow = computed(() => data.value?.forecast.windows[forecastDays.value])
const forecastBills = computed(() => {
  if (!data.value) return []
  const end = new Date(data.value.forecast.as_of+'T00:00:00Z'); end.setUTCDate(end.getUTCDate()+Number(forecastDays.value))
  return data.value.forecast.bills.filter(b => b.due_date <= end.toISOString().slice(0,10))
})
const money = (value: string | number) => `${data.value?.currency || currency.value} ${Number(value).toLocaleString('th-TH', { minimumFractionDigits:2,maximumFractionDigits:2 })}`
function comparison(key: 'income' | 'expense' | 'surplus') {
  if (!data.value) return ''
  const current = Number(data.value.metrics[key]), previous = Number(data.value.comparison[key]), delta = current-previous
  return `${delta >= 0 ? '+' : '−'}${money(Math.abs(delta))} เทียบ ${data.value.period.previous_start} ถึง ${data.value.period.previous_end}`
}
function transactionsLink(kind?: string, extra: Record<string,string> = {}) {
  return { path:'/ledger/transactions', query:{ start_date:data.value?.period.start || month.value+'-01', end_date:data.value?.period.end || month.value+'-01', currency:currency.value, ...(kind ? {report_kind:kind} : {}), ...extra } }
}
function openCategory(kind: string, id: string | null) { void router.push(transactionsLink(kind, id ? {category:id} : {uncategorized:'true'})) }
function openChartPeriod(index: number) {
  if (!data.value) return
  if (chartMode.value === 'daily') { const day=data.value.daily[index]?.date; if(day) void router.push(transactionsLink('SURPLUS',{start_date:day,end_date:day})); return }
  const row=data.value.history.slice(-Number(chartMode.value))[index]; if (!row) return
  const [year, part]=row.month.split('-').map(Number)
  const end=`${row.month}-${String(new Date(year!,part!,0).getDate()).padStart(2,'0')}`
  void router.push(transactionsLink('SURPLUS',{start_date:row.month+'-01',end_date:end < data.value.period.end ? end : data.value.period.end}))
}
let generation = 0, activeScope = ''
async function load() {
  const scope=`${month.value}:${currency.value}`, request=++generation
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(month.value) || Number(month.value.slice(0,4)) < 1900 || Number(month.value.slice(0,4)) > 9998) {
    data.value=null; loading.value=false; error.value='กรุณาเลือกเดือนที่ต้องการดูรายงาน'; return
  }
  if (scope !== activeScope) data.value=null; activeScope=scope; loading.value=true; error.value=''
  try { const result=await ledgerApi.getDashboard(month.value,currency.value); if(request===generation) data.value=result }
  catch { if(request===generation) error.value='โหลด Dashboard ไม่สำเร็จ กรุณาลองอีกครั้ง' }
  finally { if(request===generation) loading.value=false }
}
async function refresh() { await Promise.all([load(),store.fetchAccounts()]) }
async function editTransaction(id: string) {
  if(opening.value) return; opening.value=id
  try { editing.value=await ledgerApi.getTransaction(id); showTransaction.value=true }
  catch { toast.error('เปิดรายการไม่สำเร็จ') } finally { opening.value='' }
}
watch([month,currency],load)
onMounted(() => { void load(); void store.fetchAccounts(); void store.fetchCategories() })
onUnmounted(() => { generation++ })
</script>
