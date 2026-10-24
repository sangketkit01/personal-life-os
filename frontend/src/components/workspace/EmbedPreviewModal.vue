<template>
  <div
    v-if="isOpen && link"
    class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-2 sm:p-6 font-sans"
    @click.self="emit('close')"
  >
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-5xl h-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
      <!-- Header Bar -->
      <div class="h-12 px-4 flex items-center justify-between border-b border-zinc-800/80 shrink-0">
        <div class="flex items-center gap-2.5 min-w-0">
          <span class="w-6 h-6 rounded bg-zinc-900 border border-zinc-800 flex items-center justify-center text-[10px] shrink-0">
            {{ typeIcon }}
          </span>
          <div class="min-w-0">
            <h3 class="text-xs font-semibold text-zinc-100 truncate">{{ link.title }}</h3>
            <p class="text-[10px] font-mono text-zinc-500 uppercase">{{ typeLabel }}</p>
          </div>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <a
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
            class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] font-medium text-zinc-300 transition-colors flex items-center gap-1.5"
          >
            <ExternalLink class="w-3 h-3" />
            <span class="hidden sm:inline">Open Original</span>
            <span class="sm:hidden">Open</span>
          </a>
          <button
            @click="emit('close')"
            class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900 transition-colors"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Embed Frame (16:9 responsive) -->
      <div class="flex-1 bg-zinc-900/40 min-h-0 p-2 sm:p-4">
        <div v-if="embedUrl" class="w-full h-full">
          <iframe
            :src="embedUrl"
            class="w-full h-full rounded-lg border border-zinc-800/80 bg-zinc-950"
            allow="fullscreen"
            allowfullscreen
            referrerpolicy="no-referrer"
            :title="link.title"
          />
        </div>
        <div v-else class="w-full h-full flex flex-col items-center justify-center gap-3 text-center p-8">
          <MonitorX class="w-8 h-8 text-zinc-600" />
          <p class="text-xs text-zinc-400 max-w-sm leading-relaxed">
            This resource does not support embedding. Open it in a new tab instead.
          </p>
          <a
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
            class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors"
          >
            Open {{ typeLabel }} ↗
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { X, ExternalLink, MonitorX } from 'lucide-vue-next'
import type { ProjectLink, ProjectLinkType } from '../../types/workspace'

const props = defineProps<{
  isOpen: boolean
  link: ProjectLink | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const TYPE_META: Record<ProjectLinkType, { label: string; icon: string }> = {
  WEBSITE: { label: 'Website / App', icon: '🌐' },
  CANVA: { label: 'Canva Presentation', icon: '🎨' },
  FIGMA: { label: 'Figma Design', icon: '🖌️' },
  GITHUB: { label: 'GitHub Repository', icon: '💻' },
  SHEET: { label: 'Spreadsheet / Doc', icon: '📄' },
  OTHER: { label: 'External Resource', icon: '🔗' }
}

const typeLabel = computed(() => (props.link ? TYPE_META[props.link.link_type]?.label || 'Link' : ''))
const typeIcon = computed(() => (props.link ? TYPE_META[props.link.link_type]?.icon || '🔗' : '🔗'))

/**
 * Convert share URLs into embeddable URLs safely.
 * Returns null when the resource cannot be embedded in an iframe.
 */
const embedUrl = computed<string | null>(() => {
  if (!props.link) return null
  const url = props.link.url
  const type = props.link.link_type

  try {
    const parsed = new URL(url)
    const host = parsed.hostname.replace(/^www\./, '')

    // Canva design links support ?embed
    if (host.endsWith('canva.com')) {
      if (parsed.pathname.includes('/design/') || parsed.pathname.includes('/brand/')) {
        return url.includes('?') ? `${url}&embed` : `${url}?embed`
      }
      return url
    }

    // Figma has a first-party embed endpoint
    if (host.endsWith('figma.com')) {
      return `https://www.figma.com/embed?embed_host=lifeos&url=${encodeURIComponent(url)}`
    }

    // Google Docs / Sheets / Slides / Drive previews
    if (host.endsWith('docs.google.com') || host.endsWith('drive.google.com')) {
      if (parsed.pathname.startsWith('/document/')) {
        return `${url.replace(/\/edit.*$/, '/preview')}`
      }
      if (parsed.pathname.startsWith('/spreadsheets/')) {
        return `${url.replace(/\/edit.*$/, '/preview')}`
      }
      if (parsed.pathname.startsWith('/presentation/')) {
        return `${url.replace(/\/edit.*$/, '/preview')}`
      }
      if (host === 'drive.google.com' && parsed.pathname.startsWith('/file/d/')) {
        const fileId = parsed.pathname.split('/')[3]
        if (fileId) return `https://drive.google.com/file/d/${fileId}/preview`
      }
      return url
    }

    // YouTube embeds
    if (host === 'youtube.com' || host === 'm.youtube.com') {
      const videoId = parsed.searchParams.get('v')
      if (videoId) return `https://www.youtube.com/embed/${videoId}`
      if (parsed.pathname.startsWith('/shorts/')) {
        return `https://www.youtube.com/embed/${parsed.pathname.split('/')[2]}`
      }
    }
    if (host === 'youtu.be') {
      return `https://www.youtube.com/embed${parsed.pathname}`
    }

    // GitHub repository embeds are blocked by X-Frame-Options
    if (host.endsWith('github.com') && type === 'GITHUB') {
      return null
    }

    // Generic websites: attempt direct embed (may be blocked by the target site)
    return type === 'WEBSITE' || type === 'OTHER' ? url : null
  } catch {
    return null
  }
})
</script>
