<template>
  <div v-if="isOpen && obligation" @click.self="emit('close')" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 font-sans overflow-hidden">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-xl shadow-2xl relative flex flex-col max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] overflow-hidden">
      <!-- Fixed Header -->
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
        <div>
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border bg-zinc-900 text-zinc-400 border-zinc-800">
              {{ obligation.type }}
            </span>
            <span v-if="obligation.subtype || form.metadata.subtype" class="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border bg-zinc-900 text-zinc-300 border-zinc-800">
              {{ obligation.subtype || form.metadata.subtype }}
            </span>
            <span class="text-xs text-zinc-500 font-mono">ID: {{ obligation.id.slice(0, 8) }}</span>
          </div>
          <h2 class="text-base font-semibold text-zinc-100 tracking-tight flex items-center gap-2">
            <span>Edit {{ obligationTitleLabel }}</span>
          </h2>
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
      <form @submit.prevent="handleSubmit" class="flex flex-col flex-1 min-h-0 overflow-hidden">
        <div class="p-4 sm:p-5 space-y-3.5 overflow-y-auto overscroll-contain flex-1 min-h-0">
          <!-- Error message -->
          <div v-if="errorMessage" class="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {{ errorMessage }}
          </div>

          <!-- Workspace Mirrored Warning Banner -->
          <div v-if="isWorkspaceMirroredObligation" class="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-2.5">
            <span class="text-base leading-none">ℹ️</span>
            <div>
              <p class="font-medium text-amber-200">
                Managed by Workspace ({{ isMA ? 'Maintenance Agreement' : 'Infrastructure Asset' }})
              </p>
              <p class="text-[11px] text-amber-300/80 mt-0.5 leading-relaxed">
                Financial terms, schedule, and currency are synchronized from Workspace as the Single Source of Truth.
                <router-link :to="workspaceLink" class="underline text-amber-200 font-semibold hover:text-white ml-1">
                  Edit in Workspace &rarr;
                </router-link>
              </p>
            </div>
          </div>

          <!-- Common Title & Amount -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div class="sm:col-span-2">
              <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
                {{ isBNPLOrder ? 'Order / Item Name' : 'Title' }}
              </label>
              <input
                v-model="form.title"
                type="text"
                required
                :disabled="isWorkspaceMirroredObligation"
                class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              />
            </div>
            <div>
              <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
                Amount ({{ form.currency || 'THB' }})
              </label>
              <input
                v-model="form.amount"
                type="number"
                step="0.01"
                required
                :disabled="isFinancialAmountLocked"
                class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              />
              <span v-if="isFinancialAmountLocked" class="text-[9px] text-amber-500/90 font-mono block mt-0.5">
                {{ financialAmountLockReason }}
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Currency</label>
              <select
                v-model="form.currency"
                :disabled="isFinancialAmountLocked"
                class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <option value="THB">THB (฿)</option>
                <option value="USD">USD ($)</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Flow Direction</label>
              <select
                v-model="form.direction"
                :disabled="obligation.type !== 'DEBT' || isWorkspaceMirroredObligation"
                class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <option value="OUTFLOW">OUTFLOW (Expense / Liability)</option>
                <option value="INFLOW">INFLOW (Income / Receivable)</option>
              </select>
            </div>
          </div>

          <!-- 1. HIRE PURCHASE -->
          <div v-if="obligation.type === 'INSTALLMENT' && (obligation.subtype === 'HIRE_PURCHASE' || form.metadata.subtype === 'HIRE_PURCHASE')" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-semibold text-zinc-200 uppercase tracking-wider">Hire Purchase Parameters</span>
              <span class="text-[10px] text-zinc-500">Contract & Vehicle Info</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Contract Number</label>
                <input
                  v-model="form.metadata.contract_number"
                  type="text"
                  placeholder="e.g. HP-2024-001"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Lender / Leasing</label>
                <input
                  v-model="form.metadata.lender"
                  type="text"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Vehicle Model</label>
                <input
                  v-model="form.metadata.vehicle_model"
                  type="text"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">License Plate</label>
                <input
                  v-model="form.metadata.license_plate"
                  type="text"
                  placeholder="e.g. 1กก 1234 กทม"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Insurance Provider</label>
                <input
                  v-model="form.metadata.insurance_provider"
                  type="text"
                  placeholder="e.g. Viriyah Insurance"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Tax Expiry Date</label>
                <input
                  v-model="form.metadata.tax_expiry_date"
                  type="date"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Notes</label>
              <textarea
                v-model="form.metadata.notes"
                rows="2"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div class="p-2.5 rounded bg-zinc-950/70 border border-zinc-800/80 space-y-1.5 text-[10px] text-zinc-400">
              <span class="font-semibold text-zinc-300 block">Financial Terms (Schedule Locked)</span>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono">
                <div>Terms: <strong class="text-zinc-200">{{ form.metadata.current_term }}/{{ form.metadata.total_terms }}</strong></div>
                <div>Principal: <strong class="text-zinc-200">฿{{ form.metadata.financed_amount || '0' }}</strong></div>
                <div>Rate: <strong class="text-zinc-200">{{ form.metadata.flat_rate_pa || '0' }}%</strong></div>
                <div>Down: <strong class="text-zinc-200">฿{{ form.metadata.down_payment || '0' }}</strong></div>
              </div>
              <p class="text-[9px] text-zinc-500">
                Loan principal and interest rate are locked after contract initialization to protect amortization integrity.
              </p>
            </div>
          </div>

          <!-- 2. BNPL ACCOUNT -->
          <div v-else-if="obligation.type === 'INSTALLMENT' && (obligation.subtype === 'BNPL_ACCOUNT' || form.metadata.subtype === 'BNPL_ACCOUNT')" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
            <div class="text-[11px] font-semibold text-zinc-200 uppercase tracking-wider">BNPL Account Parameters</div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Provider</label>
                <input
                  v-model="form.metadata.provider"
                  type="text"
                  required
                  placeholder="e.g. SPayLater, LazPayLater"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Credit Limit</label>
                <input
                  v-model.number="form.metadata.credit_limit"
                  type="number"
                  step="0.01"
                  required
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Cutoff Day (1-31)</label>
                <input
                  v-model.number="form.metadata.cutoff_day"
                  type="number"
                  min="1"
                  max="31"
                  required
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Due Day (1-31)</label>
                <input
                  v-model.number="form.metadata.due_day"
                  type="number"
                  min="1"
                  max="31"
                  required
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Account Number / ID</label>
                <input
                  v-model="form.metadata.account_number"
                  type="text"
                  placeholder="e.g. User ID or Ref"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Notes</label>
              <textarea
                v-model="form.metadata.notes"
                rows="2"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>

          <!-- 3. BNPL ORDER (Sub-Order) -->
          <div v-else-if="obligation.type === 'INSTALLMENT' && (obligation.subtype === 'BNPL_ORDER' || form.metadata.subtype === 'BNPL_ORDER')" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
            <div class="text-[11px] font-semibold text-zinc-200 uppercase tracking-wider">Purchase Order Details</div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Store / Merchant</label>
                <input
                  v-model="form.metadata.store"
                  type="text"
                  placeholder="e.g. Apple Store, Shopee"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Order Number</label>
                <input
                  v-model="form.metadata.order_number"
                  type="text"
                  placeholder="e.g. ORD-987654"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Order Date</label>
                <input
                  v-model="form.metadata.order_date"
                  type="date"
                  :disabled="isOrderDateLocked"
                  :class="[
                    'w-full px-3 py-1.5 rounded border text-xs',
                    isOrderDateLocked
                      ? 'bg-zinc-950/60 border-zinc-800 text-zinc-500 cursor-not-allowed'
                      : 'bg-zinc-900 border-zinc-800 text-zinc-100'
                  ]"
                />
                <p v-if="isOrderDateLocked" class="text-[9px] text-amber-500/80 mt-1">
                  Order date is locked because payments have already been recorded.
                </p>
              </div>
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Notes</label>
              <textarea
                v-model="form.metadata.notes"
                rows="2"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div class="p-2.5 rounded bg-zinc-950/70 border border-zinc-800/80 space-y-1 text-[10px] text-zinc-400">
              <span class="font-semibold text-zinc-300 block">Financial Terms (Locked)</span>
              <div class="grid grid-cols-3 gap-2 font-mono">
                <div>Terms: <strong class="text-zinc-200">{{ form.metadata.current_term }}/{{ form.metadata.total_terms }}</strong></div>
                <div>Down: <strong class="text-zinc-200">฿{{ form.metadata.down_payment || '0' }}</strong></div>
                <div>Total: <strong class="text-zinc-200">฿{{ form.metadata.total_price || (Number(form.amount) * Number(form.metadata.total_terms || 1)) }}</strong></div>
              </div>
              <p class="text-[9px] text-zinc-500">
                Installment terms, down payment, and monthly amounts are locked to prevent desynchronization with billing history.
              </p>
            </div>
          </div>

          <!-- 4. STANDARD INSTALLMENT -->
          <div v-else-if="obligation.type === 'INSTALLMENT'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
            <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Installment Parameters</div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Contract Number</label>
                <input
                  v-model="form.metadata.contract_number"
                  type="text"
                  placeholder="Contract #"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Lender / Institution</label>
                <input
                  v-model="form.metadata.lender"
                  type="text"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Billing Day of Month (1-31)</label>
                <input
                  v-model.number="form.billing_day"
                  type="number"
                  min="1"
                  max="31"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Terms Progress (Locked)</label>
                <div class="px-3 py-1.5 rounded bg-zinc-950 border border-zinc-800/80 text-xs text-zinc-300 font-mono">
                  Term {{ form.metadata.current_term }} of {{ form.metadata.total_terms }}
                </div>
              </div>
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Notes</label>
              <textarea
                v-model="form.metadata.notes"
                rows="2"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>

          <!-- 5. SUBSCRIPTION & FREE TRIAL -->
          <div v-else-if="obligation.type === 'SUBSCRIPTION' || obligation.type === 'FREE_TRIAL'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">
                {{ obligation.type === 'FREE_TRIAL' ? 'Free Trial Watchdog Parameters' : 'Subscription Dossier' }}
              </span>
              <span v-if="obligation.type === 'FREE_TRIAL'" class="text-[10px] text-amber-400 font-semibold">
                Trial Auto-Renew Protection
              </span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Plan / Tier Name</label>
                <input
                  v-model="form.metadata.plan_name"
                  type="text"
                  placeholder="e.g. Pro, Family, Premium"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Category</label>
                <select
                  v-model="form.metadata.category"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                >
                  <option value="GENERAL">General</option>
                  <option value="AI Tools">AI Tools</option>
                  <option value="Streaming">Streaming</option>
                  <option value="Cloud / Infra">Cloud / Infra</option>
                  <option value="Productivity">Productivity</option>
                  <option value="Developer">Developer</option>
                  <option value="Fitness">Fitness</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Account Email</label>
                <input
                  v-model="form.metadata.account_email"
                  type="email"
                  placeholder="user@example.com"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Payment Method</label>
                <input
                  v-model="form.metadata.payment_method"
                  type="text"
                  placeholder="e.g. Visa ••4242, TrueMoney"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div v-if="obligation.type === 'SUBSCRIPTION'">
                <label class="block text-[10px] text-zinc-500 mb-1">Billing Cycle</label>
                <select
                  v-model="form.metadata.billing_cycle"
                  :disabled="isWorkspaceMirroredObligation"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  <option value="MONTHLY">Monthly</option>
                  <option value="YEARLY">Yearly</option>
                  <option value="QUARTERLY">Quarterly</option>
                  <option value="WEEKLY">Weekly</option>
                </select>
              </div>
              <div v-else>
                <label class="block text-[10px] text-zinc-500 mb-1">Auto-Renew Liability</label>
                <input
                  v-model.number="form.metadata.auto_renew_cost"
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Alert Days in Advance</label>
                <input
                  v-model.number="form.metadata.alert_days_before"
                  type="number"
                  min="1"
                  max="30"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>

            <div v-if="obligation.type === 'SUBSCRIPTION'" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Billing Day of Month (1-31)</label>
                <input
                  v-model.number="form.billing_day"
                  type="number"
                  min="1"
                  max="31"
                  :disabled="isWorkspaceMirroredObligation"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Website / Direct URL</label>
              <input
                v-model="form.metadata.cancel_url"
                type="url"
                placeholder="https://service.com/account/billing"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>

            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Cancellation / Renewal Steps</label>
              <textarea
                v-model="form.metadata.cancel_steps"
                rows="2"
                placeholder="e.g. Go to Settings → Subscriptions → Cancel Subscription"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>

            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Notes</label>
              <textarea
                v-model="form.metadata.notes"
                rows="2"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>

          <!-- 6. DEBT -->
          <div v-else-if="obligation.type === 'DEBT'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
            <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Debt Settlement Details</div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">
                  {{ form.direction === 'INFLOW' ? 'Debtor Name' : 'Creditor / Lender Name' }}
                </label>
                <input
                  v-model="form.metadata.counterparty"
                  type="text"
                  required
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">PromptPay / Settlement Account</label>
                <input
                  v-model="form.metadata.promptpay"
                  type="text"
                  placeholder="PromptPay number"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Contact Phone</label>
                <input
                  v-model="form.metadata.contact"
                  type="text"
                  placeholder="081-xxx-xxxx"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Borrow / Loan Reason</label>
                <input
                  v-model="form.metadata.reason"
                  type="text"
                  placeholder="e.g. Personal loan, Travel buffer"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>

            <!-- Formal Loan specifics -->
            <div v-if="form.metadata.subtype === 'FORMAL_LOAN'" class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-zinc-800/60">
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Contract / Ref Number</label>
                <input
                  v-model="form.metadata.contract_no"
                  type="text"
                  placeholder="Contract #"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Bank / Institution</label>
                <input
                  v-model="form.metadata.creditor_bank"
                  type="text"
                  placeholder="e.g. SCB, KBank"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-zinc-500 mb-1">Interest Rate (% p.a.)</label>
                <input
                  v-model.number="form.metadata.interest_rate_pa"
                  type="number"
                  step="0.01"
                  class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
                />
              </div>
            </div>

            <div class="flex items-center gap-2 pt-1">
              <input
                id="edit-is-flexible-due"
                v-model="form.metadata.is_flexible"
                type="checkbox"
                class="rounded border-zinc-800 bg-zinc-900 text-zinc-100 focus:ring-0 focus:ring-offset-0"
              />
              <label for="edit-is-flexible-due" class="text-xs text-zinc-400 select-none cursor-pointer">
                Flexible / Open-ended due date (no fixed settlement deadline)
              </label>
            </div>
          </div>

          <!-- Common Next Due Date (Unless flexible debt) -->
          <div v-if="!form.metadata.is_flexible">
            <label class="block text-[10px] text-zinc-500 mb-1 font-mono">
              {{ obligation.type === 'FREE_TRIAL' ? 'Trial Expiration Date' : 'Next Due / Settlement Date' }}
            </label>
            <input
              v-model="form.due_date"
              type="date"
              :disabled="isWorkspaceMirroredObligation"
              class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono disabled:opacity-60 disabled:cursor-not-allowed"
            />
          </div>
        </div>

        <!-- Action Buttons (Sticky Footer) -->
        <div class="flex items-center justify-end gap-2.5 p-4 border-t border-zinc-800/80 shrink-0 bg-zinc-950/90">
          <button
            type="button"
            @click="emit('close')"
            class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-all active:scale-[0.98]"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-all active:scale-[0.98] disabled:opacity-50 shadow-sm"
          >
            {{ isSubmitting ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useFinanceStore } from '../../stores/finance'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import type { FinancialObligation } from '../../types/finance'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  obligation: FinancialObligation | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated'): void
}>()

