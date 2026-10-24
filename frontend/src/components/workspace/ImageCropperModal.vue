<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[70] bg-black/85 backdrop-blur-sm flex items-center justify-center p-4 font-sans"
      @click.self="emit('close')"
    >
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-3xl p-4 shadow-2xl relative">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-semibold text-zinc-100">Crop Image</h3>
            <p class="text-[11px] text-zinc-500 mt-0.5">{{ fileName || 'Drag the crop box, pick a ratio or rotate' }}</p>
          </div>
          <button type="button" class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900 transition-colors" @click="emit('close')">
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- Aspect ratio presets + rotation -->
        <div class="flex items-center gap-1.5 flex-wrap mb-3">
          <button
            v-for="ratio in ASPECTS"
            :key="ratio.key"
            type="button"
            class="px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors border"
            :class="aspect === ratio.key ? 'bg-zinc-800 text-zinc-100 border-zinc-600' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'"
            @click="setAspect(ratio.key)"
          >
            {{ ratio.label }}
          </button>
          <span class="w-px h-5 bg-zinc-800 mx-1" />
          <button type="button" class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors" title="Rotate -90°" @click="rotate(-90)">
            <RotateCcw class="w-3.5 h-3.5" />
          </button>
          <button type="button" class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors" title="Rotate +90°" @click="rotate(90)">
            <RotateCw class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Crop canvas area -->
        <div class="flex items-center justify-center rounded-lg bg-zinc-900/50 border border-zinc-800 p-3 overflow-hidden">
          <div
           
            class="relative touch-none"
            :style="{ width: `${dispW}px`, height: `${dispH}px`, cursor: dragging ? 'grabbing' : 'default' }"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointerleave="onPointerUp"
          >
            <img
              :src="rotatedPreviewUrl"
              class="absolute inset-0 w-full h-full select-none"
              draggable="false"
              alt="Crop source"
            />
            <!-- Dimmed overlay (4 panels around the crop box) -->
            <div class="absolute inset-0 pointer-events-none" v-if="crop.w > 0">
              <div class="absolute bg-black/55" :style="topStyle" />
              <div class="absolute bg-black/55" :style="bottomStyle" />
              <div class="absolute bg-black/55" :style="leftStyle" />
              <div class="absolute bg-black/55" :style="rightStyle" />
            </div>

            <!-- Crop box -->
            <div
              v-if="crop.w > 0"
              class="absolute border-2 border-sky-400 cursor-move"
              :style="{ left: `${crop.x}px`, top: `${crop.y}px`, width: `${crop.w}px`, height: `${crop.h}px` }"
              @pointerdown.prevent="startDrag('move', $event)"
            >
              <span
                v-for="corner in CORNERS"
                :key="corner"
                class="absolute w-3 h-3 rounded-sm bg-sky-400 border border-zinc-950"
                :class="cornerClass(corner)"
                @pointerdown.prevent.stop="startDrag(corner, $event)"
              />
              <span class="absolute inset-0 border border-white/40 pointer-events-none" />
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between mt-4 pt-3 border-t border-zinc-800/80">
          <span class="text-[10px] font-mono text-zinc-500">
            {{ Math.round(crop.w / dispScale) }} × {{ Math.round(crop.h / dispScale) }} px output
          </span>
          <div class="flex items-center gap-2.5">
            <button type="button" class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors" @click="emit('close')">
              Cancel
            </button>
            <button type="button" class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors" @click="applyCrop">
              Apply Crop
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { RotateCcw, RotateCw, X } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  imageUrl: string
  fileName?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'cropped', file: File): void
}>()

const ASPECTS = [
  { key: 'free', label: 'Free', value: 0 },
  { key: '1:1', label: '1:1', value: 1 },
  { key: '16:9', label: '16:9', value: 16 / 9 },
  { key: '4:3', label: '4:3', value: 4 / 3 }
] as const

const CORNERS = ['nw', 'ne', 'sw', 'se'] as const
type Corner = (typeof CORNERS)[number]

const aspect = ref<string>('free')
const rotation = ref(0)

const natural = reactive({ w: 0, h: 0 })
const crop = reactive({ x: 0, y: 0, w: 0, h: 0 })
const dragging = ref<'move' | Corner | null>(null)
let dragStart = { x: 0, y: 0, cx: 0, cy: 0, cw: 0, ch: 0 }

