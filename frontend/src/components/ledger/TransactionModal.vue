<template>
  <div
    v-if="isOpen"
    @click.self="emit('close')"
    class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-hidden font-sans"
  >
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-xl max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col shadow-2xl overflow-hidden relative">
      <!-- Fixed Header -->
      <div class="shrink-0 px-4 sm:px-6 py-3.5 border-b border-zinc-800 flex items-center justify-between">
        <h3 class="text-base font-semibold text-zinc-100 tracking-tight flex items-center gap-2">
          <span>{{ isEdit ? 'Edit Transaction' : 'New Transaction' }}</span>
          <span v-if="isEdit && transactionToEdit" class="text-xs font-mono text-zinc-500 font-normal">
            #{{ transactionToEdit.id.slice(0, 8) }}
          </span>
        </h3>
        <button
          @click="emit('close')"
          type="button"
          class="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Form (Body & Sticky Footer) -->
      <form @submit.prevent="handleSubmit" class="flex flex-col flex-1 min-h-0 overflow-hidden text-xs font-mono">
        <div class="flex-1 overflow-y-auto overscroll-contain min-h-0 p-4 sm:p-6 space-y-4">
          <div v-if="errorMessage" class="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {{ errorMessage }}
          </div>

          <!-- 1. Type Switcher: Expense vs Income -->
          <div v-if="isTypeLocked" class="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/80 border border-zinc-800 text-xs font-mono">
            <span class="text-zinc-400">Transaction Type: <strong :class="form.transaction_type === 'INFLOW' ? 'text-emerald-400' : 'text-zinc-200'">{{ form.transaction_type === 'INFLOW' ? 'Income' : 'Expense' }}</strong></span>
            <span class="text-[10px] text-zinc-500">Locked after creation</span>
          </div>
          <div v-else class="flex items-center p-1 rounded-lg bg-zinc-900 border border-zinc-800">
            <button
              type="button"
              @click="form.transaction_type = 'OUTFLOW'"
              class="flex-1 py-1.5 rounded-md text-xs font-medium transition-all active:scale-[0.98] flex items-center justify-center gap-1.5 cursor-pointer"
              :class="form.transaction_type === 'OUTFLOW' ? 'bg-zinc-800 text-zinc-100 shadow-sm font-semibold' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'"
            >
              <ArrowUpRight class="w-3.5 h-3.5 text-zinc-400" />
              <span>Expense</span>
            </button>

            <button
              type="button"
              @click="form.transaction_type = 'INFLOW'"
              class="flex-1 py-1.5 rounded-md text-xs font-medium transition-all active:scale-[0.98] flex items-center justify-center gap-1.5 cursor-pointer"
              :class="form.transaction_type === 'INFLOW' ? 'bg-zinc-800 text-zinc-100 shadow-sm font-semibold' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'"
            >
              <ArrowDownLeft class="w-3.5 h-3.5 text-zinc-400" />
              <span>Income</span>
            </button>
          </div>

          <!-- 2. Account & Gross Amount -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Account / Wallet <span class="text-rose-400">*</span></label>
              <select
                v-model="form.account"
                required
                :disabled="isAccountLocked"
                class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono text-xs transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <option value="" disabled>Select account / wallet</option>
              <option
                v-for="acc in ledgerStore.accounts"
                :key="acc.id"
                :value="acc.id"
              >
                {{ acc.name }} (฿{{ Number(acc.current_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }})
              </option>
            </select>
            <span v-if="isAccountLocked" class="text-[10px] text-zinc-500 font-mono block mt-0.5">
              Account locked after creation
            </span>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="text-[11px] text-zinc-300 font-medium">Gross Amount (฿) <span class="text-rose-400">*</span></label>
              <span v-if="isSplit && splitMode === 'ITEMIZED'" class="text-[10px] text-zinc-500 font-mono">
                Auto-calculated
              </span>
            </div>
            <div class="relative">
              <span class="absolute left-3 top-2 text-zinc-500">฿</span>
              <input
                v-model.number="form.gross_amount"
                type="number"
                step="0.01"
                min="0.01"
                required
                :disabled="(isSplit && splitMode === 'ITEMIZED') || isAmountLocked"
                placeholder="0.00"
                class="w-full pl-7 pr-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono font-semibold transition-colors disabled:opacity-75 disabled:cursor-not-allowed"
              />
            </div>
            <span v-if="isAmountLocked" class="text-[9px] text-amber-500/90 font-mono block mt-1 leading-tight">
              {{ amountLockReason }}
            </span>
          </div>
        </div>

        <!-- 3. Title & Date -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Description / Payee <span class="text-rose-400">*</span></label>
            <input
              v-model="form.title"
              type="text"
              required
              placeholder="e.g. Haidilao Shabu, Cafe, Grocery"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 transition-colors"
            />
          </div>

          <div>
            <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Date</label>
            <input
              v-model="form.transaction_date"
              type="date"
              required
              :disabled="isDateLocked"
              :class="[
                'w-full px-3 py-2 rounded-md border font-mono transition-colors text-xs',
                isDateLocked
                  ? 'bg-zinc-950/60 border-zinc-800 text-zinc-500 cursor-not-allowed'
                  : 'bg-zinc-900 border-zinc-800 text-zinc-100 hover:border-zinc-700 focus:outline-none focus:border-zinc-500'
              ]"
            />
            <span v-if="isDateLocked" class="text-[9px] text-amber-500/90 font-mono block mt-1">
              Transfer date is locked to keep both accounts in sync
            </span>
          </div>
        </div>

        <!-- 4. Category Selector -->
        <div>
          <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Category</label>
          <select
            v-model="form.category"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono text-xs transition-colors"
          >
            <option :value="null">-- General / Uncategorized --</option>
            <optgroup
              v-for="cat in filteredCategories"
              :key="cat.id"
              :label="cat.name"
            >
              <option :value="cat.id">{{ cat.name }}</option>
              <option
                v-for="sub in cat.subcategories"
                :key="sub.id"
                :value="sub.id"
              >
                &nbsp;&nbsp;↳ {{ sub.name }}
              </option>
            </optgroup>
          </select>
        </div>

        <!-- 5. SMART BILL-SPLITTING PANEL (Expense Only, Create Mode Only) -->
        <div v-if="!isEdit && form.transaction_type === 'OUTFLOW'" class="pt-1">
          <div class="flex items-center justify-between pb-2 border-b border-zinc-800/80">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input
                v-model="isSplit"
                type="checkbox"
                class="rounded bg-zinc-900 border-zinc-700 text-zinc-100 accent-zinc-500 w-3.5 h-3.5 cursor-pointer"
              />
              <span class="text-zinc-200 text-xs font-semibold flex items-center gap-1.5">
                <Users class="w-3.5 h-3.5 text-zinc-400" />
                <span>Split Bill (Harntung Mode)</span>
              </span>
            </label>

            <span v-if="isSplit" class="text-[11px] text-zinc-400 font-mono">
              {{ splitMode === 'ITEMIZED' && harntungPayerName ? `${harntungPayerName}'s Share:` : 'My Net Share:' }} <strong class="text-emerald-400 font-semibold">฿{{ calculatedNetExpense.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</strong>
            </span>
          </div>

          <!-- Expanded Split Configuration -->
          <div v-if="isSplit" class="mt-3 p-3.5 rounded-lg bg-zinc-900/60 border border-zinc-800 space-y-3">
            <!-- Mode Switcher: Harntung Itemized vs Equal vs Custom -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div class="flex items-center gap-1 p-0.5 bg-zinc-950 border border-zinc-800 rounded-md text-[11px]">
                <button
                  type="button"
                  @click="splitMode = 'ITEMIZED'"
                  class="px-2.5 py-1 rounded transition-colors cursor-pointer"
                  :class="splitMode === 'ITEMIZED' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
                >
                  Harntung (Itemized)
                </button>
                <button
                  type="button"
                  @click="splitMode = 'EQUAL'"
                  class="px-2.5 py-1 rounded transition-colors cursor-pointer"
                  :class="splitMode === 'EQUAL' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
                >
                  Equal Split
                </button>
                <button
                  type="button"
                  @click="splitMode = 'CUSTOM'"
                  class="px-2.5 py-1 rounded transition-colors cursor-pointer"
                  :class="splitMode === 'CUSTOM' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
                >
                  Custom Amount
                </button>
              </div>

              <!-- Equal split people counter -->
              <div v-if="splitMode === 'EQUAL'" class="flex items-center gap-1.5 text-[11px] text-zinc-400">
                <span>Total People (incl. me):</span>
                <input
                  v-model.number="equalSplitPeopleCount"
                  type="number"
                  min="2"
                  max="50"
                  placeholder="2"
                  class="w-12 px-1.5 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-center text-zinc-100 font-mono outline-none"
                  @input="handlePeopleCountInput"
                />
              </div>
            </div>

            <!-- ================= HARNTUNG ITEMIZED MODE ================= -->
            <div v-if="splitMode === 'ITEMIZED'" class="space-y-3 pt-1">
              <!-- Participants Bar -->
              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <label class="text-[11px] font-mono text-zinc-400 font-semibold uppercase">
                    Participants ({{ harntungParticipants.length }})
                  </label>
                  <div class="flex items-center gap-2">
                    <div v-if="harntungParticipants.length > 0" class="flex items-center gap-1.5 text-[11px] font-mono">
                      <span class="text-zinc-400">Payer:</span>
                      <select
                        v-model="harntungPayerName"
                        class="bg-zinc-950 border border-zinc-800 rounded px-1.5 py-0.5 text-xs text-zinc-200 outline-none focus:border-zinc-700 cursor-pointer"
                      >
                        <option value="" disabled>Select payer</option>
                        <option
                          v-for="p in harntungParticipants"
                          :key="p.name"
                          :value="p.name"
                          :disabled="!p.name"
                        >
                          {{ p.name || '(Enter name first)' }}
                        </option>
                      </select>
                    </div>
                    <button
                      type="button"
                      @click="addHarntungParticipant"
                      class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1 cursor-pointer"
                    >
                      <Plus class="w-3 h-3" />
                      <span>Add Friend</span>
                    </button>
                  </div>
                </div>

                <div class="flex flex-wrap items-center gap-2">
                  <div
                    v-for="(p, pIdx) in harntungParticipants"
                    :key="pIdx"
                    class="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-950 border text-xs transition-colors max-w-full flex-wrap sm:flex-nowrap"
                    :class="harntungPayerName && harntungPayerName === p.name ? 'border-emerald-500/50 bg-emerald-950/20' : 'border-zinc-800'"
                  >
                    <input
                      v-model="p.name"
                      type="text"
                      placeholder="Name"
                      class="bg-transparent text-zinc-100 text-xs outline-none min-w-[60px] flex-1 sm:w-20 sm:flex-none"
                    />
                    <input
                      v-model="p.contact"
                      type="text"
                      placeholder="PromptPay"
                      class="bg-transparent text-zinc-500 text-[10px] outline-none min-w-[60px] flex-1 sm:w-20 sm:flex-none font-mono"
                    />
                    <div class="flex items-center gap-1 shrink-0 ml-auto">
                      <button
                        type="button"
                        @click="harntungPayerName = p.name"
                        :disabled="!p.name"
                        class="px-1.5 py-0.5 rounded text-[10px] font-mono transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                        :class="harntungPayerName && harntungPayerName === p.name ? 'bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-zinc-200 border border-zinc-800'"
                        :title="harntungPayerName && harntungPayerName === p.name ? 'Current payer' : 'Set as payer'"
                      >
                        {{ harntungPayerName && harntungPayerName === p.name ? 'Payer' : 'Set Payer' }}
                      </button>
                      <button
                        type="button"
                        @click="removeHarntungParticipant(pIdx)"
                        class="text-zinc-500 hover:text-rose-400 transition-colors ml-0.5 cursor-pointer shrink-0"
                      >
                        <Trash2 class="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Dishes / Items Breakdown -->
              <div class="space-y-2 pt-2 border-t border-zinc-800/60">
                <div class="flex items-center justify-between">
                  <label class="text-[11px] font-mono text-zinc-400 font-semibold uppercase">
                    Dishes & Receipt Items ({{ harntungItems.length }})
                  </label>
                  <button
                    type="button"
                    @click="addHarntungItem"
                    class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1 cursor-pointer"
                  >
                    <Plus class="w-3 h-3" />
                    <span>+ Add Dish</span>
                  </button>
                </div>

                <div class="space-y-2">
                  <div
                    v-for="(item, itemIdx) in harntungItems"
                    :key="itemIdx"
                    class="p-2.5 rounded bg-zinc-950/70 border border-zinc-800/80 space-y-2"
                  >
                    <div class="flex flex-col sm:flex-row sm:items-center gap-2">
                      <input
                        v-model="item.name"
                        type="text"
                        placeholder="Dish / Item Name"
                        class="w-full sm:flex-1 min-w-0 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 outline-none"
                      />
                      <div class="flex items-center gap-2 w-full sm:w-auto shrink-0">
                        <div class="relative flex-1 sm:w-28 min-w-0">
                          <span class="absolute left-2 top-1 text-zinc-500 text-xs">฿</span>
                          <input
                            v-model.number="item.price"
                            type="number"
                            step="0.01"
                            min="0"
                            placeholder="0.00"
                            class="w-full pl-5 pr-2 py-1 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 text-right font-mono outline-none"
                          />
                        </div>
                        <div class="flex items-center gap-1 text-[11px] text-zinc-500 shrink-0">
                          <span>x</span>
                          <input
                            v-model.number="item.quantity"
                            type="number"
                            min="1"
                            class="w-10 px-1 py-1 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 text-center font-mono outline-none"
                          />
                        </div>
                        <button
                          type="button"
                          @click="removeHarntungItem(itemIdx)"
                          class="p-1 text-zinc-500 hover:text-rose-400 transition-colors cursor-pointer shrink-0 ml-auto sm:ml-0"
                          title="Remove dish"
                        >
                          <Trash2 class="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <!-- Who Ate This? (Consumers Chips) -->
                    <div class="flex flex-wrap items-center gap-1.5 pt-1 text-[11px]">
                      <span class="text-zinc-500 text-[10px] mr-1 shrink-0">Consumers:</span>
                      <button
                        type="button"
                        @click="toggleAllConsumers(item)"
                        class="px-1.5 py-0.5 rounded text-[10px] font-mono border transition-colors cursor-pointer shrink-0"
                        :class="item.consumers.length === harntungParticipants.length ? 'bg-zinc-800 text-zinc-200 border-zinc-600' : 'text-zinc-500 border-zinc-800 hover:text-zinc-300'"
                      >
                        [All]
                      </button>
                      <button
                        v-for="p in harntungParticipants"
                        :key="p.name"
                        type="button"
                        @click="toggleConsumer(item, p.name)"
                        class="px-2 py-0.5 rounded text-[10px] font-mono border transition-colors cursor-pointer max-w-full truncate"
                        :class="item.consumers.includes(p.name) ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-semibold' : 'text-zinc-600 border-zinc-800/80 hover:text-zinc-400'"
                      >
                        {{ p.name }}
                      </button>

                      <span v-if="item.consumers.length > 0 && item.price > 0" class="text-[10px] text-zinc-500 font-mono w-full sm:w-auto sm:ml-auto pt-0.5 sm:pt-0">
                        ≈ ฿{{ (Number(item.price * (item.quantity || 1)) / item.consumers.length).toFixed(2) }} each
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Taxes & Service Charge Controls -->
              <div class="pt-2 border-t border-zinc-800/60 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
                <div class="flex items-center gap-3">
                  <!-- Service Charge Toggle -->
                  <div class="flex items-center gap-1.5">
                    <button
                      type="button"
                      @click="serviceChargePct = serviceChargePct === 10 ? 0 : 10"
                      class="px-2 py-1 rounded border text-[11px] transition-colors cursor-pointer"
                      :class="serviceChargePct > 0 ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-semibold' : 'text-zinc-500 border-zinc-800 hover:text-zinc-300'"
                    >
                      Service Charge +{{ serviceChargePct }}%
                    </button>
                  </div>

                  <!-- VAT Toggle -->
                  <div class="flex items-center gap-1.5">
                    <button
                      type="button"
                      @click="vatPct = vatPct === 7 ? 0 : 7"
                      class="px-2 py-1 rounded border text-[11px] transition-colors cursor-pointer"
                      :class="vatPct > 0 ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-semibold' : 'text-zinc-500 border-zinc-800 hover:text-zinc-300'"
                    >
                      VAT +{{ vatPct }}%
                    </button>
                  </div>
                </div>

                <div class="text-right text-zinc-400 text-[11px]">
                  <span>Subtotal: ฿{{ harntungSubtotal.toFixed(2) }}</span>
                </div>
              </div>

              <!-- Harntung Live Per-Person Shares Summary -->
              <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800 space-y-2">
                <div class="flex items-center justify-between text-xs font-semibold text-zinc-200">
                  <span>Calculated Shares Breakdown</span>
                  <button
                    type="button"
                    @click="copySettlementSummary"
                    class="text-[11px] font-mono text-zinc-400 hover:text-zinc-100 flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <Copy class="w-3 h-3" />
                    <span>{{ copySuccess ? 'Copied summary!' : 'Copy Summary for LINE' }}</span>
                  </button>
                </div>

                <div class="space-y-1 pt-1 divide-y divide-zinc-800/40 text-xs font-mono">
                  <div
                    v-for="(share, sIdx) in harntungCalculatedShares"
                    :key="sIdx"
                    class="pt-1 flex items-center justify-between"
                  >
                    <div class="flex items-center gap-1.5">
                      <span :class="harntungPayerName && share.name === harntungPayerName ? 'text-emerald-400 font-bold' : 'text-zinc-300'">
                        {{ harntungPayerName && share.name === harntungPayerName ? `${share.name} (Payer's Expense)` : share.name }}
                      </span>
                      <span class="text-[10px] text-zinc-500">({{ share.itemsCount }} items)</span>
                    </div>
                    <span :class="harntungPayerName && share.name === harntungPayerName ? 'text-emerald-400 font-semibold' : 'text-zinc-200'">
                      ฿{{ share.finalShare.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- ================= EQUAL / CUSTOM SPLIT MODE ================= -->
            <div v-else class="space-y-2">
              <div
                v-for="(p, idx) in participants"
                :key="idx"
                class="flex flex-col sm:flex-row sm:items-center gap-2 p-2 sm:p-0 rounded bg-zinc-950/40 sm:bg-transparent border sm:border-0 border-zinc-800/80"
              >
                <input
                  v-model="p.counterparty_name"
                  type="text"
                  placeholder="Friend's name"
                  class="flex-1 px-2.5 py-1.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-600 text-xs font-mono outline-none hover:border-zinc-700 focus:border-zinc-500 min-w-0 transition-colors"
                />
                <div class="flex items-center gap-2 w-full sm:w-auto">
                  <input
                    v-model="p.counterparty_contact"
                    type="text"
                    placeholder="Phone / PromptPay"
                    class="flex-1 sm:w-36 px-2 py-1.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-300 placeholder-zinc-600 text-[11px] font-mono outline-none hover:border-zinc-700 focus:border-zinc-500 transition-colors min-w-0"
                  />
                  <div class="relative w-28 sm:w-32 shrink-0">
                    <span class="absolute left-2 top-1.5 text-zinc-500 text-[11px]">฿</span>
                    <input
                      v-model.number="p.amount"
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      :disabled="splitMode === 'EQUAL'"
                      class="w-full pl-5 pr-2 py-1.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-100 text-xs font-mono text-right outline-none disabled:opacity-70 hover:border-zinc-700 focus:border-zinc-500 transition-colors"
                    />
                  </div>
                  <button
                    type="button"
                    @click="removeParticipant(idx)"
                    class="p-1 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors shrink-0 cursor-pointer"
                    title="Remove"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div class="flex items-center justify-between pt-1 flex-wrap gap-2">
                <button
                  type="button"
                  @click="addParticipant"
                  class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition-colors hover:underline cursor-pointer"
                >
                  <Plus class="w-3 h-3" />
                  <span>+ Add Person</span>
                </button>

                <button
                  type="button"
                  @click="copySettlementSummary"
                  class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition-colors hover:underline cursor-pointer"
                >
                  <Copy class="w-3 h-3" />
                  <span>{{ copySuccess ? 'Copied summary!' : 'Copy Summary' }}</span>
                </button>
              </div>
            </div>

            <!-- Auto Create Radar Debtors Checkbox -->
            <div class="pt-2 border-t border-zinc-800/60">
              <label class="flex items-center gap-2 cursor-pointer select-none">
                <input
                  v-model="autoCreateRadarDebtors"
                  type="checkbox"
                  class="rounded bg-zinc-900 border-zinc-700 text-zinc-100 accent-zinc-500 w-3.5 h-3.5 cursor-pointer"
                />
                <span class="text-zinc-300 text-[11px]">
                  Auto-create debtor records in Financial Radar
                </span>
              </label>
            </div>
          </div>
        </div>

        <!-- Split Bill Info Notice (In Edit Mode) -->
        <div v-if="isEdit && transactionToEdit?.is_split" class="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800 text-xs font-mono text-zinc-400 space-y-1">
          <div class="flex items-center gap-1.5 text-zinc-300 font-semibold">
            <Users class="w-3.5 h-3.5 text-zinc-400" />
            <span>Split Bill Transaction</span>
          </div>
          <p class="text-[11px] text-zinc-500">
            This transaction contains split allocations. Split participant shares and debtor records cannot be modified directly from this modal.
          </p>
        </div>

        <!-- Receipt / Slip Attachment (Create Mode Only) -->
        <div v-if="!isEdit">
          <div class="flex items-center justify-between mb-1">
            <label class="block text-[11px] text-zinc-300 font-medium">Receipt / Slip Attachment</label>
            <span v-if="storageStore.isConnected" class="text-[10px] text-zinc-500 font-mono">
              Direct GDrive Cloud
            </span>
          </div>

          <!-- When Google Drive is NOT connected -->
          <div
            v-if="!storageStore.isConnected"
            class="p-2.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs flex items-center justify-between gap-2"
          >
            <div class="flex items-center gap-2 text-zinc-400 text-[11px]">
              <HardDrive class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
              <span>Connect Google Drive in Settings to attach slips</span>
            </div>
            <router-link
              to="/settings"
              class="text-[10px] text-zinc-200 hover:underline font-mono shrink-0 font-medium"
            >
              Settings &rarr;
            </router-link>
          </div>

          <!-- When Google Drive IS connected -->
          <div v-else class="space-y-1.5">
            <div class="flex items-center gap-2">
              <label class="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-zinc-900 border border-dashed border-zinc-700 hover:border-zinc-500 cursor-pointer text-xs text-zinc-400 hover:text-zinc-200 transition-colors">
                <Upload class="w-3.5 h-3.5 text-zinc-400" />
                <span class="truncate">{{ selectedFile ? selectedFile.name : 'Select receipt / slip (JPG, PNG, PDF)' }}</span>
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  class="hidden"
                  @change="handleFileChange"
                />
              </label>
              <button
                v-if="selectedFile"
                type="button"
                @click="selectedFile = null"
                class="p-2 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
                title="Remove file"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
            <div v-if="storageStore.uploadProgress !== null" class="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
              <div
                class="bg-zinc-200 h-1 transition-all duration-150"
                :style="{ width: `${storageStore.uploadProgress}%` }"
              ></div>
            </div>
          </div>
        </div>

        <!-- Notes -->
        <div>
          <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Notes (Optional)</label>
          <input
            v-model="form.notes"
            type="text"
            placeholder=""
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 transition-colors"
          />
        </div>
        </div>

        <!-- Form Actions (Sticky Footer) -->
        <div class="shrink-0 p-4 border-t border-zinc-800/80 bg-zinc-950/90 flex items-center justify-end gap-2.5">
          <button
            type="button"
            @click="emit('close')"
            class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-sans text-zinc-300 transition-all active:scale-[0.98] cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting || !form.gross_amount || !form.title || isOverAllocated"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-sans font-semibold transition-all active:scale-[0.98] disabled:opacity-50 shadow-sm cursor-pointer"
          >
            {{ isSubmitting ? 'Saving...' : (isEdit ? 'Save Changes' : 'Record Transaction') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onUnmounted } from 'vue'
import { useLedgerStore } from '../../stores/ledger'
import { useStorageStore } from '../../stores/storage'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import type { TransactionType, LedgerTransaction } from '../../types/ledger'
import {
  X,
  ArrowUpRight,
  ArrowDownLeft,
  Users,
  Plus,
  Trash2,
  Copy,
  Upload,
  HardDrive
} from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  transactionToEdit?: LedgerTransaction | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created'): void
  (e: 'updated'): void
}>()

useBodyScrollLock(() => props.isOpen)

const ledgerStore = useLedgerStore()
const storageStore = useStorageStore()
const isSubmitting = ref(false)
const errorMessage = ref('')
const copySuccess = ref(false)
const selectedFile = ref<File | null>(null)

const isEdit = computed(() => !!props.transactionToEdit)
const isAccountLocked = computed(() => isEdit.value)
const isTypeLocked = computed(() => isEdit.value)

const isTransfer = computed(() => {
  if (!props.transactionToEdit) return false
  const tx = props.transactionToEdit as any
  return !!(tx.transfer_destination || tx.transfer_peer)
})

const isDateLocked = computed(() => {
  return isTransfer.value
})

const isAmountLocked = computed(() => {
  if (!props.transactionToEdit) return false
  const tx = props.transactionToEdit as any
  if (typeof tx.is_amount_locked === 'boolean') return tx.is_amount_locked
  if (tx.transfer_destination || tx.transfer_peer) return true
  if (tx.obligation || tx.payment_history) return true
  if (tx.settled_splits?.length || tx.settlement_transaction) return true
  if (tx.is_split || (tx.splits && tx.splits.length > 0)) return true
  return false
})

const amountLockReason = computed(() => {
  if (!props.transactionToEdit) return ''
  const tx = props.transactionToEdit as any
  if (tx.amount_lock_reason) return tx.amount_lock_reason
  if (tx.transfer_destination || tx.transfer_peer) {
    return 'Transfer amounts cannot be edited directly. Delete transfer and record anew.'
  }
  if (tx.obligation || tx.payment_history) {
    return 'Amount linked to an obligation payment is locked to maintain dossier balance.'
  }
  if (tx.settled_splits?.length || tx.settlement_transaction) {
    return 'Amount linked to a settled split payment is locked.'
  }
  if (tx.is_split || (tx.splits && tx.splits.length > 0)) {
    return 'Split bill amount is locked to maintain split allocation shares.'
  }
  return ''
})

const isSplit = ref(false)
const splitMode = ref<'ITEMIZED' | 'EQUAL' | 'CUSTOM'>('ITEMIZED')
const equalSplitPeopleCount = ref<number | null>(null)
const autoCreateRadarDebtors = ref(true)

// ============= Harntung Itemized State =============
const serviceChargePct = ref(0)
const vatPct = ref(0)

interface HarntungParticipant {
  name: string
  contact: string
}

interface HarntungItem {
  name: string
  price: number
  quantity: number
  consumers: string[]
}

const harntungParticipants = ref<HarntungParticipant[]>([])
const harntungPayerName = ref<string>('')

const harntungItems = ref<HarntungItem[]>([])

// ============= Classic Quick Split State =============
interface ParticipantRow {
  counterparty_name: string
  counterparty_contact: string
  amount: number
}

const participants = ref<ParticipantRow[]>([])

const form = reactive({
  account: '',
  transaction_type: 'OUTFLOW' as TransactionType,
  category: null as string | null,
  gross_amount: null as any,
  title: '',
  notes: '',
  transaction_date: ''
})

const filteredCategories = computed(() => {
  const targetType = form.transaction_type === 'INFLOW' ? 'INCOME' : 'EXPENSE'
  return ledgerStore.categories.filter((c) => c.category_type === targetType)
})

// ============= Harntung Calculations =============
const harntungSubtotal = computed(() => {
  return harntungItems.value.reduce((sum, item) => sum + (Number(item.price || 0) * Number(item.quantity || 1)), 0)
})

const harntungMultiplier = computed(() => {
  const sc = 1 + (Number(serviceChargePct.value || 0) / 100)
  const vat = 1 + (Number(vatPct.value || 0) / 100)
  return sc * vat
})

const harntungGrossTotal = computed(() => {
  return Number((harntungSubtotal.value * harntungMultiplier.value).toFixed(2))
})

const harntungCalculatedShares = computed(() => {
  const rawMap: Record<string, { raw: number; count: number }> = {}
  harntungParticipants.value.forEach(p => {
    rawMap[p.name] = { raw: 0, count: 0 }
  })

  harntungItems.value.forEach(item => {
    const itemTotal = Number(item.price || 0) * Number(item.quantity || 1)
    const consumers = item.consumers.length > 0 ? item.consumers : harntungParticipants.value.map(p => p.name)
    const perPerson = itemTotal / consumers.length
    consumers.forEach(name => {
      if (!rawMap[name]) rawMap[name] = { raw: 0, count: 0 }
      rawMap[name].raw += perPerson
      rawMap[name].count += 1
    })
  })

  return harntungParticipants.value.map(p => {
    const raw = rawMap[p.name]?.raw || 0
    const final = Number((raw * harntungMultiplier.value).toFixed(2))
    return {
      name: p.name,
      contact: p.contact,
      rawShare: raw,
      finalShare: final,
      itemsCount: rawMap[p.name]?.count || 0
    }
  })
})

const harntungPayerShare = computed(() => {
  if (!harntungPayerName.value) return 0
  const payer = harntungCalculatedShares.value.find(s => s.name === harntungPayerName.value)
  return payer ? payer.finalShare : 0
})

// Auto-sync gross amount when in Harntung mode
watch(
  () => [harntungGrossTotal.value, isSplit.value, splitMode.value],
  () => {
    if (isSplit.value && splitMode.value === 'ITEMIZED') {
      form.gross_amount = harntungGrossTotal.value
    }
  },
  { immediate: true }
)

const friendsTotalShare = computed(() => {
  if (splitMode.value === 'ITEMIZED') {
    return harntungCalculatedShares.value
      .filter(s => !harntungPayerName.value || s.name !== harntungPayerName.value)
      .reduce((sum, s) => sum + s.finalShare, 0)
  }
  return participants.value.reduce((sum, p) => sum + Number(p.amount || 0), 0)
})

const isOverAllocated = computed(() => {
  if (!isSplit.value || splitMode.value !== 'CUSTOM') return false
  return friendsTotalShare.value > Number(form.gross_amount)
})

const calculatedNetExpense = computed(() => {
  if (!isSplit.value) return form.gross_amount
  if (splitMode.value === 'ITEMIZED') return harntungPayerShare.value
  return Math.max(0, Number(form.gross_amount) - friendsTotalShare.value)
})

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.isOpen) {
    emit('close')
  }
}

watch(
  () => [props.isOpen, props.transactionToEdit] as const,
  ([open, txToEdit]) => {
    if (open) {
      window.addEventListener('keydown', handleKeyDown)
      errorMessage.value = ''
      if (ledgerStore.categories.length === 0) {
        ledgerStore.fetchCategories().catch(() => {})
      }
      if (txToEdit) {
        form.account = txToEdit.account
        form.title = txToEdit.title
        form.gross_amount = Number(txToEdit.gross_amount)
        form.notes = txToEdit.notes || ''
        form.category = txToEdit.category || null
        form.transaction_type = txToEdit.transaction_type
        form.transaction_date = txToEdit.transaction_date
        isSplit.value = false
        selectedFile.value = null
      } else {
        form.account = ''
        form.title = ''
        form.gross_amount = null as any
        form.notes = ''
        form.category = null
        form.transaction_type = 'OUTFLOW'
        form.transaction_date = ''
        isSplit.value = false
        splitMode.value = 'ITEMIZED'
        equalSplitPeopleCount.value = null
        harntungParticipants.value = []
        harntungPayerName.value = ''
        harntungItems.value = []
        participants.value = []
        serviceChargePct.value = 0
        vatPct.value = 0
        selectedFile.value = null
        storageStore.fetchStatus().catch(() => {})
      }
    } else {
      window.removeEventListener('keydown', handleKeyDown)
    }
  },
  { immediate: true }
)

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    selectedFile.value = target.files[0]
  }
}

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

