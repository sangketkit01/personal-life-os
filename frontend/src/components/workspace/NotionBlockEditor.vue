<template>
  <div ref="rootEl" class="relative select-none" @keydown="handleKeydown" @click="handleEditorClick" @paste="handlePaste">
    <!-- Sticky Rich Formatting Toolbar -->
    <div class="sticky top-0 z-20 -mx-1 px-1 py-2 mb-3 border-b border-zinc-800/60 bg-zinc-950/95 backdrop-blur flex items-center gap-1 flex-wrap">
      <!-- Inline styles -->
      <div class="flex items-center gap-0.5 pr-1.5 mr-0.5 border-r border-zinc-800/70">
        <button type="button" class="w-6 h-6 rounded text-xs font-bold transition-colors" :class="toolBtnClass" title="Bold (Ctrl+B)" @mousedown.prevent @click="execFormat('bold')">B</button>
        <button type="button" class="w-6 h-6 rounded text-xs italic transition-colors" :class="toolBtnClass" title="Italic (Ctrl+I)" @mousedown.prevent @click="execFormat('italic')">I</button>
        <button type="button" class="w-6 h-6 rounded text-xs underline transition-colors" :class="toolBtnClass" title="Underline (Ctrl+U)" @mousedown.prevent @click="execFormat('underline')">U</button>
        <button type="button" class="w-6 h-6 rounded text-xs line-through transition-colors" :class="toolBtnClass" title="Strikethrough (Ctrl+Shift+X)" @mousedown.prevent @click="execFormat('strikeThrough')">S</button>
        <button type="button" class="w-6 h-6 rounded text-[10px] font-mono transition-colors" :class="toolBtnClass" title="Inline Code" @mousedown.prevent @click="execInlineCode">&lt;/&gt;</button>
      </div>

      <!-- Colors & highlight -->
      <div class="flex items-center gap-0.5 pr-1.5 mr-0.5 border-r border-zinc-800/70 relative">
        <button type="button" class="h-6 px-1.5 rounded text-xs font-bold transition-colors flex flex-col items-center justify-center leading-none" :class="toolBtnClass" title="Text Color" @mousedown.prevent @click="toggleColorMenu('text')">
          <span>A</span>
          <span class="w-3.5 h-0.5 rounded-full bg-amber-400 mt-0.5" />
        </button>
        <button type="button" class="w-6 h-6 rounded transition-colors flex items-center justify-center" :class="toolBtnClass" title="Highlight" @mousedown.prevent @click="toggleColorMenu('highlight')">
          <Highlighter class="w-3.5 h-3.5" />
        </button>

        <div v-if="colorMenu.open" class="absolute z-40 top-full mt-1 left-0 w-44 rounded-lg bg-zinc-950 border border-zinc-700/80 shadow-2xl p-2">
          <div class="text-[9px] font-mono uppercase text-zinc-500 mb-1.5">{{ colorMenu.mode === 'text' ? 'Text Color' : 'Highlight' }}</div>
          <div class="grid grid-cols-4 gap-1.5">
            <button
              v-for="swatch in colorMenu.mode === 'text' ? TEXT_COLORS : HIGHLIGHT_COLORS"
              :key="swatch.label"
              type="button"
              class="w-8 h-8 rounded-md border border-zinc-800 flex items-center justify-center text-[10px] font-mono transition-transform hover:scale-105"
              :style="swatch.preview"
              :title="swatch.label"
              @mousedown.prevent
              @click="applyColor(swatch)"
            >
              {{ swatch.label === 'None' || swatch.label === 'Default' ? '✕' : 'A' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Hyperlink -->
      <div class="flex items-center gap-0.5 pr-1.5 mr-0.5 border-r border-zinc-800/70">
        <button type="button" class="h-6 px-1.5 rounded transition-colors flex items-center gap-1" :class="toolBtnClass" title="Hyperlink (Ctrl+K)" @mousedown.prevent @click="openLinkPopover()">
          <Link2 class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Block types -->
      <div class="flex items-center gap-0.5 pr-1.5 mr-0.5 border-r border-zinc-800/70">
        <button v-for="bt in BLOCK_TYPE_BUTTONS" :key="bt.type" type="button" class="h-6 px-1.5 rounded text-[10px] font-mono transition-colors" :class="toolBtnClass" :title="bt.title" @mousedown.prevent @click="changeType(bt.type)">
          {{ bt.icon }}
        </button>
      </div>

      <!-- Lists -->
      <div class="flex items-center gap-0.5 pr-1.5 mr-0.5 border-r border-zinc-800/70">
        <button type="button" class="w-6 h-6 rounded transition-colors flex items-center justify-center text-xs" :class="toolBtnClass" title="Bullet List" @mousedown.prevent @click="changeType('bullet')">•</button>
        <button type="button" class="w-6 h-6 rounded transition-colors flex items-center justify-center text-[10px] font-mono" :class="toolBtnClass" title="Ordered List" @mousedown.prevent @click="changeType('numbered')">1.</button>
        <button type="button" class="w-6 h-6 rounded transition-colors flex items-center justify-center" :class="toolBtnClass" title="Checklist" @mousedown.prevent @click="changeType('todo')">
          <ListTodo class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Indent -->
      <div class="flex items-center gap-0.5">
        <button type="button" class="w-6 h-6 rounded transition-colors flex items-center justify-center" :class="toolBtnClass" title="Outdent (Shift+Tab)" @mousedown.prevent @click="adjustIndent(-1)">
          <IndentDecrease class="w-3.5 h-3.5" />
        </button>
        <button type="button" class="w-6 h-6 rounded transition-colors flex items-center justify-center" :class="toolBtnClass" title="Indent (Tab)" @mousedown.prevent @click="adjustIndent(1)">
          <IndentIncrease class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Media & Table -->
      <div class="flex items-center gap-0.5 relative">
        <button type="button" class="w-6 h-6 rounded transition-colors flex items-center justify-center" :class="toolBtnClass" title="Insert Image" @mousedown.prevent @click="toggleImageChooser">
          <ImageIcon class="w-3.5 h-3.5" />
        </button>
        <button type="button" class="w-6 h-6 rounded transition-colors flex items-center justify-center" :class="toolBtnClass" title="Insert Audio / Voice Memo" @mousedown.prevent @click="insertAudioBlock()">
          <Mic class="w-3.5 h-3.5" />
        </button>
        <button type="button" class="w-6 h-6 rounded transition-colors flex items-center justify-center" :class="toolBtnClass" title="Insert Table" @mousedown.prevent @click="insertTableBlock()">
          <Table2 class="w-3.5 h-3.5" />
        </button>

        <div v-if="imageChooserOpen" class="absolute z-40 top-full mt-1 left-0 w-48 rounded-lg bg-zinc-950 border border-zinc-700/80 shadow-2xl p-1">
          <button type="button" class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-xs text-zinc-300 hover:bg-zinc-900 transition-colors" @click="chooseFromGallery">
            <ImageIcon class="w-3.5 h-3.5 text-zinc-500" /> Gallery / Device
          </button>
          <button type="button" class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-xs text-zinc-300 hover:bg-zinc-900 transition-colors" @click="chooseCamera">
            <Camera class="w-3.5 h-3.5 text-zinc-500" /> Take Photo with Camera
          </button>
        </div>
      </div>
    </div>

    <!-- Blocks -->
    <div class="space-y-0.5">
      <div
        v-for="(block, index) in modelValue"
        :key="block.id"
        class="group/block relative flex items-start gap-2 rounded-md px-1.5 py-1 transition-colors hover:bg-zinc-900/30"
        :style="{ marginLeft: `${(block.indent || 0) * 24}px` }"
        @mouseenter="hoveredIndex = index"
        @mouseleave="hoveredIndex = -1"
      >
        <!-- Hover Controls (left gutter) -->
        <div
          v-if="block.type !== 'divider'"
          class="absolute -left-1 top-1/2 -translate-y-1/2 -translate-x-full pr-1 hidden sm:flex items-center gap-0.5 opacity-0 group-hover/block:opacity-100 transition-opacity"
        >
          <button type="button" @click="moveBlock(index, -1)" :disabled="index === 0" class="p-0.5 rounded text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:hover:text-zinc-500" title="Move Up">
            <ChevronUp class="w-3.5 h-3.5" />
          </button>
          <button type="button" @click="moveBlock(index, 1)" :disabled="index === modelValue.length - 1" class="p-0.5 rounded text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:hover:text-zinc-500" title="Move Down">
            <ChevronDown class="w-3.5 h-3.5" />
          </button>
          <button type="button" @click="removeBlock(index)" class="p-0.5 rounded text-zinc-600 hover:text-rose-400" title="Delete Block">
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
          <div
            :ref="el => setBlockRef(el, index)"
            contenteditable="true"
            class="flex-1 outline-none text-sm py-0.5 font-sans min-w-0 break-words rich-editable"
            :class="block.checked ? 'text-zinc-500 line-through' : 'text-zinc-100'"
            @input="onEditableInput(index)"
            @focus="focusedIndex = index; lastFocusedIndex = index"
            @blur="focusedIndex = -1"
          />
          <span v-if="showPlaceholder(index)" class="pointer-events-none absolute left-9 top-1 text-sm text-zinc-600 font-sans">To-do item...</span>
        </template>

        <!-- BULLET block -->
        <template v-else-if="block.type === 'bullet'">
          <span class="w-4 text-center leading-6 shrink-0 text-zinc-400">•</span>
          <div
            :ref="el => setBlockRef(el, index)"
            contenteditable="true"
            class="flex-1 outline-none text-sm text-zinc-100 py-0.5 font-sans min-w-0 break-words rich-editable"
            @input="onEditableInput(index)"
            @focus="focusedIndex = index; lastFocusedIndex = index"
            @blur="focusedIndex = -1"
          />
          <span v-if="showPlaceholder(index)" class="pointer-events-none absolute left-9 top-1 text-sm text-zinc-600 font-sans">List item...</span>
        </template>

        <!-- NUMBERED block -->
        <template v-else-if="block.type === 'numbered'">
          <span class="w-4 text-center leading-6 shrink-0 text-zinc-400 text-xs font-mono">{{ numberFor(index) }}.</span>
          <div
            :ref="el => setBlockRef(el, index)"
            contenteditable="true"
            class="flex-1 outline-none text-sm text-zinc-100 py-0.5 font-sans min-w-0 break-words rich-editable"
            @input="onEditableInput(index)"
            @focus="focusedIndex = index; lastFocusedIndex = index"
            @blur="focusedIndex = -1"
          />
          <span v-if="showPlaceholder(index)" class="pointer-events-none absolute left-9 top-1 text-sm text-zinc-600 font-sans">List item...</span>
        </template>

        <!-- HEADING blocks -->
        <template v-else-if="block.type === 'h1'">
          <div
            :ref="el => setBlockRef(el, index)"
            contenteditable="true"
            class="flex-1 w-full outline-none text-xl font-bold text-zinc-50 py-0.5 font-sans min-w-0 break-words rich-editable"
            @input="onEditableInput(index)"
            @focus="focusedIndex = index; lastFocusedIndex = index"
            @blur="focusedIndex = -1"
          />
          <span v-if="showPlaceholder(index)" class="pointer-events-none absolute left-3 top-1 text-xl font-bold text-zinc-700 font-sans">Heading 1</span>
        </template>
        <template v-else-if="block.type === 'h2'">
          <div
            :ref="el => setBlockRef(el, index)"
            contenteditable="true"
            class="flex-1 w-full outline-none text-lg font-semibold text-zinc-100 py-0.5 font-sans min-w-0 break-words rich-editable"
            @input="onEditableInput(index)"
            @focus="focusedIndex = index; lastFocusedIndex = index"
            @blur="focusedIndex = -1"
          />
          <span v-if="showPlaceholder(index)" class="pointer-events-none absolute left-3 top-1 text-lg font-semibold text-zinc-700 font-sans">Heading 2</span>
        </template>
        <template v-else-if="block.type === 'h3'">
          <div
            :ref="el => setBlockRef(el, index)"
            contenteditable="true"
            class="flex-1 w-full outline-none text-sm font-semibold text-zinc-100 py-0.5 font-sans min-w-0 break-words rich-editable"
            @input="onEditableInput(index)"
            @focus="focusedIndex = index; lastFocusedIndex = index"
            @blur="focusedIndex = -1"
          />
          <span v-if="showPlaceholder(index)" class="pointer-events-none absolute left-3 top-1 text-sm font-semibold text-zinc-700 font-sans">Heading 3</span>
        </template>

        <!-- QUOTE block -->
        <template v-else-if="block.type === 'quote'">
          <div class="flex-1 border-l-2 border-zinc-500 pl-3 min-w-0">
            <div
              :ref="el => setBlockRef(el, index)"
              contenteditable="true"
              class="w-full outline-none text-sm italic text-zinc-300 py-0.5 font-sans break-words rich-editable"
              @input="onEditableInput(index)"
              @focus="focusedIndex = index; lastFocusedIndex = index"
              @blur="focusedIndex = -1"
            />
            <span v-if="showPlaceholder(index)" class="block -mt-6 text-sm italic text-zinc-600 font-sans pointer-events-none">Quote...</span>
          </div>
        </template>

        <!-- CALLOUT block -->
        <template v-else-if="block.type === 'callout'">
          <div class="flex-1 flex items-start gap-2 p-2.5 rounded-md bg-zinc-900/60 border border-zinc-800 min-w-0">
            <Lightbulb class="w-4 h-4 text-amber-400/80 shrink-0 mt-0.5" />
            <div
              :ref="el => setBlockRef(el, index)"
              contenteditable="true"
              class="flex-1 outline-none text-sm text-zinc-100 font-sans break-words rich-editable"
              @input="onEditableInput(index)"
              @focus="focusedIndex = index; lastFocusedIndex = index"
              @blur="focusedIndex = -1"
            />
            <span v-if="showPlaceholder(index)" class="pointer-events-none absolute left-10 top-3 text-sm text-zinc-600 font-sans">Callout note...</span>
          </div>
        </template>

        <!-- CODE block -->
        <template v-else-if="block.type === 'code'">
          <div class="flex-1 rounded-md bg-zinc-950 border border-zinc-800 overflow-hidden min-w-0">
            <div class="px-2.5 py-1 border-b border-zinc-800/80 flex items-center justify-between">
              <span class="text-[10px] font-mono uppercase text-zinc-500">{{ block.language || 'code' }}</span>
              <select
                v-model="block.language"
                class="bg-zinc-900 border border-zinc-800 rounded text-[10px] font-mono text-zinc-400 px-1 py-0.5 outline-none"
                @change="update([...modelValue])"
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
              placeholder="Code snippet..."
              spellcheck="false"
              class="w-full bg-transparent border-none outline-none text-xs font-mono text-emerald-300/90 p-2.5 resize-y"
              @input="update([...modelValue])"
              @focus="focusedIndex = index; lastFocusedIndex = index"
              @blur="focusedIndex = -1"
            />
          </div>
        </template>

        <!-- IMAGE block -->
        <template v-else-if="block.type === 'image'">
          <div class="flex-1 min-w-0">
            <div
              v-if="!block.drive_file_id"
              class="rounded-md border border-dashed p-4 text-center transition-colors"
              :class="uploadingIds.has(block.id) ? 'border-zinc-600 bg-zinc-900/60' : 'border-zinc-800 hover:border-zinc-600 bg-zinc-900/20'"
            >
              <div v-if="uploadingIds.has(block.id)" class="flex items-center justify-center gap-2 text-[11px] text-zinc-400 font-mono">
                <Loader2 class="w-3.5 h-3.5 animate-spin" /> Uploading to Google Drive...
              </div>
              <div v-else class="flex items-center justify-center gap-2 flex-wrap">
                <button type="button" class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] text-zinc-300 transition-colors flex items-center gap-1.5" @click="pickGalleryFor(block.id)">
                  <ImageIcon class="w-3 h-3" /> Upload Image
                </button>
                <button type="button" class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] text-zinc-300 transition-colors flex items-center gap-1.5" @click="openCamera(block.id)">
                  <Camera class="w-3 h-3" /> Take Photo
                </button>
              </div>
            </div>

            <div v-else class="relative group/img mx-auto" :style="{ width: block.width || '100%' }">
              <div v-if="!blobUrls.get(block.drive_file_id!)" class="w-full aspect-video rounded-md bg-zinc-900 border border-zinc-800 animate-pulse flex items-center justify-center">
                <Loader2 class="w-5 h-5 text-zinc-600 animate-spin" />
              </div>
              <img
                v-else
                :src="blobUrls.get(block.drive_file_id!)!"
                class="w-full rounded-md border border-zinc-800 cursor-zoom-in"
                :alt="block.content || block.file_name || 'Note image'"
                @click="openLightbox(block)"
              />
              <div v-if="blobUrls.get(block.drive_file_id!)" class="absolute top-1.5 right-1.5 hidden group-hover/img:flex items-center gap-0.5 p-0.5 rounded-md bg-zinc-950/90 border border-zinc-700/80">
                <button v-for="w in WIDTH_OPTIONS" :key="w" type="button" class="px-1 py-0.5 rounded text-[9px] font-mono transition-colors" :class="block.width === w ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-100'" :title="`Image width ${w}`" @click="setImageWidth(block, w)">{{ w }}</button>
                <span class="w-px h-3.5 bg-zinc-700 mx-0.5" />
                <button type="button" class="p-1 rounded text-zinc-400 hover:text-zinc-100" title="Full screen" @click="openLightbox(block)">
                  <Maximize2 class="w-3 h-3" />
                </button>
                <a v-if="block.file_url" :href="block.file_url" target="_blank" rel="noopener noreferrer" class="p-1 rounded text-zinc-400 hover:text-zinc-100" title="Open in Google Drive">
                  <ExternalLink class="w-3 h-3" />
                </a>
              </div>
            </div>

            <input
              v-model="block.content"
              type="text"
              placeholder="Write a caption..."
              class="mt-1.5 w-full bg-transparent border-none outline-none text-[11px] text-zinc-500 placeholder-zinc-700 font-sans"
              @input="update([...modelValue])"
            />
          </div>
        </template>

        <!-- AUDIO block -->
        <template v-else-if="block.type === 'audio'">
          <div class="flex-1 min-w-0">
            <div v-if="!block.drive_file_id" class="rounded-md border border-dashed border-zinc-800 hover:border-zinc-600 bg-zinc-900/20 p-3 transition-colors">
              <div v-if="uploadingIds.has(block.id)" class="flex items-center gap-2 text-[11px] text-zinc-400 font-mono">
                <Loader2 class="w-3.5 h-3.5 animate-spin" /> Uploading to Google Drive...
              </div>
              <div v-else-if="recorderState.blockId === block.id && recorderState.active" class="flex items-center gap-3 flex-wrap">
                <span class="relative flex items-center justify-center w-3 h-3 shrink-0">
                  <span class="absolute inline-flex w-full h-full rounded-full bg-rose-500 opacity-75 animate-ping" />
                  <span class="relative inline-flex w-3 h-3 rounded-full bg-rose-500" />
                </span>
                <span class="text-xs font-mono text-zinc-200">{{ formatRecorderTime }}</span>
                <button type="button" class="px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-[11px] font-semibold transition-colors" @click="stopRecording">
                  Stop & Save to Drive
                </button>
                <button type="button" class="px-2 py-1 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] text-zinc-400 transition-colors" @click="cancelRecording">
                  Cancel
                </button>
              </div>
              <div v-else class="flex items-center gap-2 flex-wrap">
                <button type="button" class="px-2.5 py-1.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 hover:bg-rose-500/20 text-[11px] font-medium transition-colors flex items-center gap-1.5" @click="startRecording(block.id)">
                  <Mic class="w-3 h-3" /> Record Voice Memo
                </button>
                <button type="button" class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] text-zinc-300 transition-colors flex items-center gap-1.5" @click="pickAudioFor(block.id)">
                  <Upload class="w-3 h-3" /> Choose Audio File
                </button>
              </div>
              <p v-if="recorderState.error" class="mt-2 text-[10px] text-rose-400">{{ recorderState.error }}</p>
            </div>

            <div v-else class="rounded-md bg-zinc-900/60 border border-zinc-800 p-2.5 space-y-2">
              <div class="flex items-center gap-2 min-w-0">
                <Mic class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <input
                  v-model="block.content"
                  type="text"
                  :placeholder="block.file_name || 'Voice memo'"
                  class="flex-1 min-w-0 bg-transparent border-none outline-none text-xs text-zinc-200 placeholder-zinc-500"
                  @input="update([...modelValue])"
                />
                <span class="text-[9px] font-mono text-zinc-600 shrink-0">{{ formatBytes(block.file_size || 0) }}</span>
                <span v-if="block.duration" class="text-[9px] font-mono text-zinc-600 shrink-0">{{ Math.round(block.duration) }}s</span>
                <a v-if="block.file_url" :href="block.file_url" target="_blank" rel="noopener noreferrer" class="p-1 rounded text-zinc-500 hover:text-zinc-200 shrink-0" title="Open in Google Drive">
                  <ExternalLink class="w-3 h-3" />
                </a>
              </div>
              <audio v-if="blobUrls.get(block.drive_file_id!)" controls :src="blobUrls.get(block.drive_file_id!)!" class="w-full h-8" />
              <div v-else class="h-8 rounded bg-zinc-950 border border-zinc-800 animate-pulse flex items-center px-2">
                <Loader2 class="w-3.5 h-3.5 text-zinc-600 animate-spin" />
              </div>
            </div>
          </div>
        </template>

        <!-- TABLE block -->
        <template v-else-if="block.type === 'table'">
          <div class="flex-1 min-w-0">
            <TableBlockEditor :block="block" @changed="update([...modelValue])" />
          </div>
        </template>

        <!-- PARAGRAPH (default) -->
        <template v-else>
          <div
            :ref="el => setBlockRef(el, index)"
            contenteditable="true"
            class="flex-1 outline-none text-sm text-zinc-100 py-0.5 font-sans min-w-0 break-words rich-editable"
            @input="onEditableInput(index)"
            @focus="focusedIndex = index; lastFocusedIndex = index"
            @blur="focusedIndex = -1"
          />
          <span v-if="showPlaceholder(index)" class="pointer-events-none absolute left-3 top-1 text-sm font-sans" :class="index === 0 ? 'text-zinc-600' : 'text-zinc-700'">
            {{ index === 0 ? `Type '/' for commands...` : 'Write something...' }}
          </span>
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

    <!-- Floating Selection Toolbar (bubble) -->
    <div
      v-if="bubble.visible"
      class="absolute z-40 flex items-center gap-0.5 p-1 rounded-lg bg-zinc-900 border border-zinc-700/80 shadow-2xl"
      :style="{ top: `${bubble.top}px`, left: `${bubble.left}px`, transform: 'translateX(-50%)' }"
    >
      <button type="button" class="w-6 h-6 rounded text-xs font-bold text-zinc-300 hover:bg-zinc-800" title="Bold" @mousedown.prevent @click="execFormat('bold')">B</button>
      <button type="button" class="w-6 h-6 rounded text-xs italic text-zinc-300 hover:bg-zinc-800" title="Italic" @mousedown.prevent @click="execFormat('italic')">I</button>
      <button type="button" class="w-6 h-6 rounded text-xs underline text-zinc-300 hover:bg-zinc-800" title="Underline" @mousedown.prevent @click="execFormat('underline')">U</button>
      <button type="button" class="w-6 h-6 rounded text-xs line-through text-zinc-300 hover:bg-zinc-800" title="Strikethrough" @mousedown.prevent @click="execFormat('strikeThrough')">S</button>
      <span class="w-px h-4 bg-zinc-700 mx-0.5" />
      <button type="button" class="h-6 px-1 rounded text-zinc-300 hover:bg-zinc-800" title="Text Color" @mousedown.prevent @click="openBubbleColorMenu('text')"><Highlighter class="w-3.5 h-3.5" /></button>
      <button type="button" class="w-6 h-6 rounded text-zinc-300 hover:bg-zinc-800 flex items-center justify-center" title="Hyperlink" @mousedown.prevent @click="openLinkPopover()">
        <Link2 class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- Link Popover (apply / remove) -->
    <div
      v-if="linkPopover.open"
      class="fixed z-50 w-72 rounded-lg bg-zinc-950 border border-zinc-700/80 shadow-2xl p-3 space-y-2"
      :style="{ top: `${linkPopover.top}px`, left: `${linkPopover.left}px` }"
    >
      <div class="text-[10px] font-mono uppercase text-zinc-500">Insert Hyperlink</div>
      <input
        v-model="linkPopover.text"
        type="text"
        placeholder="Link text"
        class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600"
      />
      <input
        v-model="linkPopover.url"
        type="url"
        placeholder="https://..."
        class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600"
        @keydown.enter.prevent="applyLink()"
      />
      <div class="flex items-center justify-between pt-1">
        <button type="button" class="text-[11px] text-zinc-500 hover:text-rose-400 transition-colors" @mousedown.prevent @click="removeLink()">
          Remove Link
        </button>
        <div class="flex items-center gap-1.5">
          <button type="button" class="px-2 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-300 hover:text-zinc-100" @click="linkPopover.open = false">Cancel</button>
          <button type="button" class="px-2.5 py-1 rounded-md bg-zinc-100 text-zinc-950 text-[11px] font-semibold hover:bg-white" @mousedown.prevent @click="applyLink()">Apply</button>
        </div>
      </div>
    </div>

    <!-- Existing Link Mini-Popover -->
    <div
      v-if="linkMenu.open"
      class="fixed z-50 flex items-center gap-1 p-1 rounded-lg bg-zinc-950 border border-zinc-700/80 shadow-2xl"
      :style="{ top: `${linkMenu.top}px`, left: `${linkMenu.left}px` }"
    >
      <a
        :href="linkMenu.href"
        target="_blank"
        rel="noopener noreferrer"
        class="px-2 py-1 rounded text-[11px] text-zinc-300 hover:bg-zinc-800 max-w-[180px] truncate"
        :title="linkMenu.href"
      >
        Open Link ↗
      </a>
      <button type="button" class="px-2 py-1 rounded text-[11px] text-zinc-400 hover:text-rose-400 hover:bg-zinc-800" @click="unlinkAt(linkMenu.anchor)">
        Unlink
      </button>
    </div>

    <!-- Live Camera Capture Modal -->
    <Teleport to="body">
      <div v-if="cameraState.open" class="fixed inset-0 z-[60] bg-black/85 backdrop-blur-sm flex items-center justify-center p-4 font-sans">
        <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-lg p-4 shadow-2xl relative">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-zinc-100">Take Photo</h3>
            <button type="button" class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900 transition-colors" @click="closeCamera">
              <X class="w-4 h-4" />
            </button>
          </div>

          <div class="relative rounded-lg overflow-hidden bg-zinc-900 border border-zinc-800 aspect-video">
            <video v-show="!cameraState.capturedDataUrl && cameraState.stream" ref="cameraVideo" autoplay playsinline muted class="w-full h-full object-cover" />
            <img v-if="cameraState.capturedDataUrl" :src="cameraState.capturedDataUrl" class="w-full h-full object-cover" alt="Captured photo preview" />
            <div v-if="cameraState.error" class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center p-6">
              <Camera class="w-6 h-6 text-zinc-600" />
              <p class="text-xs text-zinc-400">{{ cameraState.error }}</p>
              <button type="button" class="px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-300 hover:text-zinc-100" @click="cameraFallbackInput?.click()">
                Choose from device instead
              </button>
            </div>
          </div>

          <div class="flex items-center justify-center gap-4 mt-4 min-h-[48px]">
            <template v-if="!cameraState.capturedDataUrl">
              <button type="button" class="p-2 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-zinc-100 transition-colors" title="Flip camera" @click="flipCamera">
                <SwitchCamera class="w-4 h-4" />
              </button>
              <button type="button" class="w-12 h-12 rounded-full border-4 border-zinc-100 bg-zinc-950 hover:bg-zinc-900 transition-colors disabled:opacity-40" title="Capture photo" :disabled="!cameraState.stream" @click="capturePhoto" />
              <span class="w-8" />
            </template>
            <template v-else>
              <button type="button" class="px-3 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 hover:text-zinc-100" @click="cameraState.capturedDataUrl = ''">Retake</button>
              <button type="button" class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors" @click="usePhoto">Use Photo</button>
            </template>
          </div>

          <input ref="cameraFallbackInput" type="file" accept="image/*" capture="environment" class="hidden" @change="onCameraFallbackSelected" />
        </div>
      </div>

      <!-- Image Lightbox -->
      <div v-if="lightbox.open" class="fixed inset-0 z-[60] bg-black/90 flex flex-col items-center justify-center p-6" @click.self="lightbox.open = false">
        <img :src="lightbox.url" class="max-w-full max-h-[78vh] rounded-md border border-zinc-800" :alt="lightbox.caption" />
        <div class="flex items-center gap-3 mt-4">
          <span class="text-xs text-zinc-400">{{ lightbox.caption }}</span>
          <a v-if="lightbox.driveUrl" :href="lightbox.driveUrl" target="_blank" rel="noopener noreferrer" class="text-xs text-zinc-300 hover:text-zinc-100 underline">Open in Drive</a>
          <button type="button" class="px-3 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 hover:text-zinc-100" @click="lightbox.open = false">Close</button>
        </div>
      </div>
    </Teleport>

    <!-- Hidden media file inputs -->
    <input ref="galleryInput" type="file" accept="image/*" class="hidden" @change="onGallerySelected" />
    <input ref="audioInput" type="file" accept="audio/*" class="hidden" @change="onAudioFileSelected" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import {
  Camera,
  Check,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Highlighter,
  Image as ImageIcon,
  IndentDecrease,
  IndentIncrease,
  Lightbulb,
  Link2,
  ListTodo,
  Loader2,
  Maximize2,
  Mic,
  SwitchCamera,
  Table2,
  Trash2,
  Upload,
  X
} from 'lucide-vue-next'
import TableBlockEditor from './TableBlockEditor.vue'
import apiClient from '../../api/client'
import { useStorageStore } from '../../stores/storage'
import { useToastStore } from '../../stores/toast'
import type { NoteBlock, NoteBlockType } from '../../types/workspace'
import { isEmptyHtml, sanitizeRichHTML, stripHtml } from '../../utils/richText'

