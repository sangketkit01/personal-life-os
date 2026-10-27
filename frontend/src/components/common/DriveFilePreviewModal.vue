<template>
  <Teleport to="body">
    <div
      v-if="isOpen && driveFileId"
      class="fixed inset-0 z-[70] bg-black/85 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-hidden font-sans"
      @click.self="emit('close')"
    >
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-5xl h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col shadow-2xl overflow-hidden">
        <!-- Top bar -->
        <div class="h-12 px-4 flex items-center justify-between border-b border-zinc-800/80 shrink-0">
          <div class="flex items-center gap-2.5 min-w-0">
            <FileText class="w-4 h-4 text-zinc-500 shrink-0" />
            <div class="min-w-0">
              <h3 class="text-xs font-semibold text-zinc-100 truncate">{{ fileName || 'Drive File' }}</h3>
              <p class="text-[10px] font-mono text-zinc-500">{{ formatBytes(fileSize || 0) }} • {{ kindLabel }}</p>
            </div>
          </div>

          <div class="flex items-center gap-1.5 shrink-0">
            <!-- Image controls -->
            <template v-if="kind === 'image'">
              <button type="button" class="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors" title="Zoom out" @click="zoom = Math.max(0.25, zoom - 0.25)">
                <ZoomOut class="w-3.5 h-3.5" />
              </button>
              <button type="button" class="px-1.5 py-1 rounded-md text-[10px] font-mono text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors" title="Reset zoom" @click="zoom = 1; rotation = 0">
                {{ Math.round(zoom * 100) }}%
              </button>
              <button type="button" class="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors" title="Zoom in" @click="zoom = Math.min(4, zoom + 0.25)">
                <ZoomIn class="w-3.5 h-3.5" />
              </button>
              <button type="button" class="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors" title="Rotate 90°" @click="rotation = (rotation + 90) % 360">
                <RotateCw class="w-3.5 h-3.5" />
              </button>
            </template>

            <a
              v-if="objectUrl"
              :href="objectUrl"
              :download="fileName || 'file'"
              class="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors"
              title="Download"
            >
              <Download class="w-3.5 h-3.5" />
            </a>
            <a
              v-if="driveViewLink"
              :href="driveViewLink"
              target="_blank"
              rel="noopener noreferrer"
              class="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors"
              title="Open in Google Drive"
            >
              <ExternalLink class="w-3.5 h-3.5" />
            </a>
            <button type="button" class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900 transition-colors" title="Close (Esc)" @click="emit('close')">
              <X class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Preview body -->
        <div class="flex-1 min-h-0 bg-zinc-900/40 overflow-auto overscroll-contain flex items-center justify-center p-2 sm:p-3">
          <div v-if="loading" class="flex flex-col items-center gap-3 text-zinc-500">
            <Loader2 class="w-6 h-6 animate-spin" />
            <span class="text-xs font-mono">Loading from Google Drive...</span>
          </div>

          <div v-else-if="error" class="flex flex-col items-center gap-3 text-center p-8">
            <AlertTriangle class="w-7 h-7 text-zinc-600" />
            <p class="text-xs text-zinc-400 max-w-sm">{{ error }}</p>
            <a v-if="driveViewLink" :href="driveViewLink" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors">
              Open in Google Drive ↗
            </a>
          </div>

          <!-- Image -->
          <div v-else-if="kind === 'image' && objectUrl" class="w-full h-full flex items-center justify-center overflow-auto">
            <img
              :src="objectUrl"
              class="origin-center transition-transform duration-100 rounded-md border border-zinc-800"
              :style="{ transform: `scale(${zoom}) rotate(${rotation}deg)` }"
              :alt="fileName || 'Drive image'"
            />
          </div>

          <!-- PDF -->
          <iframe
            v-else-if="kind === 'pdf' && objectUrl"
            :src="objectUrl"
            class="w-full h-full rounded-lg border border-zinc-800 bg-white"
            :title="fileName || 'PDF preview'"
          />

          <!-- Audio -->
          <audio v-else-if="kind === 'audio' && objectUrl" controls autoplay class="w-full max-w-xl" :src="objectUrl" />

          <!-- Video -->
          <video v-else-if="kind === 'video' && objectUrl" controls autoplay class="max-w-full max-h-full rounded-lg border border-zinc-800" :src="objectUrl" />

          <!-- CSV table -->
          <div v-else-if="kind === 'csv' && csvRows.length > 0" class="w-full h-full overflow-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr>
                  <th
                    v-for="(cell, i) in csvRows[0]"
                    :key="'h' + i"
                    class="sticky top-0 px-3 py-2 text-[10px] font-mono uppercase text-zinc-400 bg-zinc-900 border-b border-zinc-800"
                  >
                    {{ cell }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, r) in csvRows.slice(1)" :key="r" class="hover:bg-zinc-900/50">
                  <td v-for="(cell, c) in row" :key="c" class="px-3 py-1.5 text-xs text-zinc-300 border-b border-zinc-800/50 font-mono">
                    {{ cell }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Text / code -->
          <div v-else-if="kind === 'text' && textLines" class="w-full h-full overflow-auto rounded-lg bg-zinc-950 border border-zinc-800">
            <div class="flex items-center justify-end px-3 py-1.5 border-b border-zinc-800/80 sticky top-0 bg-zinc-950/95">
              <button type="button" class="px-2 py-1 rounded text-[10px] font-mono text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors flex items-center gap-1" @click="copyText">
                <Check v-if="copied" class="w-3 h-3 text-emerald-400" />
                <Copy v-else class="w-3 h-3" />
                {{ copied ? 'Copied!' : 'Copy' }}
              </button>
            </div>
            <div class="flex">
              <div class="select-none py-2 pl-3 pr-2 text-right text-[11px] font-mono text-zinc-700 leading-5">
                <div v-for="n in textLines.length" :key="n">{{ n }}</div>
              </div>
              <pre class="flex-1 py-2 pr-4 text-[11px] font-mono text-zinc-300 leading-5 whitespace-pre overflow-x-auto"><code>{{ textLines.join('\n') }}</code></pre>
            </div>
          </div>

          <!-- Office / fallback via Drive embed -->
          <iframe
            v-else-if="kind === 'office'"
            :src="`https://drive.google.com/file/d/${driveFileId}/preview`"
            class="w-full h-full rounded-lg border border-zinc-800 bg-zinc-950"
            allow="autoplay"
            :title="fileName || 'Office document preview'"
          />

          <div v-else class="flex flex-col items-center gap-3 text-center p-8">
            <FileQuestion class="w-7 h-7 text-zinc-600" />
            <p class="text-xs text-zinc-400">No in-app preview for this file type.</p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  AlertTriangle,
  Check,
  Copy,
  Download,
  ExternalLink,
  FileQuestion,
  FileText,
  Loader2,
  RotateCw,
  X,
  ZoomIn,
  ZoomOut
} from 'lucide-vue-next'
import apiClient from '../../api/client'
import { useToastStore } from '../../stores/toast'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'