useBodyScrollLock(() => props.isOpen)

const financeStore = useFinanceStore()
const isSubmitting = ref(false)
const errorMessage = ref('')

const form = ref({
  title: '',
  amount: '',
  currency: 'THB',
  direction: 'OUTFLOW' as 'OUTFLOW' | 'INFLOW',
  due_date: '',
  billing_day: '' as string | number,
  metadata: {} as Record<string, any>,
  project: null as string | null,
})

const isWorkspaceMirroredObligation = computed(() => {
  const st = form.value.metadata?.source_type || props.obligation?.metadata?.source_type
  return st === 'MA_CONTRACT' || st === 'INFRA_ASSET'
})

const isMA = computed(() => {
  const st = form.value.metadata?.source_type || props.obligation?.metadata?.source_type
  return st === 'MA_CONTRACT'
})

const workspaceLink = computed(() => {
  const meta = form.value.metadata || props.obligation?.metadata || {}
  const pid = meta.project_id || props.obligation?.project
  if (pid) {
    return `/workspace/projects/${pid}`
  }
  return '/workspace'
})

const isBNPLOrder = computed(() => {
  return props.obligation?.type === 'INSTALLMENT' &&
    (props.obligation?.subtype === 'BNPL_ORDER' || form.value.metadata?.subtype === 'BNPL_ORDER')
})

