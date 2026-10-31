<template>
  <div v-if="isOpen && obligation" @click.self="emit('close')" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 font-sans overflow-hidden">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md shadow-2xl relative flex flex-col max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] overflow-hidden">
      <!-- Fixed Header -->
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
        <div>
          <div class="text-[10px] font-mono uppercase tracking-wider text-rose-400 mb-0.5">
            Subscription Lifecycle
          </div>
          <h3 class="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <span>ยุติรายการประจำ: {{ obligation.title }}</span>
          </h3>
        </div>
        <button
          @click="emit('close')"
          type="button"
          class="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleTerminate" class="flex flex-col flex-1 min-h-0 overflow-hidden">
        <div class="p-4 sm:p-5 space-y-4 overflow-y-auto overscroll-contain flex-1 min-h-0">
          <!-- Error message -->
          <div v-if="errorMessage" class="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {{ errorMessage }}
          </div>

          <!-- Termination Mode Selection -->
          <div class="space-y-2.5">
            <label class="block text-xs font-mono uppercase tracking-wider text-zinc-400">
              รูปแบบการยุติ <span class="text-rose-400">*</span>
            </label>

            <!-- Option 1: Immediate -->
            <label
              class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
              :class="mode === 'IMMEDIATE' ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-950 border-zinc-800/80 hover:bg-zinc-900/50'"
            >
              <input
                type="radio"
                name="terminate_mode"
                value="IMMEDIATE"
                v-model="mode"
                class="mt-0.5 text-zinc-100 focus:ring-0"
              />
              <div class="text-xs space-y-1">
                <span class="font-semibold text-zinc-200 block">ยุติทันที (Immediate)</span>
                <p class="text-zinc-400 text-[11px] leading-relaxed">
                  หยุดต่อรอบใหม่ทันที บิลรอบปัจจุบัน (ครบกำหนด {{ formatDate(obligation.due_date) }}) จะเป็นบิลสุดท้ายที่เปิดให้ชำระ
                </p>
              </div>
            </label>

            <!-- Option 2: Scheduled End Date -->
            <label
              class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
              :class="mode === 'SCHEDULED' ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-950 border-zinc-800/80 hover:bg-zinc-900/50'"
            >
              <input
                type="radio"
                name="terminate_mode"
                value="SCHEDULED"
                v-model="mode"
                class="mt-0.5 text-zinc-100 focus:ring-0"
              />
              <div class="text-xs space-y-1 flex-1">
                <span class="font-semibold text-zinc-200 block">กำหนดวันสิ้นสุด (Scheduled End Date)</span>
                <p class="text-zinc-400 text-[11px] leading-relaxed">
                  ต่อรอบและแจ้งเตือนตามปกติต่อเนื่อง จนกว่าจะพ้นวันสิ้นสุดที่กำหนด หลังจากนั้นจะหยุดต่อรอบโดยอัตโนมัติ
                </p>

                <div v-if="mode === 'SCHEDULED'" class="pt-2">
                  <label class="block text-[10px] font-mono text-zinc-400 mb-1">วันสิ้นสุดสัญญา / Service End Date</label>
                  <input
                    v-model="effectiveEndDate"
                    type="date"
                    required
                    :min="todayIso"
                    class="w-full bg-zinc-950 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-zinc-100 font-mono focus:border-zinc-500 outline-none"
                  />
                </div>
              </div>
            </label>
          </div>

          <!-- Consequences Checklist -->
          <div class="p-3.5 rounded-lg bg-zinc-900/60 border border-zinc-800 text-xs font-mono space-y-2">
            <span class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">ผลกระทบจากการยุติ</span>
            <ul class="space-y-1.5 text-[11px] text-zinc-300">
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 shrink-0">✓</span>
                <span>ประวัติการชำระเงินและสลิปหลักฐานทั้งหมดยังคงอยู่ ไม่ถูกลบ</span>
              </li>
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 shrink-0">✓</span>
                <span>บิลที่เกิดขึ้นแล้วยังคงเปิดให้กรอกยอดและชำระได้ตามปกติ</span>
              </li>
              <li class="flex items-start gap-2">
                <span class="text-rose-400 shrink-0">✕</span>
                <span>จะไม่มีการสร้างหรือต่อรอบบิลใหม่หลังจากวันสิ้นสุด</span>
              </li>
            </ul>
          </div>
        </div>

        <!-- Action Buttons (Sticky Footer) -->
        <div class="flex items-center justify-end gap-2.5 p-4 border-t border-zinc-800/80 shrink-0 bg-zinc-950/90">
          <button
            type="button"
            @click="emit('close')"
            class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-all active:scale-[0.98]"
          >
            ยกเลิก
          </button>
          <button
            type="submit"
            :disabled="isSubmitting || (mode === 'SCHEDULED' && !effectiveEndDate)"
            class="px-4 py-1.5 rounded-md bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            {{ isSubmitting ? 'กำลังบันทึก...' : 'ยืนยันยุติรายการประจำ' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useFinanceStore } from '../../stores/finance'
import { useToastStore } from '../../stores/toast'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import type { FinancialObligation } from '../../types/finance'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  obligation: FinancialObligation | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'terminated'): void
}>()

useBodyScrollLock(() => props.isOpen)

const financeStore = useFinanceStore()
const toast = useToastStore()

const mode = ref<'IMMEDIATE' | 'SCHEDULED'>('IMMEDIATE')
const effectiveEndDate = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

const todayIso = computed(() => {
  return new Date().toISOString().split('T')[0]
})

watch(() => props.isOpen, (open) => {
  if (open) {
    mode.value = 'IMMEDIATE'
    effectiveEndDate.value = ''
    errorMessage.value = ''
  }
})

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return dateStr
  }
}

async function handleTerminate() {
  if (!props.obligation) return
  if (mode.value === 'SCHEDULED' && !effectiveEndDate.value) {
    errorMessage.value = 'กรุณาระบุวันสิ้นสุด'
    return
  }

  isSubmitting.value = true
  errorMessage.value = ''
  try {
    await financeStore.terminateSubscription(props.obligation.id, {
      mode: mode.value,
      effective_end_date: mode.value === 'SCHEDULED' ? effectiveEndDate.value : undefined
    })
    toast.success('ยุติรายการประจำเรียบร้อยแล้ว')
    emit('terminated')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || err.message || 'Failed to terminate subscription'
  } finally {
    isSubmitting.value = false
  }
}
</script>