watch(
  () => [form.gross_amount, equalSplitPeopleCount.value, splitMode.value, isSplit.value],
  () => {
    if (isSplit.value && splitMode.value === 'EQUAL') {
      recalculateEqualSplits()
    }
  }
)

function recalculateEqualSplits() {
  if (!equalSplitPeopleCount.value || equalSplitPeopleCount.value <= 1) return
  const count = equalSplitPeopleCount.value
  const perPerson = Number((Number(form.gross_amount || 0) / count).toFixed(2))
  participants.value.forEach((p) => {
    p.amount = perPerson
  })
}

function handlePeopleCountInput() {
  if (!equalSplitPeopleCount.value || equalSplitPeopleCount.value <= 1) {
    participants.value = []
    return
  }
  const targetFriends = equalSplitPeopleCount.value - 1
  while (participants.value.length < targetFriends) {
    participants.value.push({
      counterparty_name: '',
      counterparty_contact: '',
      amount: 0
    })
  }
  while (participants.value.length > targetFriends) {
    participants.value.pop()
  }
  recalculateEqualSplits()
}

function addParticipant() {
  participants.value.push({
    counterparty_name: '',
    counterparty_contact: '',
    amount: splitMode.value === 'EQUAL' && form.gross_amount && equalSplitPeopleCount.value
      ? Number((Number(form.gross_amount) / (equalSplitPeopleCount.value)).toFixed(2))
      : 0
  })
  if (splitMode.value === 'EQUAL') {
    equalSplitPeopleCount.value = participants.value.length + 1
    recalculateEqualSplits()
  }
}

