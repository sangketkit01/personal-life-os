<template>
  <div class="space-y-6 max-w-4xl mx-auto font-sans pb-16">
    <!-- Top Navigation Breadcrumb & Quick Actions -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2 text-xs font-mono text-zinc-400">
        <RouterLink to="/portfolio" class="hover:text-zinc-200 transition-colors flex items-center gap-1">
          <ArrowLeft class="w-3.5 h-3.5" />
          <span>Portfolio</span>
        </RouterLink>
        <span class="text-zinc-600">/</span>
        <button @click="backToNews" class="hover:text-zinc-200 transition-colors">
          Market Intelligence
        </button>
        <span class="text-zinc-600">/</span>
        <span class="text-zinc-300 truncate max-w-[240px]">{{ article?.ticker || 'Article' }}</span>
      </div>

      <div class="flex items-center gap-2">
        <button
          v-if="article"
          @click="viewAsset(article.ticker)"
          class="px-2.5 py-1 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1.5"
        >
          <BarChart3 class="w-3.5 h-3.5" />
          <span>${{ article.ticker }} Asset Page</span>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="p-16 text-center text-xs text-zinc-500 font-mono space-y-2">
      <div class="w-5 h-5 border-2 border-zinc-600 border-t-zinc-200 rounded-full animate-spin mx-auto"></div>
      <div>กำลังโหลดข้อมูลข่าวและเนื้อหาฉบับเต็ม (Loading full article)...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="errorMessage || !article" class="p-12 text-center rounded-xl bg-zinc-900/30 border border-zinc-800 space-y-3">
      <p class="text-xs text-rose-400 font-mono">{{ errorMessage || 'ไม่พบบทความข่าวนี้' }}</p>
      <button
        @click="backToNews"
        class="px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200 transition-colors"
      >
        กลับสู่หน้าหลัก Portfolio
      </button>
    </div>

    <!-- Article Detail Layout (Format 2 + 1) -->
    <div v-else class="space-y-6">
      <!-- Article Header & Metadata Card -->
      <div class="p-6 rounded-xl bg-zinc-950 border border-zinc-800 shadow-xl space-y-5">
        <!-- Metadata Row -->
        <div class="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-zinc-800/80">
          <div class="flex flex-wrap items-center gap-2">
            <!-- Ticker Link Badge -->
            <button
              @click="viewAsset(article.ticker)"
              class="font-mono font-bold text-xs px-2.5 py-1 rounded bg-blue-950/60 text-blue-400 border border-blue-500/30 hover:bg-blue-900/40 transition-colors flex items-center gap-1"
              title="Click to view full asset details"
            >
              <span>${{ article.ticker }}</span>
              <ExternalLink class="w-2.5 h-2.5 ml-0.5 opacity-60" />
            </button>

            <!-- Publisher / Source -->
            <span class="text-xs font-mono px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-800">
              {{ article.source || 'Financial News' }}
            </span>

            <!-- Sentiment Badge -->
            <span
              class="text-[11px] font-mono uppercase tracking-wider px-2.5 py-0.5 rounded-full border flex items-center gap-1.5 font-medium"
              :class="getSentimentClass(article.sentiment)"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="getSentimentDot(article.sentiment)"></span>
              <span>{{ article.sentiment }}</span>
            </span>
          </div>

          <!-- Publication Date & Reading Time -->
          <div class="flex items-center gap-3 text-xs font-mono text-zinc-500">
            <div class="flex items-center gap-1.5">
              <Clock class="w-3.5 h-3.5 text-zinc-500" />
              <span>{{ formatDateTime(article.published_at) }}</span>
            </div>
            <span class="text-zinc-700">•</span>
            <div class="flex items-center gap-1">
              <BookOpen class="w-3.5 h-3.5 text-zinc-500" />
              <span>{{ readingTimeEstimate }}</span>
            </div>
          </div>
        </div>

        <!-- Thumbnail Image (If available) -->
        <div
          v-if="article.thumbnail_url"
          class="rounded-lg overflow-hidden border border-zinc-800/80 max-h-80 bg-zinc-900/60 flex items-center justify-center"
        >
          <img
            :src="article.thumbnail_url"
            :alt="article.title"
            class="w-full h-full object-cover"
            @error="handleImageError"
          />
        </div>

        <!-- Language Switcher Bar & Tools -->
        <div class="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div class="flex items-center gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-lg">
            <button
              type="button"
              @click="activeLang = 'th'"
              class="px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1.5"
              :class="activeLang === 'th' ? 'bg-zinc-800 text-zinc-100 shadow-sm font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
            >
              <span>🇹🇭 ภาษาไทย (เต็มเรื่อง + สรุป)</span>
            </button>
            <button
              type="button"
              @click="activeLang = 'en'"
              class="px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1.5"
              :class="activeLang === 'en' ? 'bg-zinc-800 text-zinc-100 shadow-sm font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
            >
              <span>🇺🇸 Original English (Full Text)</span>
            </button>
          </div>

          <!-- Tools: Copy & Text Resizer -->
          <div class="flex items-center gap-2">
            <button
              @click="copyArticleText"
              class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1"
              :title="copied ? 'คัดลอกเรียบร้อย' : 'คัดลอกเนื้อหาข่าว'"
            >
              <Check v-if="copied" class="w-3.5 h-3.5 text-emerald-400" />
              <Copy v-else class="w-3.5 h-3.5" />
              <span>{{ copied ? 'Copied' : 'Copy Text' }}</span>
            </button>

            <button
              @click="toggleFontSize"
              class="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
              title="ปรับขนาดตัวอักษร"
            >
              <span class="font-bold">{{ isLargeFont ? 'A-' : 'A+' }}</span>
            </button>
          </div>
        </div>

        <!-- Headline -->
        <h1 class="text-xl sm:text-2xl lg:text-3xl font-extrabold text-zinc-100 tracking-tight leading-snug">
          {{ currentTitle }}
        </h1>
      </div>

      <!-- FORMAT 1: AI Executive Summary & Key Takeaways Card -->
      <div class="p-6 rounded-xl bg-gradient-to-b from-amber-500/10 via-zinc-950 to-zinc-950 border border-amber-500/25 shadow-xl space-y-4">
        <div class="flex items-center justify-between border-b border-amber-500/15 pb-3">
          <div class="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-amber-400 font-semibold">
            <Sparkles class="w-4 h-4 text-amber-400" />
            <span>{{ activeLang === 'th' ? 'บทวิเคราะห์และสรุปสาระสำคัญ (AI Executive Summary)' : 'Market Intelligence & Key Takeaways' }}</span>
          </div>
          <span class="text-[11px] font-mono text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/20">
            Key Takeaways
          </span>
        </div>

        <!-- Bullet Points -->
        <div class="space-y-2.5">
          <div
            v-for="(bullet, idx) in executiveBullets"
            :key="idx"
            class="flex items-start gap-3 p-3.5 rounded-lg bg-zinc-900/50 border border-zinc-800/80 hover:border-amber-500/30 transition-colors"
          >
            <div class="w-5 h-5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-400 text-xs font-mono flex items-center justify-center shrink-0 mt-0.5 font-bold">
              {{ idx + 1 }}
            </div>
            <div class="text-sm text-zinc-200 font-sans leading-relaxed">
              {{ bullet }}
            </div>
          </div>
        </div>
      </div>

      <!-- FORMAT 2: Full Article Body Reader -->
      <div class="p-6 sm:p-8 rounded-xl bg-zinc-950 border border-zinc-800 shadow-xl space-y-6">
        <div class="flex items-center justify-between border-b border-zinc-800/80 pb-3">
          <div class="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-zinc-300 font-semibold">
            <FileText class="w-4 h-4 text-blue-400" />
            <span>{{ activeLang === 'th' ? 'เนื้อหาข่าวฉบับเต็ม (Full Article Body)' : 'Full Article Journalism' }}</span>
          </div>
          <div class="text-[11px] font-mono text-zinc-500">
            {{ activeLang === 'th' ? (article.content_th ? 'แปลไทยเรียบเรียงสมบูรณ์' : 'สรุปสาระสำคัญ') : 'Direct Source Scrape' }}
          </div>
        </div>

        <!-- Paragraphs Display -->
        <div
          class="font-sans text-zinc-300 leading-relaxed space-y-4"
          :class="isLargeFont ? 'text-lg leading-loose' : 'text-base sm:text-base leading-relaxed'"
        >
          <template v-if="articleParagraphs.length > 0">
            <p
              v-for="(para, idx) in articleParagraphs"
              :key="idx"
              class="first-letter:text-xl first-letter:font-semibold first-letter:text-zinc-100"
            >
              {{ para }}
            </p>
          </template>
          <div v-else class="p-6 text-center text-xs font-mono text-zinc-500 italic bg-zinc-900/30 rounded-lg border border-zinc-800/60">
            {{ activeLang === 'th' ? 'กำลังประมวลผลเนื้อหาฉบับเต็ม หรือข่าวนี้มีเฉพาะสาระสำคัญ' : 'Full body content is being retrieved from the original publisher.' }}
          </div>
        </div>

        <!-- Collapsible Alternate Language Full Text -->
        <div v-if="hasSecondaryLang" class="mt-6 pt-4 border-t border-zinc-800/80">
          <button
            @click="showOriginalToggle = !showOriginalToggle"
            class="text-xs font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1.5 transition-colors"
          >
            <ChevronDown class="w-3.5 h-3.5 transition-transform" :class="{ 'rotate-180': showOriginalToggle }" />
            <span>{{ activeLang === 'th' ? 'แสดงเนื้อหาภาษาอังกฤษดั้งเดิม (Show Original English Body)' : 'แสดงเนื้อหาแปลภาษาไทย (Show Thai Translation Body)' }}</span>
          </button>

          <div
            v-if="showOriginalToggle"
            class="mt-4 p-5 rounded-lg bg-zinc-900/40 border border-zinc-800 text-sm text-zinc-400 font-sans leading-relaxed whitespace-pre-line"
          >
            {{ activeLang === 'th' ? (article.content || article.summary || article.title) : (article.content_th || article.summary_th || article.title_th) }}
          </div>
        </div>
      </div>

      <!-- Original Source CTA Bar -->
      <div class="p-5 rounded-xl bg-zinc-950 border border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div class="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
            <span>สำนักข่าวต้นทาง: {{ article.source || 'Financial Media' }}</span>
          </div>
          <div class="text-[11px] text-zinc-500 font-sans mt-0.5">
            อ่านบทความต้นฉบับฉบับเต็มโดยตรงจากสำนักข่าวเพื่อการอ้างอิงเชิงลึก
          </div>
        </div>

        <a
          :href="article.url"
          target="_blank"
          rel="noopener noreferrer"
          class="px-4 py-2 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center justify-center gap-2 shadow shrink-0"
        >
          <span>เปิดบทความต้นฉบับ (Open Original)</span>
          <ExternalLink class="w-3.5 h-3.5" />
        </a>
      </div>

      <!-- Quick Ticker Action Card -->
      <div class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-blue-400 font-mono font-bold text-xs">
            ${{ article.ticker.slice(0, 3) }}
          </div>
          <div>
            <div class="text-xs font-semibold text-zinc-200">สนใจลงทุนใน {{ article.ticker }} หรือถือครองอยู่แล้ว?</div>
            <div class="text-[11px] text-zinc-500 font-sans">ดูกราฟราคา Dime-style สัดส่วนพอร์ต ทุนเฉลี่ย และประวัติการทำรายการ</div>
          </div>
        </div>

        <button
          @click="viewAsset(article.ticker)"
          class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-200 hover:text-white transition-colors"
        >
          ดูหน้าสินทรัพย์ {{ article.ticker }} →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePortfolioStore } from '../stores/portfolio'
