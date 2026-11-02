<template>
  <div class="mt-4 border-t border-zinc-800 pt-4 space-y-3 text-xs">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div>
        <h3 class="font-semibold text-zinc-200">{{ tr('Drive files', 'ไฟล์บน Drive') }}</h3>
        <p class="mt-1 text-zinc-500">{{ tr('Review file usage and preview a destination before moving existing files.', 'ตรวจว่าไฟล์ใช้ที่ไหน และดูตำแหน่งปลายทางก่อนย้ายไฟล์เก่า') }}</p>
      </div>
      <button type="button" :disabled="loading || busy" @click="load(1)" class="rounded border border-zinc-700 px-3 py-2 text-zinc-300 disabled:opacity-50">
        {{ loading ? tr('Loading…', 'กำลังโหลด…') : tr('Review files', 'ตรวจรายการไฟล์') }}
      </button>
    </div>
    <p v-if="error" role="alert" class="text-rose-400">{{ error }}</p>
    <p v-if="loaded && !rows.length" class="py-3 text-zinc-500">{{ tr('No files on this page.', 'ไม่มีไฟล์ในหน้านี้') }}</p>
    <ul v-if="rows.length" class="divide-y divide-zinc-800 rounded border border-zinc-800">
      <li v-for="row in rows" :key="row.id" class="p-3 space-y-2">
        <div class="flex flex-wrap justify-between gap-2">
          <div class="min-w-0 flex-1">
            <p class="break-words font-medium text-zinc-200">{{ row.file_name }}</p>
            <p class="mt-1 break-words text-zinc-500">{{ row.folder_path.join(' / ') || tr('Legacy location — check in Drive', 'ตำแหน่งเดิม — ตรวจสอบบน Drive') }}</p>
          </div>
          <div class="flex flex-wrap items-start gap-2">
            <a v-if="row.web_view_link" :href="row.web_view_link" target="_blank" rel="noopener noreferrer" class="text-zinc-300 underline">{{ tr('Open', 'เปิดไฟล์') }}</a>
            <button type="button" :disabled="busy || loading" @click="inspect(row)" class="text-zinc-300 underline disabled:opacity-50">{{ busyId === row.id ? tr('Checking…', 'กำลังตรวจ…') : tr('Check & preview', 'ตรวจและดูตัวอย่าง') }}</button>
            <button v-if="row.unreferenced" type="button" :disabled="busy || loading" @click="askDelete(row)" class="text-rose-400 underline disabled:opacity-50">{{ tr('Delete file', 'ลบไฟล์') }}</button>
          </div>
        </div>
        <p v-if="row.pending_payment" class="text-amber-400">{{ tr('Uploaded for a payment that has not been linked yet. Check payment history before deleting.', 'อัปโหลดสำหรับการจ่ายที่ยังไม่ผูกประวัติ ตรวจประวัติการจ่ายก่อนลบ') }}</p>
        <p class="break-words text-zinc-400">
          {{ row.references.length ? tr('Used in: ', 'ใช้อยู่ใน: ') + row.references.map(r => r.name + (r.trashed ? tr(' (trash)', ' (ถังขยะ)') : '')).join(', ') : tr('No item currently references this file.', 'ไม่มีรายการอ้างอิงไฟล์นี้อยู่') }}
          <span v-if="row.shared" class="text-amber-400"> · {{ tr('Shared file', 'ไฟล์ใช้ร่วมกัน') }}</span>
        </p>
        <div v-if="previews[row.id]" class="space-y-2 rounded bg-zinc-950 p-3 text-zinc-400">
          <p>{{ stateLabel(previews[row.id]!.state) }}</p>
          <a v-if="previews[row.id]!.current_parents[0]" :href="`https://drive.google.com/drive/folders/${previews[row.id]!.current_parents[0]}`" target="_blank" rel="noopener noreferrer" class="underline">{{ tr('Open current folder', 'เปิดโฟลเดอร์ปัจจุบัน') }}</a>
          <p v-if="previews[row.id]!.destination.length" class="break-words">{{ tr('Destination: ', 'ปลายทาง: ') }}Personal Life OS / {{ previews[row.id]!.destination.join(' / ') }}</p>
          <button v-if="previews[row.id]!.state === 'move'" type="button" :disabled="busy" @click="askMove(row)" class="rounded bg-zinc-100 px-3 py-2 text-zinc-950 disabled:opacity-50">{{ tr('Move to this folder', 'ย้ายไปโฟลเดอร์นี้') }}</button>
        </div>
      </li>
    </ul>
    <div v-if="loaded && count" class="flex items-center justify-between text-zinc-400">
      <button type="button" :disabled="page <= 1 || loading || busy" @click="load(page - 1)" class="disabled:opacity-30">{{ tr('Previous', 'ก่อนหน้า') }}</button>
      <span>{{ page }} / {{ Math.ceil(count / 20) }} · {{ count }} {{ tr('files', 'ไฟล์') }}</span>
      <button type="button" :disabled="page * 20 >= count || loading || busy" @click="load(page + 1)" class="disabled:opacity-30">{{ tr('Next', 'ถัดไป') }}</button>
    </div>
    <ConfirmModal :is-open="!!action" :title="action?.kind === 'delete' ? tr('Delete Drive file', 'ลบไฟล์จาก Drive') : tr('Move Drive file', 'ย้ายไฟล์บน Drive')"
      :message="confirmation" :is-danger="action?.kind === 'delete'" :is-loading="busy" :error-message="actionError"
      :confirm-text="action?.kind === 'delete' ? tr('Delete permanently', 'ลบถาวร') : tr('Move file', 'ย้ายไฟล์')"
      :cancel-text="tr('Cancel', 'ยกเลิก')" @confirm="execute" @cancel="action = null" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import api from '../../api/client'