function removeParticipant(idx: number) {
  participants.value.splice(idx, 1)
  if (splitMode.value === 'EQUAL') {
    equalSplitPeopleCount.value = Math.max(2, participants.value.length + 1)
    recalculateEqualSplits()
  }
}

// ============= Harntung Participant & Dish Helpers =============
function addHarntungParticipant() {
  harntungParticipants.value.push({
    name: '',
    contact: ''
  })
}

function removeHarntungParticipant(idx: number) {
  const removedName = harntungParticipants.value[idx].name
  if (harntungPayerName.value === removedName) {
    harntungPayerName.value = ''
  }
  harntungParticipants.value.splice(idx, 1)
  harntungItems.value.forEach(item => {
    item.consumers = item.consumers.filter(c => c !== removedName)
  })
}

function addHarntungItem() {
  harntungItems.value.push({
    name: '',
    price: 0,
    quantity: 1,
    consumers: harntungParticipants.value.map(p => p.name).filter(Boolean)
  })
}

function removeHarntungItem(idx: number) {
  harntungItems.value.splice(idx, 1)
}

function toggleConsumer(item: HarntungItem, name: string) {
  const index = item.consumers.indexOf(name)
  if (index > -1) {
    item.consumers.splice(index, 1)
  } else {
    item.consumers.push(name)
  }
}