const isDebtWithPaymentsOrSplit = computed(() => {
  if (props.obligation?.type !== 'DEBT') return false
  const meta = props.obligation.metadata || {}
  const hasHistory = !!(props.obligation.payment_histories && props.obligation.payment_histories.length > 0)
  const remaining = Number(meta.remaining_balance ?? props.obligation.amount)
  const principal = Number(props.obligation.amount)
  const isPartiallyPaid = remaining < principal
  const isSplit = !!(props.obligation as any).is_split_debt ||
    !!meta.origin_transaction_id ||
    !!meta.origin_bill ||
    !!meta.origin_split_id ||
    !!meta.split_bill_id ||
    !!(props.obligation as any).origin_split?.length
  return hasHistory || isPartiallyPaid || isSplit
})

const debtLockReason = computed(() => {
  if (!isDebtWithPaymentsOrSplit.value) return ''
  const meta = props.obligation?.metadata || {}
  const isSplit = !!(props.obligation as any).is_split_debt ||
    !!meta.origin_transaction_id ||
    !!meta.origin_bill ||
    !!meta.origin_split_id ||
    !!meta.split_bill_id ||
    !!(props.obligation as any).origin_split?.length
  if (isSplit) {
    return 'Principal is locked for obligations linked to a Split Bill.'
  }
  return 'Principal is locked because payment history already exists.'
})