const props = defineProps<{
  isOpen: boolean
  driveFileId: string | null
  fileName?: string
  fileType?: string
  fileSize?: number
  driveViewLink?: string
  driveDownloadLink?: string
  /** Pre-resolved object URL (skips re-fetching the stream). */
  blobUrl?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

useBodyScrollLock(() => props.isOpen)

const toast = useToastStore()

const loading = ref(false)
const error = ref('')
const objectUrl = ref('')
let createdOwnUrl = false

const zoom = ref(1)
const rotation = ref(0)
const copied = ref(false)
const textLines = ref<string[] | null>(null)
const csvRows = ref<string[][]>([])

type PreviewKind = 'image' | 'pdf' | 'audio' | 'video' | 'csv' | 'text' | 'office' | 'unknown'

const ext = computed(() => {
  const name = props.fileName || ''
  const dot = name.lastIndexOf('.')
  return dot === -1 ? '' : name.slice(dot + 1).toLowerCase()
})

const kind = computed<PreviewKind>(() => {
  const type = (props.fileType || '').toLowerCase()
  if (type.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext.value)) return 'image'
  if (type === 'application/pdf' || ext.value === 'pdf') return 'pdf'
  if (type.startsWith('audio/') || ['mp3', 'wav', 'm4a', 'ogg', 'webm', 'flac'].includes(ext.value)) return 'audio'
  if (type.startsWith('video/') || ['mp4', 'mov', 'webm', 'avi', 'mkv'].includes(ext.value)) return 'video'
  if (ext.value === 'csv') return 'csv'
  if (
    type.startsWith('text/') ||
    ['txt', 'md', 'json', 'py', 'ts', 'tsx', 'js', 'sql', 'log', 'yml', 'yaml', 'xml', 'html', 'css', 'sh', 'ini'].includes(ext.value)
  ) return 'text'
  if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(ext.value)) return 'office'
  return 'unknown'
})