const MAX_W = 640
const MAX_H = 420

// Rotated natural dimensions (90° steps swap width/height)
const rotatedW = computed(() => (rotation.value % 180 === 0 ? natural.w : natural.h))
const rotatedH = computed(() => (rotation.value % 180 === 0 ? natural.h : natural.w))

const dispScale = computed(() => {
  if (!rotatedW.value || !rotatedH.value) return 1
  return Math.min(MAX_W / rotatedW.value, MAX_H / rotatedH.value, 1)
})

const dispW = computed(() => Math.round(rotatedW.value * dispScale.value))
const dispH = computed(() => Math.round(rotatedH.value * dispScale.value))

// Rotated image preview via a data URL so the on-screen image matches the output
const rotatedPreviewUrl = ref('')

async function updateRotatedPreview() {
  if (!props.imageUrl) {
    rotatedPreviewUrl.value = ''
    return
  }
  if (rotation.value % 360 === 0 || !rotatedW.value || !rotatedH.value) {
    rotatedPreviewUrl.value = props.imageUrl
    return
  }
  const sourceImg = new Image()
  sourceImg.src = props.imageUrl
  await new Promise<void>((resolve) => {
    if (sourceImg.complete) resolve()
    else sourceImg.onload = () => resolve()
  })
  const canvas = document.createElement('canvas')
  canvas.width = rotatedW.value
  canvas.height = rotatedH.value
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    rotatedPreviewUrl.value = props.imageUrl
    return
  }
  ctx.save()
  ctx.translate(canvas.width / 2, canvas.height / 2)
  ctx.rotate((rotation.value * Math.PI) / 180)
  ctx.drawImage(sourceImg, -natural.w / 2, -natural.h / 2, natural.w, natural.h)
  ctx.restore()
  rotatedPreviewUrl.value = canvas.toDataURL('image/jpeg', 0.92)
}

function clampCrop() {
  crop.x = Math.max(0, Math.min(crop.x, dispW.value))
  crop.y = Math.max(0, Math.min(crop.y, dispH.value))
  crop.w = Math.max(24, Math.min(crop.w, dispW.value - crop.x))
  crop.h = Math.max(24, Math.min(crop.h, dispH.value - crop.y))
}

function resetCropBox() {
  const ratio = currentAspectValue()
  let w = dispW.value * 0.8
  let h = dispH.value * 0.8
  if (ratio > 0) {
    if (w / h > ratio) w = h * ratio
    else h = w / ratio
  }
  crop.w = Math.round(w)
  crop.h = Math.round(h)
  crop.x = Math.round((dispW.value - crop.w) / 2)
  crop.y = Math.round((dispH.value - crop.h) / 2)
}

function currentAspectValue(): number {
  return ASPECTS.find(a => a.key === aspect.value)?.value || 0
}

function setAspect(key: string) {
  aspect.value = key
  resetCropBox()
}

function rotate(delta: -90 | 90) {
  rotation.value = (rotation.value + delta + 360) % 360
  nextTick(async () => {
    await updateRotatedPreview()
    resetCropBox()
  })
}

function cornerClass(corner: Corner): string {
  switch (corner) {
    case 'nw': return '-left-1.5 -top-1.5 cursor-nwse-resize'
    case 'ne': return '-right-1.5 -top-1.5 cursor-nesw-resize'
    case 'sw': return '-left-1.5 -bottom-1.5 cursor-nesw-resize'
    case 'se': return '-right-1.5 -bottom-1.5 cursor-nwse-resize'
  }
}

const topStyle = computed(() => ({ left: 0, top: 0, width: '100%', height: `${Math.max(0, crop.y)}px` }))
const bottomStyle = computed(() => ({ left: 0, bottom: 0, width: '100%', height: `${Math.max(0, dispH.value - crop.y - crop.h)}px` }))
const leftStyle = computed(() => ({ left: 0, top: `${crop.y}px`, width: `${Math.max(0, crop.x)}px`, height: `${crop.h}px` }))
const rightStyle = computed(() => ({ right: 0, top: `${crop.y}px`, width: `${Math.max(0, dispW.value - crop.x - crop.w)}px`, height: `${crop.h}px` }))