const isOrderDateLocked = computed(() => {
  if (!isBNPLOrder.value) return false
  const currentTerm = Number(props.obligation?.metadata?.current_term || 0)
  const hasHistory = !!(props.obligation?.payment_histories && props.obligation.payment_histories.length > 0)
  return currentTerm > 0 || hasHistory
})

const isFinancialAmountLocked = computed(() => {
  if (!props.obligation) return false
  return isBNPLOrder.value || isDebtWithPaymentsOrSplit.value || isWorkspaceMirroredObligation.value
})

const financialAmountLockReason = computed(() => {
  if (isWorkspaceMirroredObligation.value) {
    return `Managed by Workspace (${isMA.value ? 'Maintenance Agreement' : 'Infrastructure Asset'}). Read-only.`
  }
  if (isBNPLOrder.value) {
    return 'Locked to match installment term'
  }
  if (isDebtWithPaymentsOrSplit.value) {
    return debtLockReason.value
  }
  return ''
})

const obligationTitleLabel = computed(() => {
  if (!props.obligation) return 'Obligation'
  if (props.obligation.type === 'FREE_TRIAL') return 'Free Trial Watchdog'
  if (props.obligation.type === 'SUBSCRIPTION') return 'Subscription'
  if (isBNPLOrder.value) return 'Purchase Order'
  if (props.obligation.type === 'INSTALLMENT') return 'Installment Contract'
  if (props.obligation.type === 'DEBT') return 'Debt / Loan'
  return 'Obligation'
})

