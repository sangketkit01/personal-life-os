<template>
  <div class="relative select-none" @keydown="handleKeydown">
    <!-- Quick Insert Toolbar -->
    <div class="flex items-center gap-1 flex-wrap pb-2.5 mb-3 border-b border-zinc-800/60">
      <button
        v-for="tool in toolbarItems"
        :key="tool.type"
        type="button"
        @click="insertBlock(tool.type)"
        class="px-2 py-1 rounded text-[10px] font-medium transition-colors border"
        :class="toolClass(tool.type)"
        :title="`Insert ${tool.label}`"
      >
        {{ tool.label }}
      </button>
    </div>

    <!-- Blocks -->
    <div class="space-y-0.5">
      <div
        v-for="(block, index) in modelValue"
        :key="block.id"
        class="group/block relative flex items-start gap-2 rounded-md px-1.5 py-1 transition-colors hover:bg-zinc-900/30"
        @mouseenter="hoveredIndex = index"
        @mouseleave="hoveredIndex = -1"
      >
        <!-- Hover Controls (left gutter) -->
        <div
          v-if="block.type !== 'divider'"
          class="absolute -left-1 top-1/2 -translate-y-1/2 -translate-x-full pr-1 hidden sm:flex items-center gap-0.5 opacity-0 group-hover/block:opacity-100 transition-opacity"
        >
          <button
            type="button"
            @click="moveBlock(index, -1)"
            :disabled="index === 0"
            class="p-0.5 rounded text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:hover:text-zinc-500"
            title="Move Up"
          >
            <ChevronUp class="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            @click="moveBlock(index, 1)"
            :disabled="index === modelValue.length - 1"
            class="p-0.5 rounded text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:hover:text-zinc-500"
            title="Move Down"
          >
            <ChevronDown class="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            @click="removeBlock(index)"
            class="p-0.5 rounded text-zinc-600 hover:text-rose-400"
            title="Delete Block"
          >
            <Trash2 class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Mobile hover controls -->
        <div v-if="block.type !== 'divider'" class="sm:hidden absolute right-0 top-0 flex items-center gap-0.5 opacity-40">
          <button type="button" @click="moveBlock(index, -1)" :disabled="index === 0" class="p-0.5 text-zinc-500 disabled:opacity-30">
            <ChevronUp class="w-3 h-3" />
          </button>
          <button type="button" @click="removeBlock(index)" class="p-0.5 text-zinc-600">
            <Trash2 class="w-3 h-3" />
          </button>
        </div>

        <!-- DIVIDER block -->
        <div v-if="block.type === 'divider'" class="w-full py-2.5">
          <div class="border-t border-zinc-700/70" />
        </div>

        <!-- TODO block -->
        <template v-else-if="block.type === 'todo'">
          <button
            type="button"
            @click="toggleTodo(index)"
            class="mt-0.5 w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors"
            :class="block.checked ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-400' : 'border-zinc-600 hover:border-zinc-400'"
          >
            <Check v-if="block.checked" class="w-3 h-3" />
          </button>
          <input
            :ref="el => setBlockRef(el, index)"
            v-model="block.content"
            type="text"
            :placeholder="placeholderFor(index, 'To-do item...')"
            class="flex-1 bg-transparent border-none outline-none text-sm py-0.5 font-sans"
            :class="block.checked ? 'text-zinc-500 line-through' : 'text-zinc-100'"
            @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
          />
        </template>

        <!-- BULLET block -->
        <template v-else-if="block.type === 'bullet'">
          <span class="w-4 text-center leading-6 shrink-0 text-zinc-400">•</span>
          <input
            :ref="el => setBlockRef(el, index)"
            v-model="block.content"
            type="text"
            :placeholder="placeholderFor(index, 'List item...')"
            class="flex-1 bg-transparent border-none outline-none text-sm text-zinc-100 py-0.5 font-sans"
            @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
          />
        </template>

        <!-- NUMBERED block -->
        <template v-else-if="block.type === 'numbered'">
          <span class="w-4 text-center leading-6 shrink-0 text-zinc-400 text-xs font-mono">{{ numberFor(index) }}.</span>
          <input
            :ref="el => setBlockRef(el, index)"
            v-model="block.content"
            type="text"
            :placeholder="placeholderFor(index, 'List item...')"
            class="flex-1 bg-transparent border-none outline-none text-sm text-zinc-100 py-0.5 font-sans"
            @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
          />
        </template>

        <!-- HEADING blocks -->
        <template v-else-if="block.type === 'h1'">
          <input
            :ref="el => setBlockRef(el, index)"
            v-model="block.content"
            type="text"
            :placeholder="placeholderFor(index, 'Heading 1')"
            class="flex-1 w-full bg-transparent border-none outline-none text-xl font-bold text-zinc-50 py-0.5 font-sans"
            @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
          />
        </template>
        <template v-else-if="block.type === 'h2'">
          <input
            :ref="el => setBlockRef(el, index)"
            v-model="block.content"
            type="text"
            :placeholder="placeholderFor(index, 'Heading 2')"
            class="flex-1 w-full bg-transparent border-none outline-none text-lg font-semibold text-zinc-100 py-0.5 font-sans"
            @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
          />
        </template>
        <template v-else-if="block.type === 'h3'">
          <input
            :ref="el => setBlockRef(el, index)"
            v-model="block.content"
            type="text"
            :placeholder="placeholderFor(index, 'Heading 3')"
            class="flex-1 w-full bg-transparent border-none outline-none text-sm font-semibold text-zinc-100 py-0.5 font-sans"
            @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
          />
        </template>

        <!-- QUOTE block -->
        <template v-else-if="block.type === 'quote'">
          <div class="flex-1 border-l-2 border-zinc-500 pl-3">
            <input
              :ref="el => setBlockRef(el, index)"
              v-model="block.content"
              type="text"
              :placeholder="placeholderFor(index, 'Quote...')"
              class="w-full bg-transparent border-none outline-none text-sm italic text-zinc-300 py-0.5 font-sans"
              @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
            />
          </div>
        </template>

        <!-- CALLOUT block -->
        <template v-else-if="block.type === 'callout'">
          <div class="flex-1 flex items-start gap-2 p-2.5 rounded-md bg-zinc-900/60 border border-zinc-800">
            <Lightbulb class="w-4 h-4 text-amber-400/80 shrink-0 mt-0.5" />
            <textarea
              :ref="el => setBlockRef(el, index)"
              v-model="block.content"
              rows="1"
              :placeholder="placeholderFor(index, 'Callout note...')"
              class="flex-1 bg-transparent border-none outline-none text-sm text-zinc-100 resize-none font-sans"
              @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
            />
          </div>
        </template>

        <!-- CODE block -->
        <template v-else-if="block.type === 'code'">
          <div class="flex-1 rounded-md bg-zinc-950 border border-zinc-800 overflow-hidden">
            <div class="px-2.5 py-1 border-b border-zinc-800/80 flex items-center justify-between">
              <span class="text-[10px] font-mono uppercase text-zinc-500">{{ block.language || 'code' }}</span>
              <select
                v-model="block.language"
                class="bg-zinc-900 border border-zinc-800 rounded text-[10px] font-mono text-zinc-400 px-1 py-0.5 outline-none"
              >
                <option value="">plain</option>
                <option value="typescript">typescript</option>
                <option value="javascript">javascript</option>
                <option value="python">python</option>
                <option value="bash">bash</option>
                <option value="json">json</option>
                <option value="sql">sql</option>
              </select>
            </div>
            <textarea
              :ref="el => setBlockRef(el, index)"
              v-model="block.content"
              rows="3"
              :placeholder="placeholderFor(index, 'Code snippet...')"
              spellcheck="false"
              class="w-full bg-transparent border-none outline-none text-xs font-mono text-emerald-300/90 p-2.5 resize-y"
              @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
            />
          </div>
        </template>

        <!-- PARAGRAPH (default) -->
        <template v-else>
          <input
            :ref="el => setBlockRef(el, index)"
            v-model="block.content"
            type="text"
            :placeholder="placeholderFor(index, 'Write something...')"
            class="flex-1 bg-transparent border-none outline-none text-sm text-zinc-100 py-0.5 font-sans"
            @input="onBlockInput(index)" @focus="focusedIndex = index" @blur="focusedIndex = -1"
          />
        </template>

        <!-- Slash Command Palette -->
        <div
          v-if="slashMenu.isOpen && slashMenu.blockIndex === index"
          class="absolute z-30 left-6 top-full mt-1 w-64 max-h-64 overflow-y-auto rounded-lg bg-zinc-950 border border-zinc-700/80 shadow-2xl p-1"
        >
          <div class="px-2 py-1 text-[10px] font-mono uppercase text-zinc-500 border-b border-zinc-800/80 mb-1">
            Block Types
          </div>
          <button
            v-for="(option, optIdx) in slashOptions"
            :key="option.type"
            type="button"
            @click="applySlashCommand(option.type)"
            class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-xs text-zinc-300 transition-colors"
            :class="optIdx === slashMenu.selectedIndex ? 'bg-zinc-800 text-zinc-100' : 'hover:bg-zinc-900'"
          >
            <span class="w-5 text-center text-zinc-500 font-mono text-[10px]">{{ option.icon }}</span>
            <span>{{ option.label }}</span>
          </button>
          <div v-if="slashOptions.length === 0" class="px-2 py-2 text-[11px] text-zinc-500 font-mono">
            No matching blocks
          </div>
        </div>
      </div>

      <!-- Empty state (click to create first block) -->
      <button
        v-if="modelValue.length === 0"
        type="button"
        @click="insertBlock('paragraph')"
        class="w-full text-left px-1.5 py-2 text-sm text-zinc-600 font-sans hover:text-zinc-400 transition-colors"
      >
        Empty page. Click here or type <span class="font-mono text-zinc-500">'/'</span> to insert blocks...
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { Check, ChevronDown, ChevronUp, Lightbulb, Trash2 } from 'lucide-vue-next'
import type { NoteBlock, NoteBlockType } from '../../types/workspace'

