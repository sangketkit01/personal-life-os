<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans pb-16">
    <!-- Breadcrumb & Top Navigation -->
    <div class="pb-4 border-b border-zinc-800/80">
      <nav aria-label="Breadcrumb" class="mb-2">
        <ol class="flex items-center gap-2 text-xs font-mono text-zinc-500 flex-wrap">
          <li class="flex items-center gap-2">
            <RouterLink to="/finance/overview" class="hover:text-zinc-300 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-400 rounded px-1 -mx-1">{{ t('crumb.finance') }}</RouterLink>
            <span aria-hidden="true" class="text-zinc-700 select-none">/</span>
          </li>
          <li class="flex items-center gap-2">
            <RouterLink to="/finance/installments" class="hover:text-zinc-300 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-400 rounded px-1 -mx-1">{{ t('crumb.installments') }}</RouterLink>
            <span aria-hidden="true" class="text-zinc-700 select-none">/</span>
          </li>
          <li>
            <span aria-current="page" class="text-zinc-300 font-medium">{{ contract?.title || t('crumb.contractDossier') }}</span>
          </li>
        </ol>
      </nav>

      <!-- Header Row -->
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2.5 flex-wrap">
            <h1 class="text-xl font-semibold text-zinc-100 tracking-tight">
              {{ contract?.title || 'Loading Contract...' }}
            </h1>
            <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
              {{ contract?.subtype === 'HIRE_PURCHASE' ? 'VEHICLE HIRE PURCHASE' : 'FIXED INSTALLMENT' }}
            </span>
            <span
              class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase border"
              :class="contract?.status === 'ACTIVE'
                ? 'bg-zinc-900 text-zinc-300 border-zinc-800'
                : 'bg-zinc-900 text-emerald-400 border-zinc-800'"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="contract?.status === 'ACTIVE' ? 'bg-zinc-400' : 'bg-emerald-400'"></span>
              <span>{{ contract?.status }}</span>
            </span>
          </div>

          <div class="flex items-center gap-3 text-xs text-zinc-400 mt-1 font-mono flex-wrap">
            <span v-if="contract?.metadata?.lender" class="text-zinc-300">
              Lender: <strong>{{ contract.metadata.lender }}</strong>
            </span>
            <span v-if="contract?.metadata?.contract_number" class="text-zinc-500">
              Ref: {{ contract.metadata.contract_number }}
            </span>
            <span v-if="contract?.billing_day" class="text-zinc-500">
              Billing Day: {{ contract.billing_day }}th of month
            </span>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-2 self-start lg:self-auto flex-wrap">
          <button
            @click="openPayModal"
            class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm cursor-pointer"
          >
            <CreditCard class="w-3.5 h-3.5 text-zinc-950" />
            <span>Record Payment</span>
          </button>

          <button
            @click="showUploadModal = true"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-mono transition-colors flex items-center gap-1.5"
          >
            <UploadCloud class="w-3.5 h-3.5 text-zinc-400" />
            <span>Upload Document</span>
          </button>

          <button
            @click="confirmDelete"
            class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-500 hover:text-rose-400 transition-colors"
            title="Delete contract"
          >
            <Trash2 class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="p-16 text-center text-xs font-mono text-zinc-500">
      Loading contract dossier and amortization schedule...
    </div>

    <!-- Contract Dossier Content -->
    <div v-else-if="contract" class="space-y-6">
      <!-- 1. High-Density Financial Metric Strip -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <!-- Monthly Installment -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Monthly Installment</span>
          <div class="mt-2 text-xl font-bold font-mono text-zinc-100 tabular-nums">
            {{ currencySymbol(contract.currency) }}{{ Number(contract.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 mt-1 block">Due {{ contract.due_date || 'N/A' }}</span>
        </div>

        <!-- Remaining Balance -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Remaining Balance</span>
          <div class="mt-2 text-xl font-bold font-mono text-zinc-100 tabular-nums">
            {{ currencySymbol(contract.currency) }}{{ Number(contract.summary?.remaining_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 mt-1 block">
            {{ remainingTermsCount }} of {{ totalTermsCount }} terms remaining
          </span>
        </div>

        <!-- Financed Principal -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Financed Principal</span>
          <div class="mt-2 text-xl font-bold font-mono text-zinc-300 tabular-nums">
            {{ currencySymbol(contract.currency) }}{{ Number(contract.metadata?.financed_amount || contract.metadata?.total_principal || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 mt-1 block">
            Flat Rate: {{ contract.metadata?.flat_rate_pa || '0.00' }}% p.a.
          </span>
        </div>

        <!-- Tenor Progress -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
          <div class="flex items-center justify-between text-[10px] font-mono uppercase text-zinc-500">
            <span>Tenor Progress</span>
            <span class="text-zinc-200 font-bold">{{ progressPct }}%</span>
          </div>
          <div class="mt-2 text-xl font-bold font-mono text-zinc-100 tabular-nums">
            {{ currentTermCount }} / {{ totalTermsCount }}
          </div>
          <div class="w-full bg-zinc-800 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              class="bg-zinc-200 h-full rounded-full transition-all duration-300"
              :style="{ width: `${progressPct}%` }"
            />
          </div>
        </div>
      </div>

      <!-- 2. Sub-Domain Tab Switcher -->
      <div class="flex items-center gap-1 border-b border-zinc-800/80 overflow-x-auto">
        <button
          @click="activeTab = 'SCHEDULE'"
          type="button"
          class="px-4 py-2 text-xs font-mono border-b-2 transition-all flex items-center gap-2 whitespace-nowrap"
          :class="activeTab === 'SCHEDULE'
            ? 'border-zinc-200 text-zinc-100 font-semibold'
            : 'border-transparent text-zinc-500 hover:text-zinc-300'"
        >
          <Table class="w-3.5 h-3.5" />
          <span>Amortization Schedule ({{ scheduleItems.length }} Terms)</span>
        </button>

        <button
          v-if="contract.subtype === 'HIRE_PURCHASE'"
          @click="activeTab = 'SIMULATOR'"
          type="button"
          class="px-4 py-2 text-xs font-mono border-b-2 transition-all flex items-center gap-2 whitespace-nowrap"
          :class="activeTab === 'SIMULATOR'
            ? 'border-zinc-200 text-zinc-100 font-semibold'
            : 'border-transparent text-zinc-500 hover:text-zinc-300'"
        >
          <Calculator class="w-3.5 h-3.5" />
          <span>OCPB Early Payoff Simulator</span>
        </button>

        <button
          v-if="contract.subtype === 'HIRE_PURCHASE'"
          @click="activeTab = 'ASSET'"
          type="button"
          class="px-4 py-2 text-xs font-mono border-b-2 transition-all flex items-center gap-2 whitespace-nowrap"
          :class="activeTab === 'ASSET'
            ? 'border-zinc-200 text-zinc-100 font-semibold'
            : 'border-transparent text-zinc-500 hover:text-zinc-300'"
        >
          <Car class="w-3.5 h-3.5" />
          <span>Vehicle & Insurance Dossier</span>
        </button>

        <button
          @click="activeTab = 'DOCUMENTS'"
          type="button"
          class="px-4 py-2 text-xs font-mono border-b-2 transition-all flex items-center gap-2 whitespace-nowrap"
          :class="activeTab === 'DOCUMENTS'
            ? 'border-zinc-200 text-zinc-100 font-semibold'
            : 'border-transparent text-zinc-500 hover:text-zinc-300'"
        >
          <FileText class="w-3.5 h-3.5" />
          <span>Document Vault ({{ contract.attachments?.length || 0 }})</span>
        </button>

        <button
          @click="activeTab = 'HISTORY'"
          type="button"
          class="px-4 py-2 text-xs font-mono border-b-2 transition-all flex items-center gap-2 whitespace-nowrap"
          :class="activeTab === 'HISTORY'
            ? 'border-zinc-200 text-zinc-100 font-semibold'
            : 'border-transparent text-zinc-500 hover:text-zinc-300'"
        >
          <History class="w-3.5 h-3.5" />
          <span>Payment History ({{ contract.payment_histories?.length || 0 }})</span>
        </button>
      </div>

      <!-- TAB 1: Amortization Schedule Table -->
      <div v-if="activeTab === 'SCHEDULE'" class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
          <div class="flex items-center gap-2">
            <span class="text-zinc-400">Schedule Scope:</span>
            <div class="flex items-center bg-zinc-950 border border-zinc-800 rounded p-0.5">
              <button
                @click="scheduleFilter = 'ALL'"
                type="button"
                class="px-2 py-0.5 rounded text-[11px] transition-colors"
                :class="scheduleFilter === 'ALL' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
              >
                All Terms ({{ scheduleItems.length }})
              </button>
              <button
                @click="scheduleFilter = 'UPCOMING'"
                type="button"
                class="px-2 py-0.5 rounded text-[11px] transition-colors"
                :class="scheduleFilter === 'UPCOMING' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
              >
                Due & Upcoming ({{ upcomingScheduleCount }})
              </button>
              <button
                @click="scheduleFilter = 'PAID'"
                type="button"
                class="px-2 py-0.5 rounded text-[11px] transition-colors"
                :class="scheduleFilter === 'PAID' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
              >
                Settled ({{ currentTermCount }})
              </button>
            </div>
          </div>

          <div class="text-zinc-500 text-[11px]">
            * Calculated on {{ contract.metadata?.flat_rate_pa || 0 }}% p.a. flat rate with linear principal amortization
          </div>
        </div>

        <!-- Schedule Table -->
        <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr class="border-b border-zinc-800/80 bg-zinc-950/60 text-[11px] text-zinc-500 uppercase tracking-wider font-semibold">
                  <th class="py-3 px-4">Term</th>
                  <th class="py-3 px-4">Due Date</th>
                  <th class="py-3 px-4 text-right">Payment</th>
                  <th class="py-3 px-4 text-right">Principal</th>
                  <th class="py-3 px-4 text-right">Interest</th>
                  <th class="py-3 px-4 text-right">Remaining Principal</th>
                  <th class="py-3 px-4 text-center">Status</th>
                  <th class="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/50">
                <tr
                  v-for="term in filteredSchedule"
                  :key="term.term_number"
                  class="hover:bg-zinc-900/50 transition-colors"
                  :class="term.status === 'DUE' ? 'bg-zinc-900/30' : ''"
                >
                  <td class="py-3 px-4 font-semibold text-zinc-200">
                    #{{ term.term_number }} / {{ term.total_terms }}
                  </td>
                  <td class="py-3 px-4 text-zinc-300">
                    {{ term.due_date }}
                  </td>
                  <td class="py-3 px-4 text-right font-semibold text-zinc-100 tabular-nums">
                    {{ currencySymbol(contract.currency) }}{{ term.installment_amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-3 px-4 text-right text-zinc-400 tabular-nums">
                    {{ currencySymbol(contract.currency) }}{{ term.principal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-3 px-4 text-right text-zinc-500 tabular-nums">
                    {{ currencySymbol(contract.currency) }}{{ term.interest.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-3 px-4 text-right text-zinc-300 tabular-nums">
                    {{ currencySymbol(contract.currency) }}{{ term.remaining_principal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-3 px-4 text-center">
                    <span
                      class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border"
                      :class="getTermStatusBadgeClass(term.status)"
                    >
                      <span class="w-1.5 h-1.5 rounded-full" :class="getTermStatusDotClass(term.status)"></span>
                      <span>{{ term.status }}</span>
                    </span>
                  </td>
                  <td class="py-3 px-4 text-right">
                    <button
                      v-if="term.status !== 'PAID'"
                      @click="openPayModalForTerm(term.term_number, term.installment_amount)"
                      type="button"
                      class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] text-zinc-200 transition-colors cursor-pointer"
                    >
                      Pay Term
                    </button>
                    <span v-else class="text-zinc-600 text-[11px]">Settled</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 2: OCPB 2023 Early Payoff Simulator -->
      <div v-if="activeTab === 'SIMULATOR'" class="space-y-6">
        <div class="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-zinc-800/80">
            <div>
              <h2 class="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <Scale class="w-4 h-4 text-zinc-400" />
                <span>Statutory Early Payoff Discount Engine (Thai OCPB 2023)</span>
              </h2>
              <p class="text-xs text-zinc-400 mt-0.5">
                Calculates legal discounts on unearned interest pursuant to the Consumer Protection Board Hire-Purchase Notification (B.E. 2566).
              </p>
            </div>
            <div class="flex items-center gap-2 text-xs font-mono">
              <span class="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300">
                Tier Discount: <strong>{{ simDiscountPct }}%</strong>
              </span>
            </div>
          </div>

          <!-- Interactive Term Slider -->
          <div class="space-y-2 pt-2">
            <div class="flex items-center justify-between text-xs font-mono">
              <span class="text-zinc-400">
                Simulate Early Payoff at Term:
                <strong class="text-zinc-100">#{{ simTerm }} / {{ totalTermsCount }}</strong>
              </span>
              <span class="text-zinc-500">
                ({{ totalTermsCount - simTerm }} unearned terms remaining)
              </span>
            </div>
            <input
              v-model.number="simTerm"
              type="range"
              :min="currentTermCount"
              :max="totalTermsCount"
              step="1"
              class="w-full accent-zinc-200 cursor-pointer h-2 bg-zinc-800 rounded-lg"
            />
            <div class="flex justify-between text-[10px] font-mono text-zinc-500">
              <span>Term {{ currentTermCount }} (Today)</span>
              <span>Term {{ Math.round(totalTermsCount / 3) }} (60% tier)</span>
              <span>Term {{ Math.round(totalTermsCount * 2 / 3) }} (70% tier)</span>
              <span>Term {{ totalTermsCount }} (100% discount)</span>
            </div>
          </div>

          <!-- Calculation Comparison Cards -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 pt-2">
            <!-- Normal Sum of Installments -->
            <div class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Regular Remaining Commitment</span>
              <div class="text-lg font-bold text-zinc-300 tabular-nums">
                {{ currencySymbol(contract.currency) }}{{ simCalculation.regularRemainingTotal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </div>
              <p class="text-[10px] text-zinc-500">If paid on normal monthly installments without payoff</p>
            </div>

            <!-- Net Early Payoff Figure -->
            <div class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Statutory Payoff Settlement</span>
              <div class="text-lg font-bold text-zinc-100 tabular-nums">
                {{ currencySymbol(contract.currency) }}{{ simCalculation.payoffTotal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </div>
              <p class="text-[10px] text-zinc-500">Includes principal, discounted interest + 7% VAT</p>
            </div>

            <!-- Net Cash Savings -->
            <div class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Net Interest Saved</span>
              <div class="text-lg font-bold text-emerald-400 tabular-nums">
                +{{ currencySymbol(contract.currency) }}{{ simCalculation.netSavings.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </div>
              <p class="text-[10px] text-emerald-400/80">Direct cash savings by settling early at term #{{ simTerm }}</p>
            </div>
          </div>

          <!-- Detailed Breakdown Ledger -->
          <div class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 text-xs font-mono space-y-2">
            <h3 class="text-xs uppercase text-zinc-400 font-semibold tracking-wider pb-1 border-b border-zinc-800">
              Breakdown Audit Trail
            </h3>
            <div class="flex justify-between text-zinc-400">
              <span>Outstanding Financed Principal:</span>
              <span class="text-zinc-200">{{ currencySymbol(contract.currency) }}{{ simCalculation.remainingPrincipal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
            </div>
            <div class="flex justify-between text-zinc-400">
              <span>Remaining Unearned Interest (Full):</span>
              <span class="text-zinc-300">{{ currencySymbol(contract.currency) }}{{ simCalculation.remainingInterestBefore.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
            </div>
            <div class="flex justify-between text-emerald-400 font-medium">
              <span>Legal OCPB Discount ({{ simDiscountPct }}%):</span>
              <span>-{{ currencySymbol(contract.currency) }}{{ simCalculation.interestSaved.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
            </div>
            <div class="flex justify-between text-zinc-400">
              <span>Discounted Interest Payable:</span>
              <span class="text-zinc-200">{{ currencySymbol(contract.currency) }}{{ simCalculation.discountedInterest.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
            </div>
            <div class="flex justify-between text-zinc-400">
              <span>Value-Added Tax (VAT 7.0%):</span>
              <span class="text-zinc-200">{{ currencySymbol(contract.currency) }}{{ simCalculation.vat.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
            </div>
            <div class="pt-2 border-t border-zinc-800 flex justify-between font-bold text-sm text-zinc-100">
              <span>Net Settlement Amount:</span>
              <span>{{ currencySymbol(contract.currency) }}{{ simCalculation.payoffTotal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 3: Vehicle & Asset Metadata Dossier -->
      <div v-if="activeTab === 'ASSET'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80">
            <div>
              <h2 class="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <Car class="w-4 h-4 text-zinc-400" />
                <span>Vehicle & Asset Registration Dossier</span>
              </h2>
              <p class="text-xs text-zinc-400 mt-0.5">Asset specifications, provincial license registration, and road tax schedule</p>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div class="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Vehicle Make & Model</span>
              <span class="text-zinc-100 font-semibold block text-sm">
                {{ contract.metadata?.vehicle_model || contract.title }}
              </span>
            </div>

            <div class="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">License Plate & Province</span>
              <span class="text-zinc-100 font-semibold block text-sm">
                {{ contract.metadata?.license_plate || 'Not Specified' }}
              </span>
            </div>

            <div class="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Annual Road Tax Expiry</span>
              <span class="text-zinc-100 font-semibold block text-sm">
                {{ contract.metadata?.tax_expiry_date || 'N/A' }}
              </span>
            </div>

            <div class="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Insurance Provider</span>
              <span class="text-zinc-100 font-semibold block text-sm">
                {{ contract.metadata?.insurance_provider || 'Not Specified' }}
              </span>
            </div>

            <div class="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-1 sm:col-span-2">
              <span class="text-[10px] text-zinc-500 uppercase block">Insurance Policy Number</span>
              <span class="text-zinc-100 font-semibold block text-sm">
                {{ contract.metadata?.policy_number || 'Not Specified' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 4: Document & Contract Vault -->
      <div v-if="activeTab === 'DOCUMENTS'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-800/80">
            <div>
              <h2 class="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <FileText class="w-4 h-4 text-zinc-400" />
                <span>Contract & Attachment Vault</span>
              </h2>
              <p class="text-xs text-zinc-400 mt-0.5">Lease agreements, transfer receipts, insurance cards, and payment slips</p>
            </div>
            <button
              @click="showUploadModal = true"
              type="button"
              class="self-start sm:self-auto px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              <UploadCloud class="w-3.5 h-3.5 text-zinc-950" />
              <span>Upload Document</span>
            </button>
          </div>

          <!-- Document List -->
          <div v-if="contract.attachments && contract.attachments.length > 0" class="divide-y divide-zinc-800/60 font-mono text-xs">
            <div
              v-for="att in contract.attachments"
              :key="att.id"
              class="py-3 flex items-center justify-between gap-3 hover:bg-zinc-900/40 px-2 rounded-lg transition-colors"
            >
              <div class="flex items-center gap-3 truncate">
                <div class="w-8 h-8 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-center shrink-0">
                  <FileText class="w-4 h-4 text-zinc-400" />
                </div>
                <div class="truncate">
                  <a
                    :href="att.drive_view_link || att.file_url || att.file"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="font-medium text-zinc-100 hover:text-white transition-colors truncate block text-xs"
                  >
                    {{ att.file_name }}
                  </a>
                  <div class="text-[10px] text-zinc-500 flex items-center gap-2 mt-0.5">
                    <span>{{ att.file_type }}</span>
                    <span>•</span>
                    <span>{{ formatFileSize(att.file_size) }}</span>
                    <span>•</span>
                    <span>{{ formatDate(att.uploaded_at) }}</span>
                  </div>
                </div>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <a
                  :href="att.drive_download_link || att.drive_view_link || att.file_url || att.file"
                  target="_blank"
                  download
                  class="p-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                  title="Download / Open File"
                >
                  <Download class="w-3.5 h-3.5" />
                </a>
                <button
                  @click="handleDeleteAttachment(att.id)"
                  type="button"
                  class="p-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-500 hover:text-rose-400 transition-colors"
                  title="Delete Document"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          <div v-else class="p-10 text-center text-xs font-mono text-zinc-500">
            No attachments or contracts uploaded yet. Click "Upload Document" to attach agreement PDFs or payment slips.
          </div>
        </div>
      </div>

      <!-- TAB 5: Payment History -->
      <div v-if="activeTab === 'HISTORY'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80">
            <div>
              <h2 class="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <History class="w-4 h-4 text-zinc-400" />
                <span>Historical Payment Ledger</span>
              </h2>
              <p class="text-xs text-zinc-400 mt-0.5">Chronological record of processed payments and bank slips</p>
            </div>
          </div>

          <div v-if="contract.payment_histories && contract.payment_histories.length > 0" class="overflow-x-auto">
            <table class="w-full text-left text-xs font-mono">
              <thead>
                <tr class="border-b border-zinc-800 text-zinc-500 uppercase text-[10px]">
                  <th class="py-2.5 px-3">Date</th>
                  <th class="py-2.5 px-3">Term #</th>
                  <th class="py-2.5 px-3 text-right">Paid Amount</th>
                  <th class="py-2.5 px-3">Notes</th>
                  <th class="py-2.5 px-3 text-right">Receipt / Slip</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/50">
                <tr v-for="pay in contract.payment_histories" :key="pay.id" class="hover:bg-zinc-900/40">
                  <td class="py-2.5 px-3 text-zinc-400">{{ formatDate(pay.paid_at) }}</td>
                  <td class="py-2.5 px-3 font-semibold text-zinc-200">#{{ pay.term_number || '-' }}</td>
                  <td class="py-2.5 px-3 text-right font-semibold text-zinc-100 tabular-nums">
                    {{ currencySymbol(contract.currency) }}{{ Number(pay.paid_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-2.5 px-3 text-zinc-400">{{ pay.note || '-' }}</td>
                  <td class="py-2.5 px-3 text-right">
                    <span v-if="pay.attachments && pay.attachments.length > 0" class="text-zinc-300">
                      <a :href="pay.attachments[0].file_url" target="_blank" class="hover:underline">View Slip</a>
                    </span>
                    <span v-else class="text-zinc-600">-</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else class="p-10 text-center text-xs font-mono text-zinc-500">
            No historical payments recorded yet. Click "Record Payment" to log an installment payment.
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <!-- Pay Modal -->
    <div
      v-if="showPayModalState"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
    >
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
        <div class="flex items-center justify-between pb-3 border-b border-zinc-800">
          <h3 class="text-sm font-semibold text-zinc-100 font-mono">Record Installment Payment</h3>
          <button @click="showPayModalState = false" class="text-zinc-500 hover:text-zinc-300">
            <X class="w-4 h-4" />
          </button>
        </div>

        <form @submit.prevent="handleProcessPayment" class="space-y-4 text-xs font-mono">
          <div class="space-y-1">
            <label class="text-zinc-400 block">Term Number</label>
            <input
              v-model.number="payForm.term_number"
              type="number"
              min="1"
              :max="totalTermsCount"
              required
              class="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-100 outline-none focus:border-zinc-500"
            />
          </div>

          <div class="space-y-1">
            <label class="text-zinc-400 block">Payment Amount</label>
            <input
              v-model.number="payForm.paid_amount"
              type="number"
              min="0.01"
              step="0.01"
              required
              class="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-100 outline-none focus:border-zinc-500"
            />
          </div>

          <div class="space-y-1">
            <div class="flex items-center justify-between">
              <label class="text-zinc-400 block">Deduct from Account</label>
              <span class="text-[10px] text-zinc-500">Ledger 2-Way Sync</span>
            </div>
            <select
              v-model="payForm.account_id"
              class="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-100 outline-none focus:border-zinc-500"
            >
              <option value="">-- No Account Link --</option>
              <option
                v-for="acc in ledgerStore.activeAccounts"
                :key="acc.id"
                :value="acc.id"
              >
                {{ acc.name }} ({{ acc.currency }} {{ Number(acc.current_balance).toLocaleString('en-US', { minimumFractionDigits: 2 }) }})
              </option>
            </select>
          </div>

          <div class="space-y-1">
            <label class="text-zinc-400 block">Note / Transaction Ref</label>
            <input
              v-model="payForm.note"
              type="text"
              placeholder="e.g. Bank transfer, Ref #992211"
              class="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-100 outline-none focus:border-zinc-500"
            />
          </div>

          <div class="space-y-1">
            <label class="text-zinc-400 block">Upload Transfer Slip (Optional)</label>
            <input
              type="file"
              accept="image/*,application/pdf"
              @change="handleSlipFileSelected"
              class="w-full text-zinc-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:bg-zinc-800 file:text-zinc-200 hover:file:bg-zinc-700"
            />
          </div>

          <div class="flex items-center justify-end gap-2 pt-3 border-t border-zinc-800">
            <button
              type="button"
              @click="showPayModalState = false"
              class="px-3 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isActionLoading"
              class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-semibold cursor-pointer disabled:opacity-50"
            >
              {{ isActionLoading ? 'Recording...' : 'Confirm Payment' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Upload Document Modal -->
    <div
      v-if="showUploadModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
    >
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
        <div class="flex items-center justify-between pb-3 border-b border-zinc-800">
          <h3 class="text-sm font-semibold text-zinc-100 font-mono">Upload Contract Document</h3>
          <button @click="showUploadModal = false" class="text-zinc-500 hover:text-zinc-300">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div v-if="!storageStore.isConnected" class="p-4 rounded-lg bg-zinc-900 border border-zinc-800 text-xs space-y-2 font-mono">
          <div class="flex items-center gap-2 text-zinc-300">
            <HardDrive class="w-4 h-4 text-zinc-400 shrink-0" />
            <span class="font-semibold">Google Drive Required</span>
          </div>
          <p class="text-zinc-400 text-xs font-sans leading-relaxed">
            All files are stored directly in your Google Drive under a Zero-Disk architecture. Please connect your Google Drive account first.
          </p>
          <router-link
            to="/settings"
            class="inline-flex items-center gap-1 text-xs text-zinc-100 hover:text-white underline font-medium pt-1"
          >
            Open Settings &rarr;
          </router-link>
        </div>

        <div v-else class="space-y-4 text-xs font-mono">
          <div class="space-y-1">
            <label class="text-zinc-400 block">Document Category</label>
            <select
              v-model="uploadCategory"
              class="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-100 outline-none focus:border-zinc-500"
            >
              <option value="CONTRACT">Loan / Lease Contract</option>
              <option value="STATEMENT">Billing Statement</option>
              <option value="SLIP">Payment Receipt / Slip</option>
              <option value="OTHER">Other Supporting Document</option>
            </select>
          </div>

          <div class="space-y-1">
            <label class="text-zinc-400 block">Select File (PDF or Image)</label>
            <input
              type="file"
              @change="handleDocumentFileSelected"
              class="w-full text-zinc-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:bg-zinc-800 file:text-zinc-200 hover:file:bg-zinc-700"
            />
          </div>

          <div v-if="storageStore.uploadProgress !== null" class="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
            <div
              class="bg-zinc-200 h-1 transition-all duration-150"
              :style="{ width: `${storageStore.uploadProgress}%` }"
            ></div>
          </div>

          <div class="flex items-center justify-end gap-2 pt-3 border-t border-zinc-800">
            <button
              type="button"
              @click="showUploadModal = false"
              class="px-3 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-300"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="handleUploadDocument"
              :disabled="!selectedDocumentFile || isActionLoading"
              class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-semibold cursor-pointer disabled:opacity-50"
            >
              {{ isActionLoading ? 'Uploading...' : 'Upload' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      :is-loading="confirmModal.isLoading"
      :error-message="confirmModal.errorMessage"
      @confirm="executeConfirmModal"
      @cancel="confirmModal.isOpen = false; confirmModal.errorMessage = ''"
    />
  </div>
</template>

<script setup lang="ts">
import { t } from '../../i18n'
import { currencySymbol } from '../../utils/currency'
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useInstallments, type InstallmentScheduleItem } from '../../composables/finance/useInstallments'
import { useLedgerStore } from '../../stores/ledger'
import { useStorageStore } from '../../stores/storage'
import { useToastStore } from '../../stores/toast'
import type { FinancialObligation } from '../../types/finance'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import {
  CreditCard,
  Table,
  Calculator,
  Car,
  FileText,
  History,
  UploadCloud,
  Download,
  Trash2,
  Scale,
  X,
  HardDrive
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const ledgerStore = useLedgerStore()
const storageStore = useStorageStore()

const {
  fetchInstallmentById,
  fetchSchedule,
  payInstallment,
  deleteInstallment,
  deleteAttachment,
  isActionLoading
} = useInstallments()

const contractId = computed(() => route.params.id as string)

const isLoading = ref(true)
const contract = ref<FinancialObligation | null>(null)
const scheduleItems = ref<InstallmentScheduleItem[]>([])

const activeTab = ref<'SCHEDULE' | 'SIMULATOR' | 'ASSET' | 'DOCUMENTS' | 'HISTORY'>('SCHEDULE')
const scheduleFilter = ref<'ALL' | 'UPCOMING' | 'PAID'>('ALL')

// Simulator state
const simTerm = ref<number>(0)

// Modal states
const showPayModalState = ref(false)
const payForm = ref({
  term_number: 1,
  paid_amount: 0,
  note: '',
  account_id: '',
  slip_file: undefined as File | undefined
})

const showUploadModal = ref(false)
const uploadCategory = ref('CONTRACT')
const selectedDocumentFile = ref<File | null>(null)

onMounted(async () => {
  await loadContractDetails()
})

async function loadContractDetails() {
  if (!contractId.value) return
  isLoading.value = true
  try {
    const [fetchedContract, scheduleRes] = await Promise.all([
      fetchInstallmentById(contractId.value),
      fetchSchedule(contractId.value)
    ])
    contract.value = fetchedContract
    scheduleItems.value = scheduleRes.schedule || []

    const currentTerm = Number(fetchedContract.metadata?.current_term || 0)
    simTerm.value = currentTerm
  } catch (err: any) {
    toast.error('Failed to load contract dossier')
    router.push('/finance/installments')
  } finally {
    isLoading.value = false
  }
}

const totalTermsCount = computed(() => {
  return Number(contract.value?.metadata?.total_terms || 1)
})

const currentTermCount = computed(() => {
  return Number(contract.value?.metadata?.current_term || 0)
})

const remainingTermsCount = computed(() => {
  return Math.max(0, totalTermsCount.value - currentTermCount.value)
})

const upcomingScheduleCount = computed(() => {
  return scheduleItems.value.filter(s => s.status !== 'PAID').length
})

const progressPct = computed(() => {
  if (totalTermsCount.value <= 0) return 0
  return Math.round((currentTermCount.value / totalTermsCount.value) * 100)
})

const filteredSchedule = computed(() => {
  if (scheduleFilter.value === 'UPCOMING') {
    return scheduleItems.value.filter(s => s.status !== 'PAID')
  }
  if (scheduleFilter.value === 'PAID') {
    return scheduleItems.value.filter(s => s.status === 'PAID')
  }
  return scheduleItems.value
})

function getTermStatusBadgeClass(status: string) {
  switch (status) {
    case 'PAID':
      return 'bg-zinc-900 text-zinc-300 border-zinc-800'
    case 'DUE':
      return 'bg-zinc-900 text-rose-400 border-zinc-800'
    default:
      return 'bg-zinc-950 text-zinc-500 border-zinc-900'
  }
}

function getTermStatusDotClass(status: string) {
  switch (status) {
    case 'PAID':
      return 'bg-emerald-400'
    case 'DUE':
      return 'bg-rose-400 animate-pulse'
    default:
      return 'bg-zinc-600'
  }
}

// OCPB Simulator Math
const simDiscountPct = computed(() => {
  const total = totalTermsCount.value
  const term = simTerm.value
  const ratio = total > 0 ? term / total : 0
  if (ratio <= 0.3334) return 60
  if (ratio <= 0.6667) return 70
  return 100
})

const simCalculation = computed(() => {
  const totalTerms = totalTermsCount.value
  const financed = Number(contract.value?.metadata?.financed_amount || contract.value?.metadata?.total_principal || 0)
  const flatRate = Number(contract.value?.metadata?.flat_rate_pa || 0)
  const remTerms = Math.max(0, totalTerms - simTerm.value)

  const years = totalTerms / 12
  const totalInterest = financed * (flatRate / 100) * years
  const monthlyPrincipal = totalTerms > 0 ? financed / totalTerms : 0
  const monthlyInterest = totalTerms > 0 ? totalInterest / totalTerms : 0

  const remainingPrincipal = monthlyPrincipal * remTerms
  const remainingInterestBefore = monthlyInterest * remTerms
  const discountPct = simDiscountPct.value
  const discountedInterest = remainingInterestBefore * (1 - discountPct / 100)
  const interestSaved = remainingInterestBefore - discountedInterest

  const vat = (remainingPrincipal + discountedInterest) * 0.07
  const payoffTotal = remainingPrincipal + discountedInterest + vat
  const regularRemainingTotal = remTerms * Number(contract.value?.amount || 0)
  const netSavings = Math.max(0, regularRemainingTotal - payoffTotal)

  return {
    remainingPrincipal,
    remainingInterestBefore,
    discountedInterest,
    interestSaved,
    vat,
    payoffTotal,
    regularRemainingTotal,
    netSavings
  }
})

function openPayModal() {
  const nextTerm = currentTermCount.value + 1
  payForm.value = {
    term_number: Math.min(totalTermsCount.value, nextTerm),
    paid_amount: Number(contract.value?.amount || 0),
    note: `Term #${nextTerm} installment payment`,
    account_id: '',
    slip_file: undefined
  }
  if (ledgerStore.accounts.length === 0) {
    ledgerStore.fetchAccounts().catch(() => {})
  }
  showPayModalState.value = true
}

function openPayModalForTerm(termNumber: number, amount: number) {
  payForm.value = {
    term_number: termNumber,
    paid_amount: amount,
    note: `Term #${termNumber} installment payment`,
    account_id: '',
    slip_file: undefined
  }
  if (ledgerStore.accounts.length === 0) {
    ledgerStore.fetchAccounts().catch(() => {})
  }
  showPayModalState.value = true
}

function handleSlipFileSelected(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    payForm.value.slip_file = target.files[0]
  }
}

async function handleProcessPayment() {
  if (!contract.value) return
  try {
    await payInstallment(contract.value.id, {
      paid_amount: payForm.value.paid_amount,
      term_number: payForm.value.term_number,
      note: payForm.value.note,
      slip_file: payForm.value.slip_file,
      account_id: payForm.value.account_id || undefined
    })
    if (payForm.value.account_id) {
      ledgerStore.fetchAccounts().catch(() => {})
      ledgerStore.fetchSummary().catch(() => {})
    }
    toast.success('Payment recorded successfully')
    showPayModalState.value = false
    await loadContractDetails()
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || 'Failed to record payment')
  }
}

function handleDocumentFileSelected(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    selectedDocumentFile.value = target.files[0]
  }
}

async function handleUploadDocument() {
  if (!contract.value || !selectedDocumentFile.value) return
  if (!storageStore.isConnected) {
    toast.error('Google Drive connection is required')
    return
  }
  try {
    // Zero-Disk Direct GDrive Upload
    await storageStore.uploadDirect(
      selectedDocumentFile.value,
      'finance',
      contract.value.id
    )
    toast.success('Document uploaded to Google Drive vault')
    showUploadModal.value = false
    selectedDocumentFile.value = null
    await loadContractDetails()
  } catch (err: any) {
    toast.error(err?.message || 'Failed to upload document')
  }
}

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  isLoading: false,
  errorMessage: '',
  action: async () => {}
})

async function executeConfirmModal() {
  confirmModal.isLoading = true
  confirmModal.errorMessage = ''
  try {
    await confirmModal.action()
    confirmModal.isOpen = false
  } catch (err: any) {
    confirmModal.errorMessage = err?.response?.data?.detail || err?.response?.data?.error || err?.message || 'Operation failed'
  } finally {
    confirmModal.isLoading = false
  }
}

function handleDeleteAttachment(attachmentId: string) {
  confirmModal.title = 'Delete Contract Document'
  confirmModal.message = 'Are you sure you want to permanently delete this document from your vault?'
  confirmModal.confirmText = 'Delete Document'
  confirmModal.isDanger = true
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    await deleteAttachment(attachmentId)
    toast.success('Document removed')
    await loadContractDetails()
  }
  confirmModal.isOpen = true
}

function confirmDelete() {
  if (!contract.value) return
  confirmModal.title = 'Delete Installment Contract'
  confirmModal.message = `Are you sure you want to delete contract "${contract.value.title}"? All amortization schedules and payment records will be removed.`
  confirmModal.confirmText = 'Delete Contract'
  confirmModal.isDanger = true
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    if (!contract.value) return
    await deleteInstallment(contract.value.id)
    toast.success('Contract deleted')
    router.push('/finance/installments')
  }
  confirmModal.isOpen = true
}

function formatDate(dateStr?: string) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

function formatFileSize(bytes?: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}
</script>