function toggleAllConsumers(item: HarntungItem) {
  if (item.consumers.length === harntungParticipants.value.length) {
    item.consumers = []
  } else {
    item.consumers = harntungParticipants.value.map(p => p.name).filter(Boolean)
  }
}

function copySettlementSummary() {
  let text = ''
  if (splitMode.value === 'ITEMIZED') {
    text = `Receipt: ${form.title || 'Shared Bill'} (Total: ฿${harntungGrossTotal.value.toLocaleString('en-US', { minimumFractionDigits: 2 })})\n`
    if (serviceChargePct.value > 0 || vatPct.value > 0) {
      text += `Charges: SC +${serviceChargePct.value}% | VAT +${vatPct.value}%\n`
    }
    text += `--------------------------------\n`
    harntungCalculatedShares.value.forEach(s => {
      const contactInfo = s.contact ? ` (${s.contact})` : ''
      const isPayer = harntungPayerName.value && s.name === harntungPayerName.value
      text += `• ${s.name}${isPayer ? ' (Payer)' : ''}${contactInfo}: ฿${s.finalShare.toLocaleString('en-US', { minimumFractionDigits: 2 })}\n`
    })
    text += `--------------------------------\n`
    text += `${harntungPayerName.value ? `${harntungPayerName.value}'s` : 'Payer'} Net Share: ฿${harntungPayerShare.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
  } else {
    text = `Bill: ${form.title || 'Shared Expense'} (฿${Number(form.gross_amount).toLocaleString('en-US')})\n` +
      participants.value.map((p) => `• ${p.counterparty_name}: ฿${Number(p.amount).toLocaleString('en-US')}`).join('\n') +
      `\nMy Net Share: ฿${Number(calculatedNetExpense.value).toLocaleString('en-US')}`
  }

  navigator.clipboard.writeText(text)
  copySuccess.value = true
  setTimeout(() => {
    copySuccess.value = false
  }, 2500)
}