const props = defineProps<{
  modelValue: NoteBlock[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: NoteBlock[]): void
}>()

const hoveredIndex = ref(-1)
const focusedIndex = ref(-1)
const blockRefs = new Map<number, HTMLInputElement | HTMLTextAreaElement>()

/**
 * Placeholder only appears while a block is focused (or on the first block
 * of the page) — empty lines elsewhere stay completely quiet.
 */
function placeholderFor(index: number, fallback: string): string {
  const block = props.modelValue[index]
  if (!block || block.content) return ''
  if (index === 0) return `Type '/' for commands...`
  if (index === focusedIndex.value) return fallback
  return ''
}

const BLOCK_LIBRARY: Array<{ type: NoteBlockType; label: string; icon: string }> = [
  { type: 'h1', label: 'Heading 1', icon: 'H1' },
  { type: 'h2', label: 'Heading 2', icon: 'H2' },
  { type: 'h3', label: 'Heading 3', icon: 'H3' },
  { type: 'paragraph', label: 'Text', icon: '¶' },
  { type: 'todo', label: 'To-do Checkbox', icon: '☑' },
  { type: 'bullet', label: 'Bullet List', icon: '•' },
  { type: 'numbered', label: 'Numbered List', icon: '1.' },
  { type: 'callout', label: 'Callout Box', icon: '💡' },
  { type: 'code', label: 'Code Block', icon: '{}' },
  { type: 'quote', label: 'Quote', icon: '❝' },
  { type: 'divider', label: 'Divider', icon: '—' }
]