const props = defineProps<{
  modelValue: NoteBlock[]
  uploadTargetId?: string | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: NoteBlock[]): void
}>()

const storageStore = useStorageStore()
const toast = useToastStore()

const hoveredIndex = ref(-1)
const focusedIndex = ref(-1)
const lastFocusedIndex = ref(-1)
const rootEl = ref<HTMLElement | null>(null)
const blockRefs = new Map<number, HTMLElement>()

// Selection snapshot kept while focus sits inside a popover (link / color menus)
let savedRange: Range | null = null
let savedBlockIndex = -1

function saveSelectionState() {
  savedRange = null
  savedBlockIndex = -1
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return
  const range = sel.getRangeAt(0)
  if (!rootEl.value || !rootEl.value.contains(range.commonAncestorContainer)) return
  savedRange = range.cloneRange()
  savedBlockIndex = findIndexForNode(range.startContainer)
}

function restoreSelection() {
  const el = blockRefs.get(savedBlockIndex)
  if (el && isEditable(el)) {
    el.focus()
  }
  const sel = window.getSelection()
  if (savedRange && sel) {
    sel.removeAllRanges()
    sel.addRange(savedRange)
  }
}

function findIndexForNode(node: Node | null): number {
  let cur: Node | null = node
  while (cur) {
    if (cur.nodeType === Node.ELEMENT_NODE) {
      const idx = findIndexByRef(cur as HTMLElement)
      if (idx !== -1) return idx
    }
    cur = cur.parentNode
  }
  return -1
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
  { type: 'divider', label: 'Divider', icon: '—' },
  { type: 'image', label: 'Image', icon: '🖼' },
  { type: 'audio', label: 'Audio / Voice Memo', icon: '🎙' },
  { type: 'table', label: 'Table', icon: '▦' }
]

