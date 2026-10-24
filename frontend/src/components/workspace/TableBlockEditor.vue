<template>
  <div class="w-full space-y-1.5" :ref="el => tableRef = el as HTMLElement | null">
    <div class="overflow-x-auto rounded-md border border-zinc-800">
      <table class="w-full border-collapse text-sm">
        <!-- Header row (row 0) -->
        <thead>
          <tr class="group/head">
            <th
              v-for="(_, colIdx) in headerRow"
              :key="'h' + colIdx"
              class="relative border-b border-r border-zinc-800 bg-zinc-900/80 last:border-r-0"
            >
              <div class="flex items-center">
                <input
                  :ref="el => setCellRef(el, 0, colIdx)"
                  v-model="headerRow[colIdx]"
                  type="text"
                  class="w-full bg-transparent px-2.5 py-1.5 text-xs font-semibold text-zinc-100 outline-none placeholder-zinc-600"
                  :placeholder="`Column ${colIdx + 1}`"
                  @input="emitChange()"
                  @keydown.tab.prevent="handleCellTab($event, 0, colIdx)"
                  @keydown.enter.prevent="focusCell(1, colIdx)"
                />
                <button
                  v-if="headerRow.length > 1"
                  type="button"
                  class="mr-1 flex h-4 w-4 items-center justify-center rounded text-zinc-600 opacity-0 transition-all hover:text-rose-400 group-hover/head:opacity-100 shrink-0"
                  title="Delete column"
                  @click="deleteColumn(colIdx)"
                >
                  <X class="w-3 h-3" />
                </button>
              </div>
            </th>
          </tr>
        </thead>

        <!-- Body rows -->
        <tbody>
          <tr v-for="(row, rowIdx) in bodyRows" :key="'r' + rowIdx" class="group/row">
            <td
              v-for="(_, colIdx) in row"
              :key="rowIdx + '-' + colIdx"
              class="relative border-b border-r border-zinc-800/60 bg-zinc-950/40 last:border-r-0"
            >
              <input
                :ref="el => setCellRef(el, rowIdx + 1, colIdx)"
                v-model="bodyRows[rowIdx][colIdx]"
                type="text"
                class="w-full bg-transparent px-2.5 py-1.5 text-xs text-zinc-200 outline-none placeholder-zinc-700"
                placeholder=""
                @input="emitChange()"
                @keydown.tab.prevent="handleCellTab($event, rowIdx + 1, colIdx)"
              />
              <button
                v-if="colIdx === row.length - 1 && block.rows && block.rows.length > 1"
                type="button"
                class="absolute right-1 top-1/2 -translate-y-1/2 flex h-4 w-4 items-center justify-center rounded text-zinc-700 opacity-0 transition-all hover:text-rose-400 group-hover/row:opacity-100"
                title="Delete row"
                @click="deleteRow(rowIdx + 1)"
              >
                <X class="w-3 h-3" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Table controls bar -->
    <div class="flex items-center gap-1.5 opacity-0 group-hover/block:opacity-100 transition-opacity">
      <button
        type="button"
        class="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[10px] font-mono text-zinc-400 hover:text-zinc-100 hover:border-zinc-600 transition-colors"
        @click="addRow"
      >
        + Row
      </button>
      <button
        type="button"
        class="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[10px] font-mono text-zinc-400 hover:text-zinc-100 hover:border-zinc-600 transition-colors"
        @click="addColumn"
      >
        + Column
      </button>
      <span v-if="!isRectangular" class="text-[9px] font-mono text-amber-500/70">irregular grid — edit any cell to normalize</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { X } from 'lucide-vue-next'
import type { NoteBlock } from '../../types/workspace'

const props = defineProps<{
  block: NoteBlock
}>()

const emit = defineEmits<{
  (e: 'changed'): void
}>()

const tableRef = ref<HTMLElement | null>(null)
const cellRefs = new Map<string, HTMLInputElement>()

const DEFAULT_ROWS: string[][] = [['Column 1', 'Column 2', 'Column 3'], ['', '', '']]

// rows live directly on the shared block object (same mutation pattern as the editor)
const headerRow = computed({
  get: () => {
    if (!props.block.rows || props.block.rows.length === 0) {
      props.block.rows = DEFAULT_ROWS.map(r => [...r])
    }
    return props.block.rows[0]
  },
  set: () => {}
})

const bodyRows = computed({
  get: () => {
    if (!props.block.rows || props.block.rows.length <= 1) {
      if (!props.block.rows || props.block.rows.length === 0) {
        props.block.rows = DEFAULT_ROWS.map(r => [...r])
      }
      if (props.block.rows.length === 1) {
        props.block.rows.push(['', '', ''])
      }
    }
    return props.block.rows.slice(1)
  },
  set: () => {}
})

const isRectangular = computed(() => {
  const rows = props.block.rows || []
  if (rows.length === 0) return true
  const width = rows[0].length
  return rows.every(r => r.length === width)
})

function setCellRef(el: any, rowIdx: number, colIdx: number) {
  const key = `${rowIdx}:${colIdx}`
  if (el) {
    cellRefs.set(key, el)
  } else {
    cellRefs.delete(key)
  }
}

function emitChange() {
  emit('changed')
}

function focusCell(rowIdx: number, colIdx: number) {
  nextTick(() => {
    cellRefs.get(`${rowIdx}:${colIdx}`)?.focus()
  })
}

function handleCellTab(_event: KeyboardEvent, rowIdx: number, colIdx: number) {
  const rows = props.block.rows || []
  const cols = rows[0]?.length || 0
  const isLastCell = rowIdx === rows.length - 1 && colIdx === cols - 1

  if (isLastCell) {
    // Tab on the very last cell appends a new row
    rows.push(new Array(cols).fill(''))
    emitChange()
    focusCell(rowIdx + 1, 0)
    return
  }
  if (colIdx < cols - 1) {
    focusCell(rowIdx, colIdx + 1)
  } else {
    focusCell(rowIdx + 1, 0)
  }
}

function addRow() {
  const rows = props.block.rows || (props.block.rows = DEFAULT_ROWS.map(r => [...r]))
  const cols = rows[0]?.length || 3
  rows.push(new Array(cols).fill(''))
  emitChange()
  focusCell(rows.length - 1, 0)
}

function addColumn() {
  const rows = props.block.rows || (props.block.rows = DEFAULT_ROWS.map(r => [...r]))
  if (rows[0].length >= 12) return
  for (const row of rows) {
    row.push('')
  }
  emitChange()
  focusCell(0, rows[0].length - 1)
}

function deleteRow(rowIdx: number) {
  const rows = props.block.rows
  if (!rows || rows.length <= 1) return
  rows.splice(rowIdx, 1)
  emitChange()
}

function deleteColumn(colIdx: number) {
  const rows = props.block.rows
  if (!rows || (rows[0]?.length || 0) <= 1) return
  for (const row of rows) {
    if (row.length > 1) row.splice(colIdx, 1)
  }
  emitChange()
}
</script>
