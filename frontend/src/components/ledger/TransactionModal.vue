<template>
  <div
    v-if="isOpen"
    @click.self="emit('close')"
    class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans"
  >
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-xl p-6 shadow-2xl relative my-8 max-h-[90vh] overflow-y-auto">
      <button
        @click="emit('close')"
        type="button"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="mb-4">
        <h3 class="text-base font-semibold text-zinc-100 tracking-tight flex items-center gap-2">
          <span>New Transaction</span>
        </h3>
      </div>

      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4 text-xs font-mono">
        <!-- 1. Type Switcher: Expense vs Income -->
        <div class="flex items-center p-1 rounded-lg bg-zinc-900 border border-zinc-800">
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
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono text-xs transition-colors"
            >
              <option
                v-for="acc in ledgerStore.accounts"
                :key="acc.id"
                :value="acc.id"
              >
                {{ acc.name }} (฿{{ Number(acc.current_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }})
              </option>
            </select>
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
                :disabled="isSplit && splitMode === 'ITEMIZED'"
                placeholder="0.00"
                class="w-full pl-7 pr-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono font-semibold transition-colors disabled:opacity-75"
              />
            </div>
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
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono transition-colors"
            />
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

        <!-- 5. SMART BILL-SPLITTING PANEL (Expense Only) -->
        <div v-if="form.transaction_type === 'OUTFLOW'" class="pt-1">
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
              My Net Share: <strong class="text-emerald-400 font-semibold">฿{{ calculatedNetExpense.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</strong>
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
                  <button
                    type="button"
                    @click="addHarntungParticipant"
                    class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1 cursor-pointer"
                  >
                    <Plus class="w-3 h-3" />
                    <span>Add Friend</span>
                  </button>
                </div>

                <div class="flex flex-wrap items-center gap-2">
                  <div
                    v-for="(p, pIdx) in harntungParticipants"
                    :key="pIdx"
                    class="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-950 border border-zinc-800 text-xs"
                  >
                    <span v-if="p.name === 'Me'" class="font-semibold text-emerald-400">Me (Payer)</span>
                    <input
                      v-else
                      v-model="p.name"
                      type="text"
                      placeholder="Friend name"
                      class="bg-transparent text-zinc-100 text-xs outline-none w-20"
                    />
                    <input
                      v-if="p.name !== 'Me'"
                      v-model="p.contact"
                      type="text"
                      placeholder="PromptPay"
                      class="bg-transparent text-zinc-500 text-[10px] outline-none w-20 font-mono"
                    />
                    <button
                      v-if="p.name !== 'Me'"
                      type="button"
                      @click="removeHarntungParticipant(pIdx)"
                      class="text-zinc-500 hover:text-rose-400 transition-colors ml-0.5"
                    >
                      <X class="w-3 h-3" />
                    </button>
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
                    <div class="flex items-center gap-2">
                      <input
                        v-model="item.name"
                        type="text"
                        placeholder="Dish / Item Name"
                        class="flex-1 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 outline-none"
                      />
                      <div class="relative w-28">
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
                      <div class="flex items-center gap-1 text-[11px] text-zinc-500">
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
                        class="p-1 text-zinc-500 hover:text-rose-400 transition-colors cursor-pointer"
                        title="Remove dish"
                      >
                        <Trash2 class="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <!-- Who Ate This? (Consumers Chips) -->
                    <div class="flex flex-wrap items-center gap-1.5 pt-1 text-[11px]">
                      <span class="text-zinc-500 text-[10px] mr-1">Consumers:</span>
                      <button
                        type="button"
                        @click="toggleAllConsumers(item)"
                        class="px-1.5 py-0.5 rounded text-[10px] font-mono border transition-colors cursor-pointer"
                        :class="item.consumers.length === harntungParticipants.length ? 'bg-zinc-800 text-zinc-200 border-zinc-600' : 'text-zinc-500 border-zinc-800 hover:text-zinc-300'"
                      >
                        [All]
                      </button>
                      <button
                        v-for="p in harntungParticipants"
                        :key="p.name"
                        type="button"
                        @click="toggleConsumer(item, p.name)"
                        class="px-2 py-0.5 rounded text-[10px] font-mono border transition-colors cursor-pointer"
                        :class="item.consumers.includes(p.name) ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-semibold' : 'text-zinc-600 border-zinc-800/80 hover:text-zinc-400'"
                      >
                        {{ p.name }}
                      </button>

                      <span v-if="item.consumers.length > 0 && item.price > 0" class="text-[10px] text-zinc-500 font-mono ml-auto">
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
                      <span :class="share.name === 'Me' ? 'text-emerald-400 font-bold' : 'text-zinc-300'">
                        {{ share.name === 'Me' ? 'Me (My Expense)' : share.name }}
                      </span>
                      <span class="text-[10px] text-zinc-500">({{ share.itemsCount }} items)</span>
                    </div>
                    <span :class="share.name === 'Me' ? 'text-emerald-400 font-semibold' : 'text-zinc-200'">
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
                <div class="flex items-center gap-2">
                  <input
                    v-model="p.counterparty_contact"
                    type="text"
                    placeholder="Phone / PromptPay"
                    class="w-32 sm:w-36 px-2 py-1.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-300 placeholder-zinc-600 text-[11px] font-mono outline-none hover:border-zinc-700 focus:border-zinc-500 transition-colors"
                  />
                  <div class="relative w-28 sm:w-32">
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

        <!-- Receipt / Slip Attachment (Zero-Disk Google Drive) -->
        <div>
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

        <!-- Form Actions -->
        <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800/80">
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
            {{ isSubmitting ? 'Saving...' : 'Record Transaction' }}
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
import type { TransactionType } from '../../types/ledger'
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
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created'): void
}>()

const ledgerStore = useLedgerStore()
const storageStore = useStorageStore()
const isSubmitting = ref(false)
const errorMessage = ref('')
const copySuccess = ref(false)
const selectedFile = ref<File | null>(null)

const isSplit = ref(false)
const splitMode = ref<'ITEMIZED' | 'EQUAL' | 'CUSTOM'>('ITEMIZED')
const equalSplitPeopleCount = ref(4)
const autoCreateRadarDebtors = ref(true)

// ============= Harntung Itemized State =============
const serviceChargePct = ref(10)
const vatPct = ref(7)

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

const harntungParticipants = ref<HarntungParticipant[]>([
  { name: 'Me', contact: '' },
  { name: 'Ball', contact: '' },
  { name: 'Earth', contact: '' }
])

const harntungItems = ref<HarntungItem[]>([
  { name: 'Main Dish', price: 600, quantity: 1, consumers: ['Me', 'Ball', 'Earth'] },
  { name: 'Special Menu', price: 350, quantity: 1, consumers: ['Ball', 'Earth'] }
])

// ============= Classic Quick Split State =============
interface ParticipantRow {
  counterparty_name: string
  counterparty_contact: string
  amount: number
}

const participants = ref<ParticipantRow[]>([
  { counterparty_name: 'Ball', counterparty_contact: '', amount: 0 },
  { counterparty_name: 'Earth', counterparty_contact: '', amount: 0 },
  { counterparty_name: 'Bank', counterparty_contact: '', amount: 0 }
])

const form = reactive({
  account: '',
  transaction_type: 'OUTFLOW' as TransactionType,
  category: null as string | null,
  gross_amount: 0,
  title: '',
  notes: '',
  transaction_date: new Date().toISOString().split('T')[0]
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
  const me = harntungCalculatedShares.value.find(s => s.name === 'Me')
  return me ? me.finalShare : 0
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
      .filter(s => s.name !== 'Me')
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
  () => props.isOpen,
  (open) => {
    if (open) {
      window.addEventListener('keydown', handleKeyDown)
      if (!form.account && ledgerStore.accounts.length > 0) {
        const def = ledgerStore.accounts.find((a) => a.is_default) || ledgerStore.accounts[0]
        form.account = def.id
      }
      form.transaction_date = new Date().toISOString().split('T')[0]
      errorMessage.value = ''
      selectedFile.value = null
      storageStore.fetchStatus().catch(() => {})
    } else {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }
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
  const count = Math.max(2, equalSplitPeopleCount.value)
  const perPerson = Number((Number(form.gross_amount) / count).toFixed(2))
  participants.value.forEach((p) => {
    p.amount = perPerson
  })
}

function handlePeopleCountInput() {
  const targetFriends = Math.max(1, equalSplitPeopleCount.value - 1)
  while (participants.value.length < targetFriends) {
    participants.value.push({
      counterparty_name: `Friend ${participants.value.length + 1}`,
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
    counterparty_name: `Friend ${participants.value.length + 1}`,
    counterparty_contact: '',
    amount: splitMode.value === 'EQUAL' && form.gross_amount
      ? Number((Number(form.gross_amount) / (participants.value.length + 2)).toFixed(2))
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
  const nextNum = harntungParticipants.value.length
  harntungParticipants.value.push({
    name: `Friend ${nextNum}`,
    contact: ''
  })
}

function removeHarntungParticipant(idx: number) {
  const removedName = harntungParticipants.value[idx].name
  harntungParticipants.value.splice(idx, 1)
  harntungItems.value.forEach(item => {
    item.consumers = item.consumers.filter(c => c !== removedName)
  })
}

function addHarntungItem() {
  harntungItems.value.push({
    name: `Dish ${harntungItems.value.length + 1}`,
    price: 250,
    quantity: 1,
    consumers: harntungParticipants.value.map(p => p.name)
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
    item.consumers = ['Me']
  } else {
    item.consumers = harntungParticipants.value.map(p => p.name)
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
      text += `• ${s.name}${contactInfo}: ฿${s.finalShare.toLocaleString('en-US', { minimumFractionDigits: 2 })}\n`
    })
    text += `--------------------------------\n`
    text += `My Net Share: ฿${harntungPayerShare.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
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
  if (isOverAllocated.value) return
  errorMessage.value = ''
  isSubmitting.value = true
  try {
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
        payload.split_metadata = {
          mode: 'ITEMIZED',
          service_charge_pct: Number(serviceChargePct.value || 0),
          vat_pct: Number(vatPct.value || 0),
          payer_name: 'Me',
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