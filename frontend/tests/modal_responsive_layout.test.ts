import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

describe('Modal Responsive Layout & UX Audit Verification', () => {
  const readComponent = (relPath: string) => {
    const rootDir = process.cwd().endsWith('frontend') ? process.cwd() : path.join(process.cwd(), 'frontend')
    const filePath = path.resolve(rootDir, relPath)
    return fs.readFileSync(filePath, 'utf8')
  }

  describe('1. Standard Modal Architecture (Viewport Clamping, Fixed Header, Scrollable Body, Pinned Footer)', () => {
    test('Finance modals have viewport clamping and overscroll containment', () => {
      const createObligation = readComponent('src/components/finance/CreateObligationModal.vue')
      assert.match(createObligation, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(createObligation, /overscroll-contain/)
      assert.match(createObligation, /shrink-0.*bg-zinc-950/)

      const editObligation = readComponent('src/components/finance/EditObligationModal.vue')
      assert.match(editObligation, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(editObligation, /overscroll-contain/)
      assert.match(editObligation, /shrink-0.*bg-zinc-950/)

      const payModal = readComponent('src/components/finance/PayModal.vue')
      assert.match(payModal, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(payModal, /border-t.*shrink-0|shrink-0.*border-t/)

      const paymentHistoryModal = readComponent('src/components/finance/PaymentHistoryModal.vue')
      assert.match(paymentHistoryModal, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(paymentHistoryModal, /border-t.*shrink-0|shrink-0.*border-t/)

      const inflowBreakdown = readComponent('src/components/finance/overview/ExpectedInflowBreakdownModal.vue')
      assert.match(inflowBreakdown, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(inflowBreakdown, /overscroll-contain/)
    })

    test('Inline Finance modals in SubscriptionDetailView and InstallmentDetailView are viewport clamped', () => {
      const subDetail = readComponent('src/views/finance/SubscriptionDetailView.vue')
      assert.match(subDetail, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(subDetail, /shrink-0.*bg-zinc-950/)

      const instDetail = readComponent('src/views/finance/InstallmentDetailView.vue')
      assert.match(instDetail, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(instDetail, /shrink-0.*bg-zinc-950/)
    })

    test('Ledger modals have viewport clamping, fixed header, scrollable body, pinned footer', () => {
      const txModal = readComponent('src/components/ledger/TransactionModal.vue')
      assert.match(txModal, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(txModal, /overscroll-contain/)
      assert.match(txModal, /shrink-0.*border-t/)

      const transferModal = readComponent('src/components/ledger/TransferModal.vue')
      assert.match(transferModal, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(transferModal, /shrink-0.*border-t/)

      const createAccount = readComponent('src/components/ledger/CreateAccountModal.vue')
      assert.match(createAccount, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(createAccount, /shrink-0.*border-t/)

      const settleSplit = readComponent('src/components/ledger/SettleSplitModal.vue')
      assert.match(settleSplit, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(settleSplit, /shrink-0.*border-t/)

      const budgetsView = readComponent('src/views/ledger/LedgerBudgetsView.vue')
      assert.match(budgetsView, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(budgetsView, /shrink-0.*border-t/)
    })

    test('Portfolio modals have viewport clamping, scrollable body, pinned footer', () => {
      const addTx = readComponent('src/components/portfolio/AddTransactionModal.vue')
      assert.match(addTx, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(addTx, /shrink-0.*border-t/)

      const editHolding = readComponent('src/components/portfolio/EditHoldingModal.vue')
      assert.match(editHolding, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(editHolding, /shrink-0.*border-t/)

      const moveHolding = readComponent('src/components/portfolio/MoveHoldingModal.vue')
      assert.match(moveHolding, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(moveHolding, /shrink-0.*border-t/)

      const createPort = readComponent('src/components/portfolio/CreatePortfolioModal.vue')
      assert.match(createPort, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(createPort, /shrink-0.*border-t/)

      const editPort = readComponent('src/components/portfolio/EditPortfolioModal.vue')
      assert.match(editPort, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(editPort, /shrink-0.*border-t/)
    })

    test('Workspace modals have viewport clamping and overscroll containment', () => {
      const infraAsset = readComponent('src/components/workspace/InfraAssetFormModal.vue')
      assert.match(infraAsset, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(infraAsset, /overscroll-contain/)
      assert.match(infraAsset, /border-t.*shrink-0|shrink-0.*border-t/)

      const credForm = readComponent('src/components/workspace/CredentialFormModal.vue')
      assert.match(credForm, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(credForm, /overscroll-contain/)
      assert.match(credForm, /border-t.*shrink-0|shrink-0.*border-t/)

      const maBilling = readComponent('src/components/workspace/MaBillingEditModal.vue')
      assert.match(maBilling, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(maBilling, /overscroll-contain/)
      assert.match(maBilling, /border-t.*shrink-0|shrink-0.*border-t/)

      const runbooks = readComponent('src/components/workspace/ServerRunbooksModal.vue')
      assert.match(runbooks, /max-h-\[calc\(100dvh-1rem\)\]/)
      assert.match(runbooks, /overscroll-contain/)
    })
  })

  describe('2. TransactionModal Split Bill Responsive Layout (Requirement 3)', () => {
    test('Split Bill dishes use 2-row layout on mobile and inline on desktop', () => {
      const content = readComponent('src/components/ledger/TransactionModal.vue')
      // Row 1: Dish name full-width on mobile, flex-1 on desktop
      assert.match(content, /w-full sm:flex-1/, 'Dish name input must be full width on mobile and flex-1 on desktop')
      // Row 2: Price, Quantity, Delete button container
      assert.match(content, /flex items-center gap-2 w-full sm:w-auto shrink-0/, 'Controls must be in a responsive flex row')
      // Preserved calculations and custom payer selector
      assert.match(content, /harntungPayerName/, 'Must preserve custom split payer selection')
      assert.match(content, /harntungCalculatedShares/, 'Must preserve harntung calculated shares')
    })

    test('Split Bill participant pills and consumer chips do not get clipped', () => {
      const content = readComponent('src/components/ledger/TransactionModal.vue')
      assert.match(content, /flex flex-wrap items-center gap-2/, 'Participant pills container must wrap')
      assert.match(content, /max-w-full truncate/, 'Consumer chips must truncate without overflowing')
    })
  })

  describe('3. ImageCropperModal Dynamic Viewport & Proportional Crop Scaling (Requirement 4)', () => {
    test('ImageCropperModal tracks window resize and scales crop box proportionally', () => {
      const content = readComponent('src/components/workspace/ImageCropperModal.vue')
      // Viewport tracking refs
      assert.match(content, /const windowWidth = ref\(typeof window !== 'undefined' \? window\.innerWidth : 1024\)/)
      assert.match(content, /const windowHeight = ref\(typeof window !== 'undefined' \? window\.innerHeight : 800\)/)
      // Event listeners for resize and orientationchange
      assert.match(content, /window\.addEventListener\('resize', updateViewport\)/)
      assert.match(content, /window\.addEventListener\('orientationchange', updateViewport\)/)
      assert.match(content, /window\.removeEventListener\('resize', updateViewport\)/)
      assert.match(content, /window\.removeEventListener\('orientationchange', updateViewport\)/)
      // Dynamic max dimensions
      assert.match(content, /Math\.min\(640, Math\.max\(200, windowWidth\.value - 64\)\)/)
      // Proportional crop scaling watcher
      assert.match(content, /crop\.x = Math\.round\(crop\.x \* rx\)/)
      assert.match(content, /crop\.y = Math\.round\(crop\.y \* ry\)/)
      assert.match(content, /crop\.w = Math\.round\(crop\.w \* rx\)/)
      assert.match(content, /crop\.h = Math\.round\(crop\.h \* ry\)/)
    })
  })

  describe('4. SshTerminalModal Mobile Responsiveness (Requirement 5)', () => {
    test('Runbook sidebar collapses on mobile by default and auto-fits terminal', () => {
      const content = readComponent('src/components/workspace/SshTerminalModal.vue')
      // Defaults to false on mobile < 768px
      assert.match(content, /showRunbookBar = ref\(typeof window !== 'undefined' \? window\.innerWidth >= 768 : true\)/)
      // Truncate host/username in header
      assert.match(content, /truncate min-w-0/)
      // Mobile close button in runbook sidebar
      assert.match(content, /@click="showRunbookBar = false"/)
      // fitAddon refit on window resize/orientationchange
      assert.match(content, /function handleWindowResize\(\) {[\s\S]*?fitAddon\?\.fit\(\)/)
      assert.match(content, /window\.addEventListener\('resize', handleWindowResize\)/)
      assert.match(content, /window\.addEventListener\('orientationchange', handleWindowResize\)/)
      assert.match(content, /window\.removeEventListener\('resize', handleWindowResize\)/)
      assert.match(content, /window\.removeEventListener\('orientationchange', handleWindowResize\)/)
    })
  })

  describe('5. ConfirmModal Teleport & Event Isolation (Requirement 6)', () => {
    test('ConfirmModal is teleported to body, has z-[80], and isolates escape keydown', () => {
      const content = readComponent('src/components/common/ConfirmModal.vue')
      assert.match(content, /<Teleport to="body">/)
      assert.match(content, /z-\[80\]/)
      assert.match(content, /event\.stopPropagation\(\)/, 'Escape keydown must call stopPropagation() to prevent closing parent modal')
      assert.match(content, /event\.stopImmediatePropagation\(\)/, 'Must call stopImmediatePropagation()')
      assert.match(content, /window\.addEventListener\('keydown', handleKeydown, true\)/, 'Must listen in capture phase')
      assert.match(content, /max-h-\[calc\(100dvh-1rem\)\]/)
    })

    test('TaskSidePeekDrawer and CalendarEventModal guard handleEscape against child modals', () => {
      const drawer = readComponent('src/components/workspace/TaskSidePeekDrawer.vue')
      assert.match(drawer, /showDeleteConfirm\.value \|\| attachmentToDelete\.value \|\| attachmentPreview\.open/, 'Must guard drawer against closing when child confirm modal is open')

      const calendar = readComponent('src/components/workspace/CalendarEventModal.vue')
      assert.match(calendar, /if \(showDeleteConfirm\.value\) return/, 'Must guard calendar modal against closing when confirm modal is open')
    })
  })

  describe('6. Body and Root Scroll Lock Mechanism', () => {
    test('useBodyScrollLock composable source implements full body and root lock with reference counting', () => {
      const content = readComponent('src/composables/useBodyScrollLock.ts')
      assert.match(content, /document\.body\.style\.overflow = 'hidden'/, 'Must lock body style')
      assert.match(content, /document\.documentElement\.style\.overflow = 'hidden'/, 'Must lock documentElement style')
      assert.match(content, /document\.body\.classList\.add\('overflow-hidden'\)/, 'Must add overflow-hidden class to body')
      assert.match(content, /document\.documentElement\.classList\.add\('overflow-hidden'\)/, 'Must add overflow-hidden class to root')
      assert.match(content, /activeLockCount/, 'Must track lock count for nested modals')
      assert.match(content, /unlockBodyScroll/, 'Must export unlockBodyScroll')
      assert.match(content, /onBeforeUnmount/, 'Must clean up on unmount')
    })

    test('TransferModal and key modals integrate useBodyScrollLock', () => {
      const transferModal = readComponent('src/components/ledger/TransferModal.vue')
      assert.match(transferModal, /useBodyScrollLock/, 'TransferModal must integrate useBodyScrollLock')
      assert.match(transferModal, /useBodyScrollLock\(\(\) => props\.isOpen\)/)

      const confirmModal = readComponent('src/components/common/ConfirmModal.vue')
      assert.match(confirmModal, /useBodyScrollLock/, 'ConfirmModal must integrate useBodyScrollLock')

      const taskDrawer = readComponent('src/components/workspace/TaskSidePeekDrawer.vue')
      assert.match(taskDrawer, /useBodyScrollLock/, 'TaskSidePeekDrawer must integrate useBodyScrollLock')

      const txModal = readComponent('src/components/ledger/TransactionModal.vue')
      assert.match(txModal, /useBodyScrollLock/, 'TransactionModal must integrate useBodyScrollLock')

      // Ensure useBodyScrollLock is positioned AFTER variable declarations to avoid TDZ ReferenceError
      const infraTab = readComponent('src/components/workspace/ProjectInfrastructureTab.vue')
      const linkModalIdx = infraTab.indexOf('const linkModal =')
      const infraLockIdx = infraTab.indexOf('useBodyScrollLock(() => logsViewer.open || linkModal.open)')
      assert.strictEqual(linkModalIdx !== -1 && infraLockIdx > linkModalIdx, true, 'useBodyScrollLock in ProjectInfrastructureTab must be after linkModal declaration')

      const projectDetail = readComponent('src/views/workspace/WorkspaceProjectDetailView.vue')
      const showLinkModalIdx = projectDetail.indexOf('const showLinkModal =')
      const detailLockIdx = projectDetail.indexOf('useBodyScrollLock(() => showProjectModal.value || showLinkModal.value)')
      assert.strictEqual(showLinkModalIdx !== -1 && detailLockIdx > showLinkModalIdx, true, 'useBodyScrollLock in WorkspaceProjectDetailView must be after showLinkModal declaration')
    })
  })
})