const toolbarItems = BLOCK_LIBRARY

const toolClass = (type: NoteBlockType) => {
  const base = 'bg-zinc-900/60 hover:bg-zinc-800 border-zinc-800 text-zinc-400 hover:text-zinc-200'
  if (type === 'h1' || type === 'h2' || type === 'h3') return `${base} font-bold`
  if (type === 'code') return `${base} font-mono`
  return base
}

const slashMenu = reactive<{
  isOpen: boolean
  blockIndex: number
  query: string
  selectedIndex: number
}>({
  isOpen: false,
  blockIndex: -1,
  query: '',
  selectedIndex: 0
})

const slashOptions = computed(() => {
  const q = slashMenu.query.toLowerCase()
  if (!q) return BLOCK_LIBRARY
  return BLOCK_LIBRARY.filter(b => b.label.toLowerCase().includes(q) || b.type.includes(q))
})

function setBlockRef(el: any, index: number) {
  if (el) {
    blockRefs.set(index, el)
  } else {
    blockRefs.delete(index)
  }
}

function newBlock(type: NoteBlockType = 'paragraph', content = ''): NoteBlock {
  return {
    id: crypto.randomUUID(),
    type,
    content,
    checked: type === 'todo' ? false : undefined,
    language: type === 'code' ? 'typescript' : undefined
  }
}