import type { StockNewsArticle } from '../types/portfolio'
import {
  ArrowLeft,
  Clock,
  Sparkles,
  ExternalLink,
  ChevronDown,
  BarChart3,
  BookOpen,
  FileText,
  Copy,
  Check
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const portfolioStore = usePortfolioStore()

const article = ref<StockNewsArticle | null>(null)
const isLoading = ref(true)
const errorMessage = ref('')
const activeLang = ref<'th' | 'en'>('th')
const showOriginalToggle = ref(false)
const copied = ref(false)
const isLargeFont = ref(false)

const currentTitle = computed(() => {
  if (!article.value) return ''
  if (activeLang.value === 'th' && article.value.title_th) {
    return article.value.title_th
  }
  return article.value.title
})

const executiveBullets = computed(() => {
  if (!article.value) return []
  const text = activeLang.value === 'th'
    ? (article.value.summary_th || article.value.summary || article.value.title_th)
    : (article.value.summary || article.value.title)

  if (!text) return []

  // แยกบรรทัดและตัดสัญลักษณ์ Bullet ออก
  const lines = text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .map(line => line.replace(/^([•\-\*\d+\.]\s*)+/, '').trim())
    .filter(line => line.length > 5)

  if (lines.length > 0) return lines
  return [text]
})

const articleParagraphs = computed(() => {
  if (!article.value) return []

  let rawContent = ''
  if (activeLang.value === 'th') {
    rawContent = article.value.content_th || article.value.content || ''
  } else {
    rawContent = article.value.content || ''
  }

  // หากไม่มีเนื้อหาฉบับเต็ม ให้ใช้ summary เป็นย่อหน้าเดี่ยว
  if (!rawContent) {
    const fallback = activeLang.value === 'th'
      ? (article.value.summary_th || article.value.summary)
      : article.value.summary
    return fallback ? [fallback] : []
  }

  return rawContent
    .split('\n\n')
    .map(p => p.trim())
    .filter(p => p.length > 0)
})

const readingTimeEstimate = computed(() => {
  if (!article.value) return '~1 min'
  const text = (article.value.content || '') + ' ' + (article.value.summary || '')
  const words = text.split(/\s+/).filter(Boolean).length
  const minutes = Math.max(1, Math.ceil(words / 180))
  return `~${minutes} นาที (${words} คำ)`
})

const hasSecondaryLang = computed(() => {
  if (!article.value) return false
  return Boolean(article.value.content && article.value.content_th)
})

function toggleFontSize() {
  isLargeFont.value = !isLargeFont.value
}

async function copyArticleText() {
  if (!article.value) return
  const title = currentTitle.value
  const bullets = executiveBullets.value.map((b, i) => `${i + 1}. ${b}`).join('\n')
  const body = articleParagraphs.value.join('\n\n')
  const fullText = `${title}\n\n[Executive Summary]\n${bullets}\n\n[Full Article]\n${body}\n\nSource: ${article.value.url}`

  try {
    await navigator.clipboard.writeText(fullText)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy text', err)
  }
}

function getSentimentClass(sentiment: string) {
  switch (sentiment) {
    case 'BULLISH':
      return 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30'
    case 'BEARISH':
      return 'bg-rose-950/40 text-rose-400 border-rose-500/30'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

function getSentimentDot(sentiment: string) {
  switch (sentiment) {
    case 'BULLISH':
      return 'bg-emerald-400'
    case 'BEARISH':
      return 'bg-rose-400'
    default:
      return 'bg-zinc-500'
  }
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('th-TH', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function handleImageError(e: Event) {
  const target = e.target as HTMLElement
  if (target) {
    target.style.display = 'none'
  }
}

function backToNews() {
  router.push('/portfolio')
}

function viewAsset(ticker: string) {
  router.push(`/portfolio/asset/${encodeURIComponent(ticker)}`)
}

onMounted(async () => {
  const articleId = route.params.id as string
  if (!articleId) {
    errorMessage.value = 'ไม่พบรหัสบทความ (Invalid article ID)'
    isLoading.value = false
    return
  }

  // 1. ลองค้นหาใน Pinia Store
  const existing = portfolioStore.news.find(n => n.id === articleId)
  if (existing && existing.content && existing.content_th) {
    article.value = existing
    activeLang.value = existing.title_th || existing.summary_th ? 'th' : 'en'
    isLoading.value = false
    return
  }

  // 2. ดึงจาก Backend API (จะทำการ Lazy Backfill เนื้อหาอัตโนมัติหากยังไม่มี)
  try {
    const fetched = await portfolioStore.fetchNewsArticle(articleId)
    article.value = fetched
    activeLang.value = fetched.title_th || fetched.summary_th ? 'th' : 'en'
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.detail || 'ไม่สามารถโหลดรายละเอียดบทความได้'
  } finally {
    isLoading.value = false
  }
})
</script>