import { locale } from '../../i18n'
import { useToastStore } from '../../stores/toast'
import { deleteDriveFile, type DriveFileItem } from '../../api/storage'
import ConfirmModal from '../common/ConfirmModal.vue'

interface FileRow extends DriveFileItem {
  references: { name: string; kind: string; target_id: string; trashed?: boolean }[]
  shared: boolean
  unreferenced: boolean
  destination: string[]
}
interface Preview {
  state: string
  move_token: string
  current_parents: string[]
  destination: string[]
}
const tr = (en: string, th: string) => locale.value === 'th' ? th : en
const toast = useToastStore()
const rows = ref<FileRow[]>([]), count = ref(0), page = ref(1), loaded = ref(false)
const loading = ref(false), busy = ref(false), busyId = ref(''), error = ref(''), actionError = ref('')
const previews = ref<Record<string, Preview>>({})
const action = ref<{ kind: 'move' | 'delete'; row: FileRow; token?: string } | null>(null)
const confirmation = computed(() => !action.value ? '' : action.value.kind === 'delete'
  ? tr(`Permanently delete “${action.value.row.file_name}” from Google Drive?`, `ลบ “${action.value.row.file_name}” จาก Google Drive ถาวรหรือไม่?`)
  : tr(`Move “${action.value.row.file_name}” to Personal Life OS / ${previews.value[action.value.row.id]?.destination.join(' / ')}? Existing file links will be preserved.`, `ย้าย “${action.value.row.file_name}” ไปที่ Personal Life OS / ${previews.value[action.value.row.id]?.destination.join(' / ')} หรือไม่? ลิงก์ไฟล์เดิมยังใช้งานได้`))
const message = (e: any) => e.response?.data?.error || e.message || tr('Operation failed. Please retry.', 'ดำเนินการไม่สำเร็จ กรุณาลองอีกครั้ง')
function stateLabel(state: string) {
  return ({ current: tr('Already organized.', 'อยู่ในโครงสร้างใหม่แล้ว'), move: tr('Ready to organize. No file has been moved yet.', 'พร้อมจัดโฟลเดอร์ ยังไม่ได้ย้ายไฟล์'), missing: tr('File not found in this Google account.', 'ไม่พบไฟล์ในบัญชี Google นี้'), trashed: tr('File is in Drive trash.', 'ไฟล์อยู่ในถังขยะของ Drive'), unreferenced: tr('No destination can be inferred. Review before deleting.', 'ระบุปลายทางไม่ได้ กรุณาตรวจสอบก่อนลบ') } as Record<string, string>)[state] || state
}
async function load(nextPage: number) {
  loading.value = true; error.value = ''
  try {
    const { data } = await api.get('/storage/files/', { params: { page: nextPage } })
    rows.value = data.results; count.value = data.count; page.value = data.page; loaded.value = true; previews.value = {}
  } catch (e) { error.value = message(e) } finally { loading.value = false }
}
async function inspect(row: FileRow) {
  busy.value = true; busyId.value = row.id; error.value = ''
  delete previews.value[row.id]
  try { const { data } = await api.get(`/storage/files/${row.id}/organization/`); previews.value[row.id] = data }
  catch (e) { error.value = message(e) } finally { busy.value = false; busyId.value = '' }
}
function askDelete(row: FileRow) { actionError.value = ''; action.value = { kind: 'delete', row } }
function askMove(row: FileRow) { actionError.value = ''; action.value = { kind: 'move', row, token: previews.value[row.id]?.move_token } }
async function execute() {
  if (!action.value || busy.value) return
  busy.value = true; actionError.value = ''
  try {
    if (action.value.kind === 'delete') await deleteDriveFile(action.value.row.id)
    else await api.post(`/storage/files/${action.value.row.id}/organization/`, { move_token: action.value.token })
    toast.success(action.value.kind === 'delete' ? tr('File deleted', 'ลบไฟล์แล้ว') : tr('File moved', 'ย้ายไฟล์แล้ว'))
    action.value = null
    await load(count.value % 20 === 1 && page.value > 1 ? page.value - 1 : page.value)
  } catch (e) { actionError.value = message(e) } finally { busy.value = false }
}
</script>