function update(blocks: NoteBlock[]) {
  emit('update:modelValue', blocks)
}

function focusBlock(index: number, caretEnd = true) {
  nextTick(() => {
    const el = blockRefs.get(index)
    if (!el) return
    el.focus()
    if (caretEnd && 'setSelectionRange' in el) {
      const len = (el as HTMLInputElement).value.length
      ;(el as HTMLInputElement).setSelectionRange(len, len)
    }
  })
}

function insertBlock(type: NoteBlockType, atIndex: number = props.modelValue.length, content = '') {
  const blocks = [...props.modelValue]
  blocks.splice(atIndex, 0, newBlock(type, content))
  update(blocks)
  if (type !== 'divider') {
    focusBlock(atIndex)
  }
}

function removeBlock(index: number) {
  const blocks = props.modelValue.filter((_, i) => i !== index)
  update(blocks)
  if (blocks.length > 0) {
    focusBlock(Math.min(index, blocks.length - 1))
  }
}

function moveBlock(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= props.modelValue.length) return
  const blocks = [...props.modelValue]
  const [moved] = blocks.splice(index, 1)
  blocks.splice(target, 0, moved)
  update(blocks)
  focusBlock(target)
}

function changeBlockType(index: number, type: NoteBlockType) {
  const blocks = [...props.modelValue]
  const block = { ...blocks[index], type }
  if (type === 'todo' && block.checked === undefined) block.checked = false
  if (type === 'code' && !block.language) block.language = 'typescript'
  if (type !== 'todo' && type !== 'code') {
    delete block.checked
    delete block.language
  }
  blocks[index] = block
  update(blocks)
  focusBlock(index)
}

function toggleTodo(index: number) {
  const blocks = [...props.modelValue]
  blocks[index] = { ...blocks[index], checked: !blocks[index].checked }
  update(blocks)
}

function numberFor(index: number): number {
  let count = 1
  for (let i = index - 1; i >= 0; i--) {
    if (props.modelValue[i].type === 'numbered') count++
    else break
  }
  return count
}

function onBlockInput(index: number) {
  const block = props.modelValue[index]
  if (!block) return
  update([...props.modelValue])

  // Slash command: "/" typed at the start of a block opens the palette
  const text = block.content
  if (text.startsWith('/')) {
    slashMenu.isOpen = true
    slashMenu.blockIndex = index
    slashMenu.query = text.slice(1)
    slashMenu.selectedIndex = 0
  } else if (slashMenu.isOpen && slashMenu.blockIndex === index) {
    slashMenu.isOpen = false
    slashMenu.blockIndex = -1
    slashMenu.query = ''
    slashMenu.selectedIndex = 0
  }
}