const BLOCK_TYPE_BUTTONS: Array<{ type: NoteBlockType; icon: string; title: string }> = [
  { type: 'paragraph', icon: 'P', title: 'Text' },
  { type: 'h1', icon: 'H1', title: 'Heading 1' },
  { type: 'h2', icon: 'H2', title: 'Heading 2' },
  { type: 'h3', icon: 'H3', title: 'Heading 3' },
  { type: 'quote', icon: '❝', title: 'Quote' },
  { type: 'callout', icon: '💡', title: 'Callout' },
  { type: 'divider', icon: '—', title: 'Divider' }
]

const toolBtnClass = 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800'

const TEXT_COLORS = [
  { label: 'Default', value: '#f4f4f5', preview: { background: '#27272a', color: '#f4f4f5' } },
  { label: 'Muted', value: '#a1a1aa', preview: { background: '#27272a', color: '#a1a1aa' } },
  { label: 'Amber', value: '#fbbf24', preview: { background: '#27272a', color: '#fbbf24' } },
  { label: 'Emerald', value: '#34d399', preview: { background: '#27272a', color: '#34d399' } },
  { label: 'Sky', value: '#38bdf8', preview: { background: '#27272a', color: '#38bdf8' } },
  { label: 'Violet', value: '#a78bfa', preview: { background: '#27272a', color: '#a78bfa' } },
  { label: 'Rose', value: '#fb7185', preview: { background: '#27272a', color: '#fb7185' } }
]