const kindLabel = computed(() => {
  switch (kind.value) {
    case 'image': return 'Image'
    case 'pdf': return 'PDF Document'
    case 'audio': return 'Audio'
    case 'video': return 'Video'
    case 'csv': return 'CSV Table'
    case 'text': return 'Text / Code'
    case 'office': return 'Office Document'
    default: return 'File'
  }
})

watch(
  () => [props.isOpen, props.driveFileId],
  async ([open, driveFileId]) => {
    if (!open || !driveFileId) return
    loading.value = true
    error.value = ''
    zoom.value = 1
    rotation.value = 0
    copied.value = false
    textLines.value = null
    csvRows.value = []

    try {
      if (kind.value === 'office') {
        loading.value = false
        return
      }
      let fetchedBlob: Blob | null = null
      if (props.blobUrl && kind.value !== 'text' && kind.value !== 'csv') {
        objectUrl.value = props.blobUrl
        createdOwnUrl = false
      } else {
        const res = await apiClient.get(`/storage/files/${driveFileId}/stream/`, { responseType: 'blob' })
        let blob: Blob = res.data
        if (kind.value === 'pdf' && blob.type !== 'application/pdf') {
          blob = new Blob([blob], { type: 'application/pdf' })
        }
        fetchedBlob = blob
        objectUrl.value = URL.createObjectURL(blob)
        createdOwnUrl = true
      }

      if (kind.value === 'text' || kind.value === 'csv') {
        const blobForText = fetchedBlob || (await apiClient.get(`/storage/files/${driveFileId}/stream/`, { responseType: 'blob' })).data
        const text = await blobForText.text()
        textLines.value = text.replace(/\r\n/g, '\n').split('\n')
        if (kind.value === 'csv' && textLines.value) {
          csvRows.value = textLines.value.filter(l => l.length > 0).map(line => line.split(',').map(c => c.trim().replace(/^"|"$/g, '')))
        }
      }
    } catch {
      error.value = 'Could not load this file from Google Drive. Try opening it directly in Drive.'
    } finally {
      loading.value = false
    }
  },
  { immediate: true }
)

watch(
  () => props.isOpen,
  (open) => {
    if (!open && createdOwnUrl && objectUrl.value) {
      URL.revokeObjectURL(objectUrl.value)
    }
    if (!open) {
      objectUrl.value = ''
      createdOwnUrl = false
    }
  }
)

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.isOpen) {
    e.preventDefault()
    emit('close')
  }
}

window.addEventListener('keydown', handleKeydown)
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (createdOwnUrl && objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
  }
})

async function copyText() {
  if (!textLines.value) return
  try {
    await navigator.clipboard.writeText(textLines.value.join('\n'))
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch {
    toast.error('Failed to copy to clipboard')
  }
}

function formatBytes(bytes: number): string {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, exp)).toFixed(exp === 0 ? 0 : 1)} ${units[exp]}`
}
</script>