function applySlashCommand(type: NoteBlockType) {
  const index = slashMenu.blockIndex
  slashMenu.isOpen = false
  slashMenu.query = ''
  slashMenu.blockIndex = -1
  slashMenu.selectedIndex = 0
  if (index < 0 || index >= props.modelValue.length) return

  const blocks = [...props.modelValue]
  const current = blocks[index]

  if (type === 'divider') {
    blocks[index] = { ...newBlock('divider') }
    update(blocks)
    insertBlock('paragraph', index + 1)
    return
  }

  // Strip the "/query" text out of the block so the slash itself never lingers
  const next: NoteBlock = { ...current, type, content: '' }
  if (type === 'todo' && next.checked === undefined) next.checked = false
  if (type === 'code' && !next.language) next.language = 'typescript'
  if (type !== 'todo' && type !== 'code') {
    delete next.checked
    delete next.language
  }
  blocks[index] = next
  update(blocks)
  focusBlock(index)
}

function handleKeydown(event: KeyboardEvent) {
  // Slash palette keyboard navigation takes priority over block editing keys
  if (slashMenu.isOpen) {
    if (event.key === 'Escape') {
      event.preventDefault()
      slashMenu.isOpen = false
      slashMenu.blockIndex = -1
      slashMenu.selectedIndex = 0
      return
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      slashMenu.selectedIndex = Math.min(slashMenu.selectedIndex + 1, Math.max(slashOptions.value.length - 1, 0))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      slashMenu.selectedIndex = Math.max(slashMenu.selectedIndex - 1, 0)
      return
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      const option = slashOptions.value[slashMenu.selectedIndex]
      if (option) {
        applySlashCommand(option.type)
      }
      return
    }
  }

  const target = event.target as HTMLInputElement | HTMLTextAreaElement
  const index = findIndexByRef(target)
  if (index === -1) return

  const isTextarea = target.tagName === 'TEXTAREA'

  // Enter: split block / insert new block below (skip in textarea for multiline input)
  if (event.key === 'Enter' && !event.shiftKey && !isTextarea) {
    event.preventDefault()
    const block = props.modelValue[index]
    const caret = target.selectionStart ?? block.content.length
    const before = block.content.slice(0, caret)
    const after = block.content.slice(caret)

    const blocks = [...props.modelValue]
    blocks[index] = { ...block, content: before }

    const nextType: NoteBlockType = ['bullet', 'numbered', 'todo'].includes(block.type) ? block.type : 'paragraph'
    blocks.splice(index + 1, 0, newBlock(nextType, after))
    update(blocks)
    focusBlock(index + 1, false)
    return
  }

  // Backspace on empty block: remove or convert to paragraph, focus previous
  if (event.key === 'Backspace') {
    const block = props.modelValue[index]
    const caret = target.selectionStart ?? 0
    const selectionEnd = target.selectionEnd ?? 0
    if (block.content.length === 0 || (caret === 0 && selectionEnd === 0)) {
      if (block.type !== 'paragraph') {
        event.preventDefault()
        changeBlockType(index, 'paragraph')
        return
      }
      if (props.modelValue.length > 1) {
        event.preventDefault()
        const prev = props.modelValue[index - 1]
        const blocks = props.modelValue.filter((_, i) => i !== index)
        if (prev.type !== 'divider' && block.content) {
          blocks[index - 1] = { ...prev, content: prev.content + block.content }
        }
        update(blocks)
        focusBlock(index - 1)
      }
    }
  }
}

function findIndexByRef(el: HTMLElement): number {
  for (const [index, refEl] of blockRefs.entries()) {
    if (refEl === el) return index
  }
  return -1
}
</script>