const HIGHLIGHT_COLORS = [
  { label: 'None', value: 'transparent', preview: { background: '#18181b', color: '#a1a1aa' } },
  { label: 'Amber', value: 'rgba(251, 191, 36, 0.22)', preview: { background: 'rgba(251, 191, 36, 0.22)', color: '#fbbf24' } },
  { label: 'Emerald', value: 'rgba(52, 211, 153, 0.22)', preview: { background: 'rgba(52, 211, 153, 0.22)', color: '#34d399' } },
  { label: 'Sky', value: 'rgba(56, 189, 248, 0.22)', preview: { background: 'rgba(56, 189, 248, 0.22)', color: '#38bdf8' } },
  { label: 'Violet', value: 'rgba(167, 139, 250, 0.22)', preview: { background: 'rgba(167, 139, 250, 0.22)', color: '#a78bfa' } },
  { label: 'Rose', value: 'rgba(251, 113, 133, 0.22)', preview: { background: 'rgba(251, 113, 133, 0.22)', color: '#fb7185' } }
]

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

const bubble = reactive({ visible: false, top: 0, left: 0 })
const colorMenu = reactive<{ open: boolean; mode: 'text' | 'highlight' }>({ open: false, mode: 'text' })
const linkPopover = reactive({ open: false, top: 0, left: 0, text: '', url: '', hadSelection: false })
const linkMenu = reactive({ open: false, top: 0, left: 0, href: '', anchor: null as HTMLAnchorElement | null })

