<template>
  <div class="max-w-5xl mx-auto space-y-6 font-sans">
    <!-- Breadcrumb & Back Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          @click="router.push('/portfolio/executions')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Trade Executions Log"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-base font-semibold text-zinc-100 tracking-tight">CSV Statement Import Engine</h1>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800 font-medium">
              BULK INGESTION
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-0.5">
            Bulk import historical transactions from brokerage exports (Dime!, SET Streaming, Bitkub, or standard CSV).
          </p>
        </div>
      </div>
    </div>

    <!-- Configuration Strip: Target Portfolio & Broker Preset -->
    <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
      <div class="flex items-center justify-between pb-2 border-b border-zinc-800/60">
        <div class="flex items-center gap-2">
          <FileSpreadsheet class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Import Parameters
          </h2>
        </div>

        <button
          type="button"
          @click="downloadSampleCsv"
          class="text-xs font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition-colors"
        >
          <Download class="w-3.5 h-3.5 text-zinc-500" />
          <span>Download Sample CSV Template</span>
        </button>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
        <!-- Target Portfolio Selector -->
        <div class="space-y-1.5">
          <label class="block text-zinc-400 text-xs">
            Target Destination Portfolio <span class="text-rose-400">*</span>
          </label>
          <select
            v-model="selectedPortfolioId"
            class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-100 outline-none focus:border-zinc-600 transition-colors"
          >
            <option
              v-for="p in portfolioStore.portfolios"
              :key="p.id"
              :value="p.id"
            >
              {{ p.name }} ({{ p.currency }}) {{ p.is_default ? '• Default' : '' }}
            </option>
          </select>
          <span class="text-[10px] text-zinc-500 block">
            All imported trades will be attributed to this brokerage account.
          </span>
        </div>

        <!-- Broker Parser Preset -->
        <div class="space-y-1.5">
          <label class="block text-zinc-400 text-xs">
            Brokerage Export Format
          </label>
          <select
            v-model="selectedFormat"
            class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-100 outline-none focus:border-zinc-600 transition-colors"
          >
            <option value="AUTO">Auto-Detect Statement Format</option>
            <option value="DIME">Dime! US Shares Statement CSV</option>
            <option value="STREAMING">SET Streaming / InnovestX CSV</option>
            <option value="BITKUB">Bitkub / Digital Assets CSV</option>
            <option value="GENERIC">Generic Portfolio CSV (Standard)</option>
          </select>
          <span class="text-[10px] text-zinc-500 block">
            Engine automatically maps columns: Date, Action, Symbol, Volume, Price, Fee.
          </span>
        </div>
      </div>
    </div>

    <!-- Drag & Drop Upload Zone -->
    <div
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      class="p-8 rounded-xl border border-dashed text-center transition-all cursor-pointer flex flex-col items-center justify-center space-y-3"
      :class="isDragging ? 'bg-zinc-900 border-zinc-500 shadow-sm' : 'bg-zinc-900/20 border-zinc-800 hover:border-zinc-700'"
      @click="triggerFileInput"
    >
      <input
        ref="fileInputRef"
        type="file"
        accept=".csv,.txt"
        class="hidden"
        @change="handleFileSelect"
      />

      <div class="w-12 h-12 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400">
        <Upload class="w-6 h-6" />
      </div>

      <div>
        <div class="text-sm font-semibold text-zinc-200 font-sans">
          {{ selectedFileName || 'Choose or drop your brokerage statement CSV here' }}
        </div>
        <p class="text-xs text-zinc-500 font-mono mt-1">
          Supports .CSV files exported from Dime!, InnovestX, SET Streaming, Bitkub, Binance
        </p>
      </div>

      <div v-if="parsedTrades.length > 0" class="inline-flex items-center gap-2 px-3 py-1 rounded bg-zinc-900 border border-zinc-800 text-xs font-mono text-emerald-400">
        <Check class="w-3.5 h-3.5" />
        <span>{{ parsedTrades.length }} trades ready to review</span>
      </div>
    </div>

    <!-- Interactive Parsed Preview Table -->
    <div v-if="parsedTrades.length > 0" class="space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/80">
        <div>
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono flex items-center gap-2">
            <span>Staged Transactions Preview</span>
            <span class="text-[11px] text-zinc-500 font-normal">({{ parsedTrades.length }} records parsed)</span>
          </h2>
          <p class="text-xs text-zinc-500 mt-0.5">
            Verify trade rows before committing. Existing identical records will be automatically skipped by deduplication.
          </p>
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            @click="clearParsed"
            class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-400 hover:text-zinc-200 font-mono transition-colors"
          >
            Clear
          </button>
          <button
            type="button"
            :disabled="isImporting"
            @click="commitImport"
            class="px-4 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            <Check class="w-3.5 h-3.5 text-zinc-950" />
            <span>{{ isImporting ? 'Ingesting...' : `Import ${parsedTrades.length} Trades` }}</span>
          </button>
        </div>
      </div>

      <!-- Preview Table -->
      <div class="rounded-xl border border-zinc-800/80 overflow-hidden bg-zinc-900/30 shadow-sm">
        <div class="overflow-x-auto max-h-96">
          <table class="w-full text-left text-xs font-mono">
            <thead class="sticky top-0 z-10">
              <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-950">
                <th class="py-2.5 pl-4">#</th>
                <th class="py-2.5">Date & Time</th>
                <th class="py-2.5">Action</th>
                <th class="py-2.5">Ticker</th>
                <th class="py-2.5 text-right">Shares</th>
                <th class="py-2.5 text-right">Price</th>
                <th class="py-2.5 text-right">Fee</th>
                <th class="py-2.5 text-right pr-4">Total Amount</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr
                v-for="(trade, idx) in parsedTrades"
                :key="idx"
                class="hover:bg-zinc-900/40 transition-colors"
              >
                <td class="py-2.5 pl-4 text-zinc-500">{{ idx + 1 }}</td>
                <td class="py-2.5 text-zinc-400">{{ trade.executed_at ? new Date(trade.executed_at).toLocaleString('en-GB') : '-' }}</td>
                <td class="py-2.5">
                  <span
                    class="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded border font-semibold"
                    :class="trade.transaction_type === 'BUY'
                      ? 'bg-zinc-900 text-emerald-400 border-emerald-500/30'
                      : (trade.transaction_type === 'SELL' ? 'bg-zinc-900 text-rose-400 border-rose-500/30' : 'bg-zinc-900 text-zinc-300 border-zinc-700')"
                  >
                    {{ trade.transaction_type }}
                  </span>
                </td>
                <td class="py-2.5 font-semibold text-zinc-200">{{ trade.ticker }}</td>
                <td class="py-2.5 text-right text-zinc-300 tabular-nums">{{ Number(trade.shares).toLocaleString('en-US', { maximumFractionDigits: 6 }) }}</td>
                <td class="py-2.5 text-right text-zinc-400 tabular-nums">{{ Number(trade.price_per_share).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) }}</td>
                <td class="py-2.5 text-right text-zinc-500 tabular-nums">{{ Number(trade.fee || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</td>
                <td class="py-2.5 text-right pr-4 font-semibold text-zinc-100 tabular-nums">
                  {{ Number((Number(trade.shares) * Number(trade.price_per_share)) + Number(trade.fee || 0)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import apiClient from '../../api/client'
import {
  ArrowLeft,
  FileSpreadsheet,
  Upload,
  Download,
  Check
} from 'lucide-vue-next'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const selectedPortfolioId = ref<string>('')
const selectedFormat = ref<'AUTO' | 'DIME' | 'STREAMING' | 'BITKUB' | 'GENERIC'>('AUTO')
const isDragging = ref(false)
const isImporting = ref(false)
const selectedFileName = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)

interface ParsedTrade {
  ticker: string
  transaction_type: 'BUY' | 'SELL' | 'DIVIDEND'
  shares: number
  price_per_share: number
  fee: number
  currency: 'THB' | 'USD'
  executed_at: string
  notes?: string
}

const parsedTrades = ref<ParsedTrade[]>([])

onMounted(async () => {
  await portfolioStore.fetchPortfolios()
  const defaultPf = portfolioStore.portfolios.find(p => p.is_default) || portfolioStore.portfolios[0]
  if (defaultPf) {
    selectedPortfolioId.value = defaultPf.id
  }
})

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) parseFile(file)
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) parseFile(file)
}

async function parseFile(file: File) {
  selectedFileName.value = file.name
  const text = await file.text()
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0)

  if (lines.length < 2) {
    toast.error('CSV file has no data rows.')
    return
  }

  const delimiter = lines[0].includes('\t') ? '\t' : ','
  const header = lines[0].split(delimiter).map(h => h.trim().replace(/^["']|["']$/g, '').toLowerCase())

  const rows: ParsedTrade[] = []

  for (let i = 1; i < lines.length; i++) {
    const rawCols = lines[i].split(delimiter).map(c => c.trim().replace(/^["']|["']$/g, ''))
    if (rawCols.length < 3) continue

    try {
      const parsed = parseRow(header, rawCols)
      if (parsed) rows.push(parsed)
    } catch {
      // Skip invalid row
    }
  }

  if (rows.length === 0) {
    toast.error('Could not parse any valid trades from this file. Check CSV headers.')
    return
  }

  parsedTrades.value = rows
  toast.success(`Successfully parsed ${rows.length} transactions from statement!`)
}

function parseRow(header: string[], cols: string[]): ParsedTrade | null {
  const rowMap: Record<string, string> = {}
  header.forEach((h, idx) => {
    rowMap[h] = cols[idx] || ''
  })

  // 1. Ticker column detection
  const ticker = (rowMap['ticker'] || rowMap['symbol'] || rowMap['stock'] || rowMap['asset'] || rowMap['pair'] || '').toUpperCase()
  if (!ticker) return null

  // 2. Action / Side column detection
  const sideRaw = (rowMap['action'] || rowMap['type'] || rowMap['side'] || rowMap['trans type'] || rowMap['transaction_type'] || 'BUY').toUpperCase()
  let action: 'BUY' | 'SELL' | 'DIVIDEND' = 'BUY'
  if (sideRaw.includes('SELL') || sideRaw === 'S' || sideRaw.includes('SHORT')) action = 'SELL'
  else if (sideRaw.includes('DIV') || sideRaw.includes('INCOME')) action = 'DIVIDEND'

  // 3. Shares / Volume column detection
  const sharesRaw = rowMap['shares'] || rowMap['volume'] || rowMap['vol'] || rowMap['filled quantity'] || rowMap['amount'] || rowMap['qty'] || '0'
  const shares = Math.abs(parseFloat(sharesRaw.replace(/,/g, '')) || 0)
  if (shares <= 0) return null

  // 4. Price column detection
  const priceRaw = rowMap['price'] || rowMap['price_per_share'] || rowMap['filled price'] || rowMap['avg price'] || rowMap['rate'] || '0'
  const price = Math.abs(parseFloat(priceRaw.replace(/,/g, '')) || 0)

  // 5. Fee column detection
  const feeRaw = rowMap['fee'] || rowMap['commission'] || rowMap['comm'] || rowMap['vat'] || '0'
  const fee = Math.abs(parseFloat(feeRaw.replace(/,/g, '')) || 0)

  // 6. Date column detection
  const dateRaw = rowMap['date'] || rowMap['executed_at'] || rowMap['trade date'] || rowMap['matched date'] || rowMap['time'] || ''
  let executedAt = new Date().toISOString()
  if (dateRaw) {
    const parsedD = new Date(dateRaw)
    if (!isNaN(parsedD.getTime())) {
      executedAt = parsedD.toISOString()
    }
  }

  // 7. Currency detection
  let currency: 'THB' | 'USD' = 'USD'
  if (rowMap['currency']) {
    currency = rowMap['currency'].toUpperCase() === 'THB' ? 'THB' : 'USD'
  } else if (ticker.endsWith('.BK')) {
    currency = 'THB'
  }

  return {
    ticker,
    transaction_type: action,
    shares,
    price_per_share: price,
    fee,
    currency,
    executed_at: executedAt,
    notes: 'CSV Statement Import'
  }
}

function clearParsed() {
  parsedTrades.value = []
  selectedFileName.value = ''
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function downloadSampleCsv() {
  const sample = `Date,Ticker,Type,Shares,Price,Fee,Currency
2026-10-15 10:30:00,AAPL,BUY,10,182.50,1.20,USD
2026-10-16 11:00:00,NVDA,BUY,5,135.20,0.80,USD
2026-10-18 14:15:00,PTT.BK,BUY,500,34.50,25.00,THB
2026-10-20 09:45:00,BTC-USD,BUY,0.015,64500.00,2.50,USD`

  const blob = new Blob([sample], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'portfolio_trade_import_sample.csv'
  a.click()
  URL.revokeObjectURL(url)
}

async function commitImport() {
  if (parsedTrades.value.length === 0) return

  isImporting.value = true
  try {
    const res = await apiClient.post('/portfolio/transactions/bulk-import/', {
      portfolio_id: selectedPortfolioId.value || undefined,
      transactions: parsedTrades.value
    })

    const { imported, duplicates_skipped, errors_count } = res.data
    toast.success(`Import complete! ${imported} trades created (${duplicates_skipped} duplicates skipped, ${errors_count} errors)`)
    await portfolioStore.fetchTransactions()
    router.push('/portfolio/executions')
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || 'Failed to bulk import transactions')
  } finally {
    isImporting.value = false
  }
}
</script>