function startDrag(mode: 'move' | Corner, event: PointerEvent) {
  dragging.value = mode
  dragStart = { x: event.clientX, y: event.clientY, cx: crop.x, cy: crop.y, cw: crop.w, ch: crop.h }
}

function onPointerMove(event: PointerEvent) {
  if (!dragging.value) return
  const dx = event.clientX - dragStart.x
  const dy = event.clientY - dragStart.y
  const mode = dragging.value
  const ratio = currentAspectValue()

  if (mode === 'move') {
    crop.x = Math.max(0, Math.min(dragStart.cx + dx, dispW.value - crop.w))
    crop.y = Math.max(0, Math.min(dragStart.cy + dy, dispH.value - crop.h))
    return
  }

  // Corner resize
  let newW = dragStart.cw
  let newH = dragStart.ch
  if (mode === 'ne' || mode === 'se') {
    newW = dragStart.cw + dx
  } else {
    newW = dragStart.cw - dx
  }
  if (mode === 'sw' || mode === 'se') {
    newH = dragStart.ch + dy
  } else {
    newH = dragStart.ch - dy
  }

  if (ratio > 0) {
    // Keep aspect: use the dominant dimension
    if (Math.abs(newW - dragStart.cw) > Math.abs(newH - dragStart.ch)) {
      newH = newW / ratio
    } else {
      newW = newH * ratio
    }
  }

  newW = Math.max(24, newW)
  newH = Math.max(24, newH)
  if (ratio > 0) {
    // Re-apply after clamping to keep ratio
    if (newW / newH > ratio) newW = newH * ratio
    else newH = newW / ratio
  }

  let x = dragStart.cx
  let y = dragStart.cy
  if (mode === 'nw' || mode === 'sw') {
    x = dragStart.cx + (dragStart.cw - newW)
  }
  if (mode === 'nw' || mode === 'ne') {
    y = dragStart.cy + (dragStart.ch - newH)
  }

  crop.x = x
  crop.y = y
  crop.w = newW
  crop.h = newH
  clampCrop()
}

function onPointerUp() {
  dragging.value = null
}

// Load natural size when opened
watch(
  () => [props.isOpen, props.imageUrl],
  async ([open]) => {
    if (!open || !props.imageUrl) return
    rotation.value = 0
    aspect.value = 'free'
    const img = new Image()
    img.onload = () => {
      natural.w = img.naturalWidth
      natural.h = img.naturalHeight
      rotatedPreviewUrl.value = props.imageUrl
      nextTick(resetCropBox)
    }
    img.src = props.imageUrl
  },
  { immediate: true }
)

async function applyCrop() {
  if (crop.w <= 0 || crop.h <= 0 || !rotatedW.value) return

  const scale = dispScale.value

  // 1. Render the rotated source at natural size onto a base canvas
  const base = document.createElement('canvas')
  base.width = rotatedW.value
  base.height = rotatedH.value
  const bctx = base.getContext('2d')
  if (!bctx) return

  const sourceImg = new Image()
  sourceImg.src = props.imageUrl
  await new Promise<void>((resolve) => {
    if (sourceImg.complete) resolve()
    else sourceImg.onload = () => resolve()
  })

  bctx.save()
  bctx.translate(base.width / 2, base.height / 2)
  bctx.rotate((rotation.value * Math.PI) / 180)
  bctx.drawImage(sourceImg, -natural.w / 2, -natural.h / 2, natural.w, natural.h)
  bctx.restore()

  // 2. Extract the cropped region (display coords -> rotated natural coords)
  const sx = crop.x / scale
  const sy = crop.y / scale
  const sw = Math.max(1, crop.w / scale)
  const sh = Math.max(1, crop.h / scale)

  const out = document.createElement('canvas')
  out.width = Math.round(sw)
  out.height = Math.round(sh)
  const octx = out.getContext('2d')
  if (!octx) return
  octx.drawImage(base, sx, sy, sw, sh, 0, 0, out.width, out.height)

  const blob = await new Promise<Blob | null>(resolve => out.toBlob(resolve, 'image/jpeg', 0.92))
  if (!blob) return
  const baseName = (props.fileName || 'image').replace(/\.[^.]+$/, '')
  const file = new File([blob], `${baseName}-cropped.jpg`, { type: 'image/jpeg' })
  emit('cropped', file)
}
</script>