// ===== Refs & DOM sync =====

function isEditable(el: HTMLElement): boolean {
  return el.isContentEditable
}

function setBlockRef(el: any, index: number) {
  if (el) {
    const prev = blockRefs.get(index)
    blockRefs.set(index, el)
    const block = props.modelValue[index]
    if (
      el !== prev &&
      block &&
      isEditable(el) &&
      document.activeElement !== el &&
      el.innerHTML !== block.content
    ) {
      el.innerHTML = block.content || ''
    }
  } else {
    blockRefs.delete(index)
  }
}

const TABLE_DEFAULT_ROWS: string[][] = [['Column 1', 'Column 2', 'Column 3'], ['', '', '']]
const WIDTH_OPTIONS: Array<'50%' | '75%' | '100%'> = ['50%', '75%', '100%']

function newBlock(type: NoteBlockType = 'paragraph', content = ''): NoteBlock {
  const block: NoteBlock = {
    id: crypto.randomUUID(),
    type,
    content,
    checked: type === 'todo' ? false : undefined,
    indent: 0,
    language: type === 'code' ? 'typescript' : undefined
  }
  if (type === 'table') {
    block.rows = TABLE_DEFAULT_ROWS.map(r => [...r])
  }
  if (type === 'image') {
    block.width = '100%'
  }
  return block
}

function update(blocks: NoteBlock[]) {
  emit('update:modelValue', blocks)
}

function focusBlock(index: number, caretEnd = true) {
  nextTick(() => {
    const el = blockRefs.get(index)
    if (!el) return
    if (isEditable(el)) {
      el.focus()
      if (caretEnd) placeCaretAtEnd(el)
    } else {
      ;(el as HTMLTextAreaElement).focus()
    }
  })
}