async function handleSubmit() {
  if (isSubmitting.value) return
  if (isOverAllocated.value) return
  if (!form.account) {
    errorMessage.value = 'Please select an account'
    return
  }
  if (!form.transaction_date) {
    errorMessage.value = 'Please select a transaction date'
    return
  }
  if (!form.gross_amount || Number(form.gross_amount) <= 0) {
    errorMessage.value = 'Gross amount must be greater than 0'
    return
  }
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    if (isEdit.value && props.transactionToEdit) {
      const updatePayload: any = {
        title: form.title.trim(),
        notes: form.notes,
        category: form.category,
        transaction_date: isDateLocked.value ? (props.transactionToEdit as any).transaction_date : form.transaction_date
      }
      if (!isAmountLocked.value) {
        updatePayload.gross_amount = Number(form.gross_amount)
        updatePayload.net_amount = Number(form.gross_amount)
      }
      await ledgerStore.updateTransaction(props.transactionToEdit.id, updatePayload)
      emit('updated')
      emit('close')
      return
    }

    const payload: any = {
      account: form.account,
      transaction_type: form.transaction_type,
      category: form.category,
      gross_amount: form.gross_amount,
      net_amount: isSplit.value ? calculatedNetExpense.value : form.gross_amount,
      title: form.title,
      notes: form.notes,
      transaction_date: form.transaction_date
    }

    if (isSplit.value && form.transaction_type === 'OUTFLOW') {
      if (splitMode.value === 'ITEMIZED') {
        if (harntungParticipants.value.length > 0 && !harntungPayerName.value) {
          errorMessage.value = 'Please select who paid for the bill (Payer)'
          isSubmitting.value = false
          return
        }
        payload.split_metadata = {
          mode: 'ITEMIZED',
          service_charge_pct: Number(serviceChargePct.value || 0),
          vat_pct: Number(vatPct.value || 0),
          payer_name: harntungPayerName.value || 'Me',
          items: harntungItems.value,
          participants: harntungParticipants.value
        }
        payload.auto_create_radar_debtors = autoCreateRadarDebtors.value
      } else if (participants.value.length > 0) {
        payload.splits_payload = participants.value.map((p) => ({
          counterparty_name: p.counterparty_name,
          counterparty_contact: p.counterparty_contact,
          amount: p.amount
        }))
        payload.auto_create_radar_debtors = autoCreateRadarDebtors.value
      }
    }

    const created = await ledgerStore.createTransaction(payload)
    if (selectedFile.value && created?.id) {
      try {
        await storageStore.uploadDirect(selectedFile.value, 'ledger', created.id)
      } catch (uploadErr) {
        console.error('Failed to attach slip to transaction', uploadErr)
      }
    }
    emit('created')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.error || err.response?.data?.gross_amount || err.message || 'Failed to record transaction.'
  } finally {
    isSubmitting.value = false
  }
}
</script>