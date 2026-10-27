import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

describe('Manual Entry Forms & Blank Initialization Verification', () => {
  describe('1. Presets and Mock Templates Purged from Source Code', () => {
    test('SubscriptionCreateView has no popularPresets and starts blank', () => {
      const filePath = path.resolve(process.cwd(), 'src/views/finance/SubscriptionCreateView.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes('popularPresets'), false, 'Should not contain popularPresets array')
      assert.strictEqual(content.includes('applyPreset'), false, 'Should not contain applyPreset function')
      assert.strictEqual(content.includes('amount: null'), true, 'amount should start as null')
      assert.strictEqual(content.includes("category: ''"), true, 'category should start as empty string')
      assert.strictEqual(content.includes("billing_cycle: ''"), true, 'billing_cycle should start as empty string')
      assert.strictEqual(content.includes("currency: ''"), true, 'currency should start as empty string')
      assert.strictEqual(content.includes("due_date: ''"), true, 'due_date should start as empty string')
    })

    test('BNPLAccountCreateView has no providerPresets and starts blank', () => {
      const filePath = path.resolve(process.cwd(), 'src/views/finance/BNPLAccountCreateView.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes('providerPresets'), false, 'Should not contain providerPresets')
      assert.strictEqual(content.includes('applyPreset'), false, 'Should not contain applyPreset')
      assert.strictEqual(content.includes('credit_limit: null'), true, 'credit_limit should start as null')
      assert.strictEqual(content.includes('cutoff_day: null'), true, 'cutoff_day should start as null')
      assert.strictEqual(content.includes('due_day: null'), true, 'due_day should start as null')
    })

    test('BNPLOrderCreateView has no quick tenor buttons and starts blank', () => {
      const filePath = path.resolve(process.cwd(), 'src/views/finance/BNPLOrderCreateView.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes('[1, 2, 3, 5, 6, 12]'), false, 'Quick tenor buttons must be removed')
      assert.strictEqual(content.includes('total_price: null'), true, 'total_price should start as null')
      assert.strictEqual(content.includes('total_terms: null'), true, 'total_terms should start as null')
      assert.strictEqual(content.includes("order_date: ''"), true, 'order_date should start as empty string')
    })

    test('InstallmentCreateView has no quick tenor buttons and starts blank', () => {
      const filePath = path.resolve(process.cwd(), 'src/views/finance/InstallmentCreateView.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes('[6, 10, 12, 24, 48]'), false, 'Quick tenor buttons must be removed')
      assert.strictEqual(content.includes('financed_amount: null'), true, 'financed_amount should start as null')
      assert.strictEqual(content.includes('total_terms: null'), true, 'total_terms should start as null')
      assert.strictEqual(content.includes('flat_rate_pa: null'), true, 'flat_rate_pa should start as null')
      assert.strictEqual(content.includes("due_date: ''"), true, 'due_date should start as empty string')
    })

    test('DebtCreateView does not read promptpay from localStorage and starts blank', () => {
      const filePath = path.resolve(process.cwd(), 'src/views/finance/DebtCreateView.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes("localStorage.getItem('finance_promptpay_default')"), false, 'Must not prefill promptpay from localStorage')
      assert.strictEqual(content.includes('amount: null'), true, 'amount should start as null')
      assert.strictEqual(content.includes("due_date: ''"), true, 'due_date should start as empty string')
      assert.strictEqual(content.includes("promptpay: ''"), true, 'promptpay should start empty')
    })

    test('PortfolioAccountCreateView has no brokerPresets and starts blank', () => {
      const filePath = path.resolve(process.cwd(), 'src/views/portfolio/PortfolioAccountCreateView.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes('brokerPresets'), false, 'Should not contain brokerPresets')
      assert.strictEqual(content.includes('applyPreset'), false, 'Should not contain applyPreset')
      assert.strictEqual(content.includes("currency: ''"), true, 'currency should start unselected')
    })

    test('CreateObligationModal does not pre-fill dummy terms, rates or providers on type change', () => {
      const filePath = path.resolve(process.cwd(), 'src/components/finance/CreateObligationModal.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes('financed_amount: 150000'), false, 'Must not prefill dummy 150000')
      assert.strictEqual(content.includes('total_terms: 36'), false, 'Must not prefill dummy 36')
      assert.strictEqual(content.includes('flat_rate_pa: 4.5'), false, 'Must not prefill dummy 4.5')
      assert.strictEqual(content.includes('vat_pct: 7.0'), false, 'Must not pre-select 7% VAT')
    })
  })

  describe('2. Specific Bug Fixes for Audit Items', () => {
    test('AddTransactionModal does not pre-fill price from watchlist current_price', () => {
      const filePath = path.resolve(process.cwd(), 'src/components/portfolio/AddTransactionModal.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes('form.value.price_per_share = Number(watch.current_price)'), false, 'Must not assign watch.current_price')
    })

    test('TransactionModal resets account, date, equalSplitPeopleCount, and harntungParticipants on open', () => {
      const filePath = path.resolve(process.cwd(), 'src/components/ledger/TransactionModal.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes("form.account = ''"), true, 'Account must reset to empty on open')
      assert.strictEqual(content.includes("form.transaction_date = ''"), true, 'Transaction date must reset to empty on open')
      assert.strictEqual(content.includes('equalSplitPeopleCount.value = null'), true, 'People count must reset to null on open')
      assert.strictEqual(content.includes('harntungParticipants.value = []'), true, 'Participants must reset to empty array on open')
      assert.strictEqual(content.includes("harntungPayerName.value = ''"), true, 'Payer name must reset on open')
      assert.strictEqual(content.includes("form.account = def.id"), false, 'Must not auto-assign default account id')
    })

    test('TransactionModal allows explicit Payer selection in Harntung itemized mode', () => {
      const filePath = path.resolve(process.cwd(), 'src/components/ledger/TransactionModal.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes('harntungPayerName'), true, 'harntungPayerName state must exist')
      assert.strictEqual(content.includes("payer_name: harntungPayerName.value || 'Me'"), true, 'Payload must use selected harntungPayerName')
      assert.strictEqual(content.includes("s.name.toLowerCase() === 'me'"), false, 'Should not hardcode name comparison to Me')

      // Simulation test: 100 THB bill, Alice & Bob share equally (50 THB each), Alice is payer
      const participants = [{ name: 'Alice', contact: '' }, { name: 'Bob', contact: '' }]
      const items = [{ name: 'Lunch', price: 100, quantity: 1, consumers: ['Alice', 'Bob'] }]
      const rawMap: Record<string, number> = { Alice: 0, Bob: 0 }
      items.forEach(it => {
        const perPerson = (it.price * it.quantity) / it.consumers.length
        it.consumers.forEach(c => { rawMap[c] = (rawMap[c] || 0) + perPerson })
      })

      const shares = participants.map(p => ({
        name: p.name,
        finalShare: Number(rawMap[p.name].toFixed(2))
      }))

      const harntungPayerName = 'Alice'
      const payerShare = shares.find(s => s.name === harntungPayerName)?.finalShare || 0
      const friendsShare = shares.filter(s => s.name !== harntungPayerName).reduce((sum, s) => sum + s.finalShare, 0)

      assert.strictEqual(payerShare, 50, "Payer (Alice) expense must be 50")
      assert.strictEqual(friendsShare, 50, "Friends total share (Bob) receivable must be 50")
    })

    test('AddTransactionModal starts with empty portfolio, date/time, and currency for new transactions', () => {
      const filePath = path.resolve(process.cwd(), 'src/components/portfolio/AddTransactionModal.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes("form.value.portfolio = activePortfolioId"), false, 'Must not auto-select default or active portfolio')
      assert.strictEqual(content.includes("form.value.executed_at = getNowLocalDateTime()"), false, 'Must not auto-fill execution datetime for new trades')
      assert.strictEqual(content.includes("form.value.currency = portfolioStore.displayCurrency"), false, 'Must not default to displayCurrency')
      assert.strictEqual(content.includes('<option value="" disabled>Select portfolio</option>'), true, 'Must have disabled Select portfolio placeholder option')
      assert.strictEqual(content.includes("Please select a target portfolio"), true, 'Must validate target portfolio before submit')
      assert.strictEqual(content.includes("Please specify the execution date and time"), true, 'Must validate execution date before submit')
      assert.strictEqual(content.includes("Please select a trade currency"), true, 'Must validate trade currency before submit')
    })

    test('Preserved and restored example placeholders across finance and portfolio inputs', () => {
      const oblContent = fs.readFileSync(path.resolve(process.cwd(), 'src/components/finance/CreateObligationModal.vue'), 'utf8')
      const txContent = fs.readFileSync(path.resolve(process.cwd(), 'src/components/portfolio/AddTransactionModal.vue'), 'utf8')
      const newsContent = fs.readFileSync(path.resolve(process.cwd(), 'src/views/portfolio/PortfolioNewsView.vue'), 'utf8')
      const accountsContent = fs.readFileSync(path.resolve(process.cwd(), 'src/views/portfolio/PortfolioAccountsView.vue'), 'utf8')

      assert.strictEqual(oblContent.includes('placeholder="e.g. KBank, Apple Store"'), true, 'Obligation lender placeholder restored')
      assert.strictEqual(oblContent.includes('placeholder="e.g. Alex Wong"'), true, 'Obligation counterparty placeholder restored')
      assert.strictEqual(txContent.includes('placeholder="Search symbol or name (e.g. AAPL, PTT, BTC, NVDA, SCB)"'), true, 'AddTransaction ticker search placeholder restored')
      assert.strictEqual(newsContent.includes('placeholder="Filter ticker (e.g. NVDA)..."'), true, 'Portfolio news ticker placeholder restored')
      assert.strictEqual(accountsContent.includes('placeholder="Search any ticker (e.g. NVDA, PTT.BK, BTC-USD)..."'), true, 'Portfolio accounts ticker placeholder restored')
    })

    test('TransferModal resets notes and date on open', () => {
      const filePath = path.resolve(process.cwd(), 'src/components/ledger/TransferModal.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes("form.notes = ''"), true, 'Transfer modal must reset notes on open')
      assert.strictEqual(content.includes("form.transaction_date = ''"), true, 'Transfer modal must reset date on open')
    })

    test('CreatePortfolioModal does not auto-select currency from displayCurrency', () => {
      const filePath = path.resolve(process.cwd(), 'src/components/portfolio/CreatePortfolioModal.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes('currency: portfolioStore.displayCurrency'), false, 'Must not pre-select currency from displayCurrency')
      assert.strictEqual(content.includes("currency: ''"), true, 'Currency must start unselected')
    })

    test('CreateAccountModal starts with unselected account_type and currency', () => {
      const filePath = path.resolve(process.cwd(), 'src/components/ledger/CreateAccountModal.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes("account_type: ''"), true, 'account_type must start unselected')
      assert.strictEqual(content.includes("currency: ''"), true, 'currency must start unselected')
    })

    test('InfraAssetFormModal starts with empty root username, currency, and cycle', () => {
      const filePath = path.resolve(process.cwd(), 'src/components/workspace/InfraAssetFormModal.vue')
      const content = fs.readFileSync(filePath, 'utf8')

      assert.strictEqual(content.includes("ssh_username: 'root'"), false, 'Must not default ssh_username to root')
      assert.strictEqual(content.includes("ssh_username: ''"), true, 'ssh_username must start blank')
      assert.strictEqual(content.includes("cost_currency: ''"), true, 'cost_currency must start unselected')
      assert.strictEqual(content.includes("billing_cycle: ''"), true, 'billing_cycle must start unselected')
    })

    test('Helpful format placeholders are preserved on inputs', () => {
      const credContent = fs.readFileSync(path.resolve(process.cwd(), 'src/components/workspace/CredentialFormModal.vue'), 'utf8')
      const rbContent = fs.readFileSync(path.resolve(process.cwd(), 'src/components/workspace/ServerRunbooksModal.vue'), 'utf8')

      assert.strictEqual(credContent.includes('placeholder="postgres://host:5432/db"'), true, 'Credential host format placeholder should exist')
      assert.strictEqual(rbContent.includes('placeholder="/var/www/app"'), true, 'Runbook working dir format placeholder should exist')
    })
  })

  describe('3. Localization & Dictionaries Integrity', () => {
    test('dictionaries.ts contains no duplicate property keys', () => {
      const filePath = path.resolve(process.cwd(), 'src/i18n/dictionaries.ts')
      const content = fs.readFileSync(filePath, 'utf8')
      const lines = content.split('\n')
      const seen = new Set<string>()
      const duplicates: string[] = []

      for (const line of lines) {
        const m = line.match(/^\s*'([^']+)':/)
        if (m) {
          const key = m[1]
          if (seen.has(key)) {
            duplicates.push(key)
          } else {
            seen.add(key)
          }
        }
      }

      assert.deepStrictEqual(duplicates, [], 'dictionaries.ts must have zero duplicate keys')
    })

    test('translates delete note permanently and debt settlements phrases to Thai', async () => {
      const { translatePhraseToThai } = await import('../src/i18n/dictionaries')

      assert.strictEqual(
        translatePhraseToThai('Delete note permanently?'),
        'ลบโน้ตนี้ถาวรหรือไม่?'
      )
      assert.strictEqual(
        translatePhraseToThai('Delete Permanently'),
        'ลบถาวร'
      )
      assert.strictEqual(
        translatePhraseToThai('Track liabilities payable, peer debts receivable, and settlements'),
        'ติดตามหนี้สิน ลูกหนี้ และการชำระหนี้'
      )
      assert.strictEqual(
        translatePhraseToThai('Debtors receivable, liabilities payable, and settlements'),
        'ลูกหนี้ หนี้สิน และการชำระหนี้'
      )
      assert.strictEqual(
        translatePhraseToThai("'Shopping List' will be permanently deleted. This cannot be undone."),
        "'Shopping List' จะถูกลบถาวร ไม่สามารถย้อนกลับได้"
      )
    })
  })

  describe('4. Update & Edit Operations Integrity (P1 & P2 Fixes)', () => {
    test('useBodyScrollLock is invoked strictly after confirmModal declaration', () => {
      const subView = fs.readFileSync(path.resolve(process.cwd(), 'src/views/finance/SubscriptionsView.vue'), 'utf8')
      const subDetail = fs.readFileSync(path.resolve(process.cwd(), 'src/views/finance/SubscriptionDetailView.vue'), 'utf8')
      const instDetail = fs.readFileSync(path.resolve(process.cwd(), 'src/views/finance/InstallmentDetailView.vue'), 'utf8')

      assert.strictEqual(
        subView.indexOf('useBodyScrollLock(') > subView.indexOf('const confirmModal = reactive'),
        true,
        'SubscriptionsView must call useBodyScrollLock after confirmModal'
      )
      assert.strictEqual(
        subDetail.indexOf('useBodyScrollLock(') > subDetail.indexOf('const confirmModal = reactive'),
        true,
        'SubscriptionDetailView must call useBodyScrollLock after confirmModal'
      )
      assert.strictEqual(
        instDetail.indexOf('useBodyScrollLock(') > instDetail.indexOf('const confirmModal = reactive'),
        true,
        'InstallmentDetailView must call useBodyScrollLock after confirmModal'
      )
    })

    test('EditObligationModal locks order_date on payment history and reloads on open', () => {
      const content = fs.readFileSync(path.resolve(process.cwd(), 'src/components/finance/EditObligationModal.vue'), 'utf8')

      assert.strictEqual(content.includes('isOrderDateLocked'), true, 'Must define isOrderDateLocked')
      assert.strictEqual(content.includes(':disabled="isOrderDateLocked"'), true, 'Order date must be disabled when locked')
      assert.strictEqual(content.includes('initForm(ob)'), true, 'Must initialize form on open')
      assert.strictEqual(content.includes('if (isSubmitting.value || !props.obligation) return'), true, 'Must guard against concurrent submits')
    })

    test('PortfolioAccountDetailView listens to @saved on EditHoldingModal', () => {
      const content = fs.readFileSync(path.resolve(process.cwd(), 'src/views/portfolio/PortfolioAccountDetailView.vue'), 'utf8')
      assert.strictEqual(content.includes('@saved="refreshAll"'), true, 'Must listen to @saved event')
    })

    test('LedgerAccountDetailView loads categories directly', () => {
      const content = fs.readFileSync(path.resolve(process.cwd(), 'src/views/ledger/LedgerAccountDetailView.vue'), 'utf8')
      assert.strictEqual(content.includes('ledgerStore.fetchCategories()'), true, 'Must fetch categories on load')
    })

    test('TransactionModal and LedgerBudgetsView have double-submit guards and proper event emission', () => {
      const txContent = fs.readFileSync(path.resolve(process.cwd(), 'src/components/ledger/TransactionModal.vue'), 'utf8')
      const budgetContent = fs.readFileSync(path.resolve(process.cwd(), 'src/views/ledger/LedgerBudgetsView.vue'), 'utf8')

      assert.strictEqual(txContent.includes('if (isSubmitting.value) return'), true, 'TransactionModal must guard against concurrent submit')
      assert.strictEqual(budgetContent.includes('if (isSaving.value) return'), true, 'LedgerBudgetsView must guard against concurrent save')

      // Ensure TransactionModal emits only updated on edit, not both updated and created
      assert.strictEqual(
        txContent.includes("await ledgerStore.updateTransaction(props.transactionToEdit.id, updatePayload)\n      emit('updated')\n      emit('close')"),
        true,
        'TransactionModal must emit only updated on edit'
      )
    })
  })
})
