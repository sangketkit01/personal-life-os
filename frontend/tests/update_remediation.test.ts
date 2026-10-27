import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

describe('Update Operations Remediation Verification', () => {
  const readComponent = (relPath: string) => {
    const rootDir = process.cwd().endsWith('frontend') ? process.cwd() : path.join(process.cwd(), 'frontend')
    const filePath = path.resolve(rootDir, relPath)
    return fs.readFileSync(filePath, 'utf8')
  }

  test('Item 1: Debt principal locking & metadata sanity in EditObligationModal.vue', () => {
    const editModal = readComponent('src/components/finance/EditObligationModal.vue')
    assert.match(editModal, /isDebtWithPaymentsOrSplit/)
    assert.match(editModal, /debtLockReason/)
    assert.match(editModal, /delete updatedMeta\.remaining_balance/)
    assert.match(editModal, /delete updatedMeta\.total_paid/)
  })

  test('Item 3: Holding currency locked when trade history exists in EditHoldingModal.vue', () => {
    const editHolding = readComponent('src/components/portfolio/EditHoldingModal.vue')
    assert.match(editHolding, /isCurrencyLocked/)
    assert.match(editHolding, /:disabled="isCurrencyLocked"/)
    assert.match(editHolding, /Currency is locked because trade history already exists/)
  })

  test('Item 6: Workspace SSOT lock for MA and Infra in EditObligationModal.vue', () => {
    const editModal = readComponent('src/components/finance/EditObligationModal.vue')
    assert.match(editModal, /isWorkspaceMirroredObligation/)
    assert.match(editModal, /Managed by Workspace/)
    assert.match(editModal, /workspaceLink/)
  })

  test('Item 7: Atomic Move + Edit Holding in EditHoldingModal.vue without separate moveHolding call', () => {
    const editHolding = readComponent('src/components/portfolio/EditHoldingModal.vue')
    // Ensure we do NOT call moveHolding separately before updateHolding
    assert.doesNotMatch(editHolding, /portfolioStore\.moveHolding/)
    assert.match(editHolding, /updateHolding\(props\.holding\.id, payload\)/)
  })

  test('Item 8: Transaction context (portfolio_id) & holdings preload in Portfolio views', () => {
    const detailView = readComponent('src/views/portfolio/PortfolioAccountDetailView.vue')
    assert.match(detailView, /t\.portfolio_id \|\| t\.portfolio/)
    assert.match(detailView, /portfolioStore\.fetchHoldings/)

    const addModal = readComponent('src/components/portfolio/AddTransactionModal.vue')
    assert.match(addModal, /props\.editingTransaction\?\.holding/)
  })

  test('Item 10: Free Trial payment method and linked_card synchronized on submit', () => {
    const editModal = readComponent('src/components/finance/EditObligationModal.vue')
    assert.match(editModal, /updatedMeta\.payment_method = pm/)
    assert.match(editModal, /updatedMeta\.linked_card = pm/)
  })

  test('Item 11: Paired transfer date lock in TransactionModal.vue', () => {
    const txModal = readComponent('src/components/ledger/TransactionModal.vue')
    assert.match(txModal, /isDateLocked/)
    assert.match(txModal, /Transfer date is locked to keep both accounts in sync/)
  })
})