function initForm(ob: FinancialObligation | null) {
  errorMessage.value = ''
  if (!ob) return

  const meta = { ...(ob.metadata || {}) }

  form.value = {
    title: ob.title,
    amount: String(ob.amount),
    currency: ob.currency,
    direction: ob.direction || 'OUTFLOW',
    due_date: ob.due_date ? ob.due_date.split('T')[0] : '',
    billing_day: ob.billing_day || '',
    project: ob.project || null,
    metadata: {
      ...meta,
      is_flexible: !!meta.is_flexible,
      plan_name: meta.plan_name || '',
      category: meta.category || 'GENERAL',
      account_email: meta.account_email || '',
      payment_method: meta.payment_method || meta.linked_card || '',
      cancel_url: meta.cancel_url || '',
      cancel_steps: meta.cancel_steps || '',
      alert_days_before: meta.alert_days_before ?? 3,
      auto_renew_cost: meta.auto_renew_cost ?? ob.amount,
      notes: meta.notes || '',
      store: meta.store || '',
      order_number: meta.order_number || '',
      order_date: meta.order_date || '',
      contract_number: meta.contract_number || meta.contract_no || '',
      contract_no: meta.contract_no || meta.contract_number || '',
      license_plate: meta.license_plate || '',
      insurance_provider: meta.insurance_provider || '',
      policy_number: meta.policy_number || '',
      tax_expiry_date: meta.tax_expiry_date || '',
      counterparty: meta.counterparty || '',
      contact: meta.contact || '',
      promptpay: meta.promptpay || '',
      reason: meta.reason || '',
      creditor_bank: meta.creditor_bank || '',
      interest_rate_pa: meta.interest_rate_pa ?? 0
    }
  }
}