function placeCaretAtEnd(el: HTMLElement) {
  const range = document.createRange()
  range.selectNodeContents(el)
  range.collapse(false)
  const sel = window.getSelection()
  sel?.removeAllRanges()
  sel?.addRange(range)
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

function currentEditableIndex(): number {
  const active = document.activeElement
  if (active) {
    const idx = findIndexByRef(active as HTMLElement)
    if (idx !== -1) return idx
  }
  if (focusedIndex.value >= 0) return focusedIndex.value
  if (lastFocusedIndex.value >= 0 && lastFocusedIndex.value < props.modelValue.length) {
    return lastFocusedIndex.value
  }
  return Math.max(props.modelValue.length - 1, 0)
}

function changeType(type: NoteBlockType) {
  const index = currentEditableIndex()
  if (index < 0 || index >= props.modelValue.length) return
  changeBlockType(index, type)
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

function adjustIndent(delta: -1 | 1) {
  const index = currentEditableIndex()
  if (index < 0 || index >= props.modelValue.length) return
  const blocks = [...props.modelValue]
  const block = blocks[index]
  if (block.type === 'divider' || block.type === 'code') return
  block.indent = Math.max(0, Math.min(4, (block.indent || 0) + delta))
  update(blocks)
  focusBlock(index)
}

function numberFor(index: number): number {
  const ref = props.modelValue[index]
  let count = 1
  for (let i = index - 1; i >= 0; i--) {
    const b = props.modelValue[i]
    if (b.type === 'numbered' && (b.indent || 0) === (ref.indent || 0)) count++
    else break
  }
  return count
}

// ===== Rich text editing =====

function execFormat(command: string, value?: string) {
  document.execCommand('styleWithCSS', false, 'true')
  document.execCommand(command, false, value)
  const index = currentEditableIndex()
  syncBlockFromDom(index)
}

function execInlineCode() {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return
  const text = sel.toString()
  if (!text) return
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  document.execCommand('insertHTML', false, `<code>${escaped}</code>`)
  syncBlockFromDom(currentEditableIndex())
}

function syncBlockFromDom(index: number) {
  const el = blockRefs.get(index)
  const block = props.modelValue[index]
  if (!el || !block || !isEditable(el)) return
  block.content = sanitizeRichHTML(el.innerHTML)
  update([...props.modelValue])
}

function toggleColorMenu(mode: 'text' | 'highlight') {
  colorMenu.open = colorMenu.open && colorMenu.mode === mode ? false : true
  colorMenu.mode = mode
  if (colorMenu.open) {
    saveSelectionState()
    bubble.visible = false
  }
}

function openBubbleColorMenu(mode: 'text' | 'highlight') {
  saveSelectionState()
  colorMenu.mode = mode
  colorMenu.open = true
}

function applyColor(swatch: { label: string; value: string }) {
  colorMenu.open = false
  restoreSelection()
  if (colorMenu.mode === 'text') {
    execFormat('foreColor', swatch.value)
  } else {
    execFormat('hiliteColor', swatch.value)
  }
  if (savedBlockIndex !== -1) {
    syncBlockFromDom(savedBlockIndex)
  }
}

// ===== Link handling =====

function openLinkPopover() {
  saveSelectionState()
  const sel = window.getSelection()
  const selectedText = sel ? sel.toString() : ''
  linkPopover.text = selectedText
  linkPopover.url = ''
  linkPopover.hadSelection = Boolean(selectedText)
  const rect = sel && sel.rangeCount > 0 ? sel.getRangeAt(0).getBoundingClientRect() : null
  const hostRect = rootEl.value?.getBoundingClientRect()
  linkPopover.top = Math.max(8, (rect?.bottom ?? 100) + 8)
  linkPopover.left = Math.max(8, Math.min((rect?.left ?? hostRect?.left ?? 100), (window.innerWidth || 800) - 300))
  linkPopover.open = true
  bubble.visible = false
  nextTick(() => {
    const input = document.querySelector('input[placeholder="https://..."]') as HTMLInputElement | null
    input?.focus()
  })
}

function applyLink() {
  const url = linkPopover.url.trim()
  if (!url || !/^https?:\/\//i.test(url)) {
    linkPopover.open = false
    return
  }
  restoreSelection()
  const text = linkPopover.text.trim() || url
  const escapedText = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const escapedUrl = url.replace(/"/g, '&quot;')
  document.execCommand('insertHTML', false, `<a href="${escapedUrl}" target="_blank" rel="noopener noreferrer">${escapedText}</a>`)
  linkPopover.open = false
  syncBlockFromDom(savedBlockIndex !== -1 ? savedBlockIndex : currentEditableIndex())
}

function removeLink() {
  restoreSelection()
  document.execCommand('unlink')
  linkPopover.open = false
  syncBlockFromDom(savedBlockIndex !== -1 ? savedBlockIndex : currentEditableIndex())
}

function handleEditorClick(event: MouseEvent) {
  linkMenu.open = false
  const target = event.target as HTMLElement
  const anchor = target.closest?.('a') as HTMLAnchorElement | null
  if (anchor && rootEl.value?.contains(anchor)) {
    const rect = anchor.getBoundingClientRect()
    linkMenu.href = anchor.getAttribute('href') || '#'
    linkMenu.anchor = anchor
    linkMenu.top = rect.bottom + 6
    linkMenu.left = Math.max(8, Math.min(rect.left, (window.innerWidth || 800) - 220))
    linkMenu.open = true
    event.preventDefault()
  }
}

function unlinkAt(anchor: HTMLAnchorElement | null) {
  linkMenu.open = false
  if (!anchor) return
  const range = document.createRange()
  range.selectNode(anchor)
  const sel = window.getSelection()
  sel?.removeAllRanges()
  sel?.addRange(range)
  document.execCommand('unlink')
  const index = findIndexByRef(anchor.closest('.rich-editable') as HTMLElement)
  if (index !== -1) syncBlockFromDom(index)
}

// ===== Selection bubble =====

function handleSelectionChange() {
  if (linkPopover.open || linkMenu.open || colorMenu.open) return
  const sel = window.getSelection()
  if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
    bubble.visible = false
    return
  }
  const range = sel.getRangeAt(0)
  const container = rootEl.value
  if (!container || !container.contains(range.commonAncestorContainer)) {
    bubble.visible = false
    return
  }
  const rect = range.getBoundingClientRect()
  const hostRect = container.getBoundingClientRect()
  if (rect.width === 0 && rect.height === 0) {
    bubble.visible = false
    return
  }
  bubble.top = rect.top - hostRect.top - 42
  bubble.left = rect.left - hostRect.left + rect.width / 2
  bubble.visible = true
}

// ===== Input / keyboard / paste =====

function onEditableInput(index: number) {
  const el = blockRefs.get(index)
  const block = props.modelValue[index]
  if (!el || !block) return
  block.content = sanitizeRichHTML(el.innerHTML)
  update([...props.modelValue])

  // Slash command: "/" typed at the start of a block opens the palette
  const text = stripHtml(block.content)
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

function handlePaste(event: ClipboardEvent) {
  const target = event.target as HTMLElement
  if (!target.isContentEditable) return

  // Clipboard image paste -> inline image block streamed straight to Google Drive
  const files = Array.from(event.clipboardData?.files || [])
  const imageFile = files.find(f => f.type.startsWith('image/'))
  if (imageFile) {
    event.preventDefault()
    const blockId = insertImageBlock()
    uploadMediaToBlock(blockId, imageFile)
    return
  }

  event.preventDefault()
  const html = event.clipboardData?.getData('text/html')
  const text = event.clipboardData?.getData('text/plain')
  if (html) {
    document.execCommand('insertHTML', false, sanitizeRichHTML(html))
  } else if (text) {
    document.execCommand('insertText', false, text)
  }
  const index = findIndexByRef(target)
  if (index !== -1) syncBlockFromDom(index)
}

function showPlaceholder(index: number): boolean {
  const block = props.modelValue[index]
  if (!block || !isEmptyHtml(block.content)) return false
  if (index === 0) return true
  return index === focusedIndex.value
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

  // Media & table blocks are inserted as fresh blocks (never convert the text block)
  if (type === 'image' || type === 'audio' || type === 'table') {
    const fresh = newBlock(type)
    blocks[index] = { id: current.id, type: 'paragraph', content: '' }
    blocks.splice(index + 1, 0, fresh)
    update(blocks)
    focusBlock(index)
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
  const el = blockRefs.get(index)
  if (el && isEditable(el)) {
    el.innerHTML = ''
  }
  focusBlock(index)
}

function splitAtCaret(el: HTMLElement): [string, string] {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return [el.innerHTML, '']
  const range = sel.getRangeAt(0)

  const beforeRange = range.cloneRange()
  beforeRange.selectNodeContents(el)
  beforeRange.setEnd(range.startContainer, range.startOffset)

  const afterRange = range.cloneRange()
  afterRange.selectNodeContents(el)
  afterRange.setStart(range.endContainer, range.endOffset)

  const beforeDiv = document.createElement('div')
  beforeDiv.appendChild(beforeRange.cloneContents())
  const afterDiv = document.createElement('div')
  afterDiv.appendChild(afterRange.cloneContents())

  return [sanitizeRichHTML(beforeDiv.innerHTML), sanitizeRichHTML(afterDiv.innerHTML)]
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

  const target = event.target as HTMLElement
  const index = findIndexByRef(target)
  if (index === -1) return

  const isEditableTarget = target.isContentEditable
  const block = props.modelValue[index]

  // Ctrl/Meta shortcuts for inline formatting
  if ((event.ctrlKey || event.metaKey) && isEditableTarget) {
    const key = event.key.toLowerCase()
    if (key === 'b') {
      event.preventDefault()
      execFormat('bold')
      return
    }
    if (key === 'i') {
      event.preventDefault()
      execFormat('italic')
      return
    }
    if (key === 'u') {
      event.preventDefault()
      execFormat('underline')
      return
    }
    if (event.shiftKey && key === 'x') {
      event.preventDefault()
      execFormat('strikeThrough')
      return
    }
    if (key === 'k') {
      event.preventDefault()
      openLinkPopover()
      return
    }
  }

  // Tab / Shift+Tab indent & outdent
  if (event.key === 'Tab' && isEditableTarget && block.type !== 'code') {
    event.preventDefault()
    adjustIndent(event.shiftKey ? -1 : 1)
    return
  }

  // Enter: split block / continue lists
  if (event.key === 'Enter' && !event.shiftKey && isEditableTarget) {
    event.preventDefault()
    const [beforeHTML, afterHTML] = splitAtCaret(target as HTMLElement)
    const isList = ['bullet', 'numbered', 'todo'].includes(block.type)

    // Enter on an empty list item exits the list (outdent or reset to paragraph)
    if (isList && isEmptyHtml(block.content)) {
      if ((block.indent || 0) > 0) {
        const blocks = [...props.modelValue]
        blocks[index] = { ...block, indent: (block.indent || 0) - 1 }
        update(blocks)
        focusBlock(index)
      } else {
        changeBlockType(index, 'paragraph')
      }
      return
    }

    const blocks = [...props.modelValue]
    blocks[index] = { ...block, content: beforeHTML }

    let nextType: NoteBlockType = 'paragraph'
    let nextIndent = 0
    if (isList) {
      nextType = block.type
      nextIndent = block.indent || 0
    } else if (block.type === 'quote' || block.type === 'callout') {
      nextType = block.type
      nextIndent = block.indent || 0
    }
    blocks.splice(index + 1, 0, { ...newBlock(nextType, afterHTML), indent: nextIndent })
    update(blocks)
    focusBlock(index + 1, false)
    return
  }

  // Backspace on empty block: remove or convert to paragraph, focus previous
  if (event.key === 'Backspace') {
    const caret = (target as HTMLElement).isContentEditable
      ? isCaretAtStart(target as HTMLElement)
      : (target as HTMLTextAreaElement).selectionStart === 0
    const textEmpty = isEmptyHtml(block.content)
    if (!textEmpty && !caret) return

    if (block.type !== 'paragraph' && block.type !== 'code') {
      event.preventDefault()
      changeBlockType(index, 'paragraph')
      return
    }
    if (props.modelValue.length > 1 && textEmpty) {
      event.preventDefault()
      const prev = props.modelValue[index - 1]
      const blocks = props.modelValue.filter((_, i) => i !== index)
      update(blocks)
      focusBlock(index - 1)
      void prev
    }
  }
}

function isCaretAtStart(el: HTMLElement): boolean {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0 || !sel.isCollapsed) return false
  const range = sel.getRangeAt(0)
  const startRange = document.createRange()
  startRange.selectNodeContents(el)
  startRange.setEnd(range.startContainer, range.startOffset)
  return stripHtml(startRange.toString()) === ''
}

function findIndexByRef(el: HTMLElement | null): number {
  if (!el) return -1
  for (const [index, refEl] of blockRefs.entries()) {
    if (refEl === el || refEl.contains(el)) return index
  }
  return -1
}

// ===== Media blocks (image / audio / table) =====

const imageChooserOpen = ref(false)
const pendingMediaBlockId = ref('')
const galleryInput = ref<HTMLInputElement | null>(null)
const audioInput = ref<HTMLInputElement | null>(null)
const cameraFallbackInput = ref<HTMLInputElement | null>(null)
const uploadingIds = reactive(new Set<string>())

function insertImageBlock(): string {
  const blocks = [...props.modelValue]
  const block = newBlock('image')
  blocks.push(block)
  update(blocks)
  return block.id
}

function insertAudioBlock() {
  const blocks = [...props.modelValue]
  blocks.push(newBlock('audio'))
  update(blocks)
}

function insertTableBlock() {
  const blocks = [...props.modelValue]
  blocks.push(newBlock('table'))
  update(blocks)
}

function toggleImageChooser() {
  imageChooserOpen.value = !imageChooserOpen.value
}

function chooseFromGallery() {
  imageChooserOpen.value = false
  pendingMediaBlockId.value = insertImageBlock()
  galleryInput.value?.click()
}

function chooseCamera() {
  imageChooserOpen.value = false
  const blockId = insertImageBlock()
  openCamera(blockId)
}

function pickGalleryFor(blockId: string) {
  pendingMediaBlockId.value = blockId
  galleryInput.value?.click()
}

function pickAudioFor(blockId: string) {
  pendingMediaBlockId.value = blockId
  audioInput.value?.click()
}

async function onGallerySelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  const blockId = pendingMediaBlockId.value
  pendingMediaBlockId.value = ''
  if (file && blockId) {
    await uploadMediaToBlock(blockId, file)
  }
}

async function onAudioFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  const blockId = pendingMediaBlockId.value
  pendingMediaBlockId.value = ''
  if (file && blockId) {
    await uploadMediaToBlock(blockId, file)
  }
}

async function uploadMediaToBlock(blockId: string, file: File, duration?: number) {
  const index = props.modelValue.findIndex(b => b.id === blockId)
  if (index === -1) return
  if (!props.uploadTargetId) {
    toast.error('Save the note before attaching media')
    return
  }
  uploadingIds.add(blockId)
  try {
    const saved = await storageStore.uploadDirect(file, 'note', props.uploadTargetId)
    const blocks = [...props.modelValue]
    const idx = blocks.findIndex(b => b.id === blockId)
    if (idx !== -1) {
      blocks[idx] = {
        ...blocks[idx],
        drive_file_id: saved.drive_file_id,
        file_url: saved.web_view_link || saved.web_content_link || '',
        file_name: file.name,
        file_type: file.type || 'application/octet-stream',
        file_size: file.size,
        ...(duration !== undefined ? { duration } : {})
      }
      update(blocks)
      loadBlob(saved.drive_file_id)
    }
    toast.success('Media uploaded to Google Drive')
  } catch (err: any) {
    toast.error(err?.message || 'Failed to upload media to Google Drive')
  } finally {
    uploadingIds.delete(blockId)
  }
}

function setImageWidth(block: NoteBlock, width: '50%' | '75%' | '100%') {
  const blocks = [...props.modelValue]
  const idx = blocks.findIndex(b => b.id === block.id)
  if (idx === -1) return
  blocks[idx] = { ...blocks[idx], width }
  update(blocks)
}

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, exp)).toFixed(exp === 0 ? 0 : 1)} ${units[exp]}`
}

// ===== Blob resolution via the authenticated Drive stream endpoint =====

const blobUrls = reactive(new Map<string, string>())
const loadingBlobs = reactive(new Set<string>())

async function loadBlob(driveFileId: string) {
  if (blobUrls.has(driveFileId) || loadingBlobs.has(driveFileId)) return
  loadingBlobs.add(driveFileId)
  try {
    const res = await apiClient.get(`/storage/files/${driveFileId}/stream/`, { responseType: 'blob' })
    blobUrls.set(driveFileId, URL.createObjectURL(res.data))
  } catch {
    // Left unresolved - the UI keeps showing a loading skeleton
  } finally {
    loadingBlobs.delete(driveFileId)
  }
}

watch(
  () => props.modelValue,
  () => {
    for (const block of props.modelValue) {
      if ((block.type === 'image' || block.type === 'audio') && block.drive_file_id) {
        loadBlob(block.drive_file_id)
      }
    }
  },
  { immediate: true }
)

// ===== Lightbox =====

const lightbox = reactive({ open: false, url: '', caption: '', driveUrl: '' })

function openLightbox(block: NoteBlock) {
  const url = block.drive_file_id ? blobUrls.get(block.drive_file_id) : ''
  if (!url) return
  lightbox.url = url
  lightbox.caption = block.content || block.file_name || ''
  lightbox.driveUrl = block.file_url || ''
  lightbox.open = true
}

// ===== Live camera capture =====

const cameraState = reactive({
  open: false,
  facingMode: 'environment',
  stream: null as MediaStream | null,
  capturedDataUrl: '',
  error: ''
})
const cameraVideo = ref<HTMLVideoElement | null>(null)
let cameraPendingBlockId = ''

async function openCamera(blockId: string) {
  cameraPendingBlockId = blockId
  cameraState.open = true
  cameraState.capturedDataUrl = ''
  cameraState.error = ''
  nextTick(async () => {
    try {
      cameraState.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: cameraState.facingMode },
        audio: false
      })
      if (cameraVideo.value) {
        cameraVideo.value.srcObject = cameraState.stream
        await cameraVideo.value.play().catch(() => {})
      }
    } catch {
      cameraState.error = 'Camera unavailable. Use the device gallery instead.'
    }
  })
}

function closeCamera() {
  cameraState.stream?.getTracks().forEach(t => t.stop())
  cameraState.stream = null
  cameraState.open = false
  cameraState.capturedDataUrl = ''
}

async function flipCamera() {
  cameraState.facingMode = cameraState.facingMode === 'environment' ? 'user' : 'environment'
  cameraState.stream?.getTracks().forEach(t => t.stop())
  try {
    cameraState.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: cameraState.facingMode },
      audio: false
    })
    if (cameraVideo.value) {
      cameraVideo.value.srcObject = cameraState.stream
      await cameraVideo.value.play().catch(() => {})
    }
  } catch {
    cameraState.error = 'Could not switch camera.'
  }
}

function capturePhoto() {
  const video = cameraVideo.value
  if (!video || !video.videoWidth) return
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d')?.drawImage(video, 0, 0)
  cameraState.capturedDataUrl = canvas.toDataURL('image/jpeg', 0.92)
}

async function usePhoto() {
  if (!cameraState.capturedDataUrl || !cameraPendingBlockId) return
  const blockId = cameraPendingBlockId
  const blob = await (await fetch(cameraState.capturedDataUrl)).blob()
  const file = new File([blob], `camera-photo-${mediaTimestamp()}.jpg`, { type: 'image/jpeg' })
  closeCamera()
  cameraPendingBlockId = ''
  await uploadMediaToBlock(blockId, file)
}

async function onCameraFallbackSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  const blockId = cameraPendingBlockId
  closeCamera()
  cameraPendingBlockId = ''
  if (file && blockId) {
    await uploadMediaToBlock(blockId, file)
  }
}

// ===== Live voice recorder =====

const recorderState = reactive({
  blockId: '',
  active: false,
  seconds: 0,
  error: ''
})
const recorderTimer = ref<number | null>(null)
let mediaRecorder: MediaRecorder | null = null
let recorderStream: MediaStream | null = null
let recorderChunks: Blob[] = []

const formatRecorderTime = computed(() => {
  const total = recorderState.seconds
  const mm = String(Math.floor(total / 60)).padStart(2, '0')
  const ss = String(total % 60).padStart(2, '0')
  return `${mm}:${ss}`
})

function mediaTimestamp(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
}

async function startRecording(blockId: string) {
  if (!props.uploadTargetId) {
    toast.error('Save the note before recording audio')
    return
  }
  try {
    recorderStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    recorderChunks = []
    const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
    const mimeType = candidates.find(t => typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported?.(t))
    mediaRecorder = mimeType ? new MediaRecorder(recorderStream, { mimeType }) : new MediaRecorder(recorderStream)
    mediaRecorder.ondataavailable = (e: BlobEvent) => {
      if (e.data.size > 0) recorderChunks.push(e.data)
    }
    mediaRecorder.onstop = async () => {
      recorderStream?.getTracks().forEach(t => t.stop())
      recorderStream = null
      const type = mediaRecorder?.mimeType || 'audio/webm'
      const ext = type.includes('ogg') ? 'ogg' : type.includes('mp4') ? 'm4a' : 'webm'
      const hadData = recorderChunks.length > 0
      const blob = new Blob(recorderChunks, { type })
      const file = new File([blob], `voice-note-${mediaTimestamp()}.${ext}`, { type })
      const targetBlockId = recorderState.blockId
      const recordedDuration = recorderState.seconds
      if (recorderTimer.value !== null) {
        clearInterval(recorderTimer.value)
        recorderTimer.value = null
      }
      recorderState.active = false
      recorderState.blockId = ''
      if (hadData && targetBlockId) {
        await uploadMediaToBlock(targetBlockId, file, recordedDuration)
      }
    }
    recorderState.blockId = blockId
    recorderState.active = true
    recorderState.seconds = 0
    recorderState.error = ''
    mediaRecorder.start()
    recorderTimer.value = window.setInterval(() => {
      recorderState.seconds++
    }, 1000)
  } catch {
    recorderState.error = 'Microphone unavailable. Upload an audio file instead.'
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
}

function cancelRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.onstop = null
    mediaRecorder.stop()
  }
  mediaRecorder = null
  recorderStream?.getTracks().forEach(t => t.stop())
  recorderStream = null
  recorderChunks = []
  if (recorderTimer.value !== null) {
    clearInterval(recorderTimer.value)
    recorderTimer.value = null
  }
  recorderState.active = false
  recorderState.blockId = ''
}

onMounted(() => {
  document.addEventListener('selectionchange', handleSelectionChange)
})

onUnmounted(() => {
  document.removeEventListener('selectionchange', handleSelectionChange)
})

onBeforeUnmount(() => {
  for (const url of blobUrls.values()) {
    URL.revokeObjectURL(url)
  }
  blobUrls.clear()
  cameraState.stream?.getTracks().forEach(t => t.stop())
  recorderStream?.getTracks().forEach(t => t.stop())
  if (recorderTimer.value !== null) {
    clearInterval(recorderTimer.value)
  }
})
</script>