watch(
  () => [props.isOpen, props.obligation] as const,
  ([open, ob], prev) => {
    const prevOpen = prev ? prev[0] : false
    const prevOb = prev ? prev[1] : null
    if (open && (!prevOpen || ob !== prevOb)) {
      initForm(ob)
    }
  },
  { immediate: true }
)

async function handleSubmit() {
  if (isSubmitting.value || !props.obligation) return
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    const existingMeta = props.obligation.metadata || {}
    const updatedMeta: Record<string, any> = {
      ...existingMeta,
      ...form.value.metadata
    }

    if (isBNPLOrder.value) {
      if (existingMeta.total_terms !== undefined) updatedMeta.total_terms = existingMeta.total_terms
      if (existingMeta.down_payment !== undefined) updatedMeta.down_payment = existingMeta.down_payment
      if (existingMeta.financed_amount !== undefined) updatedMeta.financed_amount = existingMeta.financed_amount
      if (isOrderDateLocked.value && existingMeta.order_date !== undefined) {
        updatedMeta.order_date = existingMeta.order_date
      }
    }

    if (props.obligation.type === 'DEBT') {
      delete updatedMeta.remaining_balance
      delete updatedMeta.total_paid
      delete updatedMeta.paid_total
      delete updatedMeta.progress_pct
      delete updatedMeta.progress_percentage
      delete updatedMeta.is_settled
    }

    if (props.obligation.type === 'FREE_TRIAL' || props.obligation.type === 'SUBSCRIPTION') {
      const pm = (form.value.metadata.payment_method || '').trim()
      updatedMeta.payment_method = pm
      updatedMeta.linked_card = pm
    }

    // Clean optional fields to ensure empty strings or nulls are properly sanitized
    if (form.value.metadata.is_flexible) {
      updatedMeta.is_flexible = true
    } else {
      updatedMeta.is_flexible = false
    }

    const payload: Record<string, any> = {
      title: form.value.title.trim(),
      amount: parseFloat(form.value.amount),
      currency: form.value.currency,
      direction: form.value.direction,
      metadata: updatedMeta,
      project: form.value.project
    }

    if (isDebtWithPaymentsOrSplit.value) {
      payload.amount = parseFloat(String(props.obligation.amount))
      payload.currency = props.obligation.currency
    }

    if (isWorkspaceMirroredObligation.value) {
      payload.title = props.obligation.title
      payload.amount = parseFloat(String(props.obligation.amount))
      payload.currency = props.obligation.currency
      payload.due_date = props.obligation.due_date ? props.obligation.due_date.split('T')[0] : null
      payload.billing_day = props.obligation.billing_day || null
      if (props.obligation.metadata?.billing_cycle) {
        updatedMeta.billing_cycle = props.obligation.metadata.billing_cycle
      }
    } else {
      if (form.value.metadata.is_flexible) {
        payload.due_date = null
      } else if (form.value.due_date) {
        payload.due_date = form.value.due_date
      } else {
        payload.due_date = null
      }

      if (form.value.billing_day) {
        payload.billing_day = parseInt(String(form.value.billing_day), 10)
      } else {
        payload.billing_day = null
      }
    }

    await financeStore.updateObligation(props.obligation.id, payload)
    emit('updated')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || err.response?.data?.metadata || err.message || 'Failed to update obligation'
  } finally {
    isSubmitting.value = false
  }
}
</script>
