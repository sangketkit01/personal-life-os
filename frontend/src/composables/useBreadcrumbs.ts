import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { t } from '../i18n'

export interface BreadcrumbItem {
  label: string
  to?: string
}

export function useBreadcrumbs() {
  const route = useRoute()

  const breadcrumbs = computed<BreadcrumbItem[]>(() => {
    const path = route.path
    const name = String(route.name || '')
    const params = route.params
    const query = route.query

    const homeItem: BreadcrumbItem = { label: t('crumb.home'), to: '/' }

    // 1. Root Overview (Home) - current page, not a link
    if (path === '/' || name === 'overview') {
      return [{ label: t('crumb.home') }]
    }

    // 2. Direct Home-level standalone pages: Notes & Settings
    if (path === '/notes' || path.startsWith('/notes/') || name === 'notes') {
      return [
        homeItem,
        { label: t('nav.notes') }
      ]
    }

    if (path === '/settings' || path.startsWith('/settings/') || name === 'settings') {
      return [
        homeItem,
        { label: t('nav.settings') }
      ]
    }

    if (path.startsWith('/auth/google/callback') || name === 'google-auth-callback') {
      return [
        homeItem,
        { label: t('nav.settings'), to: '/settings' },
        { label: 'Google Drive Auth' }
      ]
    }

    // 3. Finance Domain (Main destination: /finance/overview)
    if (path.startsWith('/finance') || name.startsWith('finance-')) {
      const financeDomainItem: BreadcrumbItem = { label: t('crumb.finance'), to: '/finance/overview' }

      // Finance Overview itself
      if (path === '/finance/overview' || name === 'finance-overview' || path === '/finance') {
        return [
          homeItem,
          { label: t('crumb.finance') }
        ]
      }

      // Installments & Contracts
      if (path.startsWith('/finance/installments') || name.startsWith('finance-installments')) {
        const installmentsParent: BreadcrumbItem = { label: t('crumb.installments'), to: '/finance/installments' }
        if (name === 'finance-installments-new' || path === '/finance/installments/new') {
          return [
            homeItem,
            financeDomainItem,
            installmentsParent,
            { label: t('crumb.newContract') }
          ]
        }
        if (name === 'finance-installments-detail' || (params.id && path.startsWith('/finance/installments/'))) {
          return [
            homeItem,
            financeDomainItem,
            installmentsParent,
            { label: t('crumb.contractDossier') }
          ]
        }
        return [
          homeItem,
          financeDomainItem,
          { label: t('crumb.installments') }
        ]
      }

      // BNPL (Shopping Credit)
      if (path.startsWith('/finance/bnpl') || name.startsWith('finance-bnpl')) {
        const bnplParent: BreadcrumbItem = { label: t('crumb.bnpl'), to: '/finance/bnpl' }
        if (name === 'finance-bnpl-new' || path === '/finance/bnpl/new') {
          return [
            homeItem,
            financeDomainItem,
            bnplParent,
            { label: t('crumb.newCredit') }
          ]
        }
        if (name === 'finance-bnpl-new-order' || path.endsWith('/new-order')) {
          const accountId = String(params.id || '')
          return [
            homeItem,
            financeDomainItem,
            bnplParent,
            { label: t('crumb.bnplAccount'), to: `/finance/bnpl/${accountId}` },
            { label: t('crumb.newOrder') }
          ]
        }
        if (name === 'finance-bnpl-detail' || (params.id && path.startsWith('/finance/bnpl/'))) {
          return [
            homeItem,
            financeDomainItem,
            bnplParent,
            { label: t('crumb.accountDossier') }
          ]
        }
        return [
          homeItem,
          financeDomainItem,
          { label: t('crumb.bnpl') }
        ]
      }

      // Subscriptions
      if (path.startsWith('/finance/subscriptions') || name.startsWith('finance-subscriptions')) {
        const subsParent: BreadcrumbItem = { label: t('crumb.subscriptions'), to: '/finance/subscriptions' }
        if (name === 'finance-subscriptions-new' || path === '/finance/subscriptions/new') {
          return [
            homeItem,
            financeDomainItem,
            subsParent,
            { label: t('crumb.newSubscription') }
          ]
        }
        if (name === 'finance-subscriptions-detail' || (params.id && path.startsWith('/finance/subscriptions/'))) {
          return [
            homeItem,
            financeDomainItem,
            subsParent,
            { label: t('crumb.subscriptionDossier') }
          ]
        }
        return [
          homeItem,
          financeDomainItem,
          { label: t('crumb.subscriptions') }
        ]
      }

      // Debts
      if (path.startsWith('/finance/debts') || name.startsWith('finance-debts')) {
        const debtsParent: BreadcrumbItem = { label: t('crumb.debts'), to: '/finance/debts' }
        if (name === 'finance-debts-new' || path === '/finance/debts/new') {
          return [
            homeItem,
            financeDomainItem,
            debtsParent,
            { label: t('crumb.newDebt') }
          ]
        }
        if (name === 'finance-debts-detail' || (params.id && path.startsWith('/finance/debts/'))) {
          return [
            homeItem,
            financeDomainItem,
            debtsParent,
            { label: t('crumb.debtDossier') }
          ]
        }
        return [
          homeItem,
          financeDomainItem,
          { label: t('crumb.debts') }
        ]
      }
    }

    // 4. Portfolio Domain (Main destination: /portfolio/overview)
    if (path.startsWith('/portfolio') || name.startsWith('portfolio-')) {
      const portfolioDomainItem: BreadcrumbItem = { label: t('crumb.portfolio'), to: '/portfolio/overview' }

      if (path === '/portfolio/overview' || name === 'portfolio-overview' || path === '/portfolio') {
        return [
          homeItem,
          { label: t('crumb.portfolio') }
        ]
      }

      // Accounts / My Portfolios
      if (path.startsWith('/portfolio/accounts') || name.startsWith('portfolio-accounts')) {
        const accountsParent: BreadcrumbItem = { label: t('crumb.myPortfolios'), to: '/portfolio/accounts' }
        if (name === 'portfolio-accounts-new' || path === '/portfolio/accounts/new') {
          return [
            homeItem,
            portfolioDomainItem,
            accountsParent,
            { label: t('crumb.newBasket') }
          ]
        }
        if (name === 'portfolio-accounts-detail' || (params.id && path.startsWith('/portfolio/accounts/'))) {
          return [
            homeItem,
            portfolioDomainItem,
            accountsParent,
            { label: t('crumb.accountDossier') }
          ]
        }
        return [
          homeItem,
          portfolioDomainItem,
          { label: t('crumb.myPortfolios') }
        ]
      }

      // Watchlist
      if (path.startsWith('/portfolio/watchlist') || name === 'portfolio-watchlist') {
        return [
          homeItem,
          portfolioDomainItem,
          { label: t('crumb.watchlist') }
        ]
      }

      // Executions
      if (path.startsWith('/portfolio/executions') || name.startsWith('portfolio-executions')) {
        const execParent: BreadcrumbItem = { label: t('crumb.executions'), to: '/portfolio/executions' }
        if (name === 'portfolio-executions-import' || path === '/portfolio/executions/import') {
          return [
            homeItem,
            portfolioDomainItem,
            execParent,
            { label: t('crumb.importCsv') }
          ]
        }
        if (name === 'portfolio-executions-dividends' || path === '/portfolio/executions/dividends') {
          return [
            homeItem,
            portfolioDomainItem,
            execParent,
            { label: t('crumb.dividendLedger') }
          ]
        }
        return [
          homeItem,
          portfolioDomainItem,
          { label: t('crumb.executions') }
        ]
      }

      // Market News
      if (path.startsWith('/portfolio/news') || name.startsWith('portfolio-news')) {
        const newsParent: BreadcrumbItem = { label: t('crumb.marketNews'), to: '/portfolio/news' }
        if (name === 'portfolio-news-detail' || (params.id && path.startsWith('/portfolio/news/'))) {
          return [
            homeItem,
            portfolioDomainItem,
            newsParent,
            { label: t('crumb.newsBriefing') }
          ]
        }
        return [
          homeItem,
          portfolioDomainItem,
          { label: t('crumb.marketNews') }
        ]
      }

      // Asset Detail: /portfolio/asset/:ticker
      if (path.startsWith('/portfolio/asset') || name === 'portfolio-asset-detail') {
        const ticker = String(params.ticker || 'Asset')
        const portfolioId = query.portfolio_id ? String(query.portfolio_id) : ''
        if (portfolioId) {
          return [
            homeItem,
            portfolioDomainItem,
            { label: t('crumb.myPortfolios'), to: '/portfolio/accounts' },
            { label: t('crumb.accountDossier'), to: `/portfolio/accounts/${portfolioId}` },
            { label: ticker }
          ]
        }
        return [
          homeItem,
          portfolioDomainItem,
          { label: ticker }
        ]
      }
    }

    // 5. Workspace Domain (Main destination: /workspace)
    if (path.startsWith('/workspace') || name.startsWith('workspace-')) {
      const workspaceDomainItem: BreadcrumbItem = { label: t('crumb.workspace'), to: '/workspace' }

      if (path === '/workspace' || name === 'workspace-hub') {
        return [
          homeItem,
          { label: t('crumb.workspace') }
        ]
      }

      if (path.startsWith('/workspace/calendar') || name === 'workspace-calendar') {
        return [
          homeItem,
          workspaceDomainItem,
          { label: t('crumb.calendar') }
        ]
      }

      if (path.startsWith('/workspace/projects/') || name === 'workspace-project-detail') {
        return [
          homeItem,
          workspaceDomainItem,
          { label: t('crumb.projectDossier') }
        ]
      }
    }

    // 6. Cash Flow & Ledger Domain (Main destination: /ledger)
    if (path.startsWith('/ledger') || name.startsWith('ledger-')) {
      const ledgerDomainItem: BreadcrumbItem = { label: t('crumb.ledger'), to: '/ledger' }

      if (path === '/ledger' || path === '/ledger/overview' || name === 'ledger-overview') {
        return [
          homeItem,
          { label: t('crumb.ledger') }
        ]
      }

      if (path.startsWith('/ledger/transactions') || name === 'ledger-transactions') {
        return [
          homeItem,
          ledgerDomainItem,
          { label: t('crumb.transactions') }
        ]
      }

      if (path.startsWith('/ledger/accounts') || name.startsWith('ledger-accounts')) {
        const accountsParent: BreadcrumbItem = { label: t('crumb.accounts'), to: '/ledger/accounts' }
        if (name === 'ledger-account-detail' || (params.id && path.startsWith('/ledger/accounts/'))) {
          return [
            homeItem,
            ledgerDomainItem,
            accountsParent,
            { label: t('crumb.accountStatement') }
          ]
        }
        return [
          homeItem,
          ledgerDomainItem,
          { label: t('crumb.accounts') }
        ]
      }

      if (path.startsWith('/ledger/splits') || name === 'ledger-splits') {
        return [
          homeItem,
          ledgerDomainItem,
          { label: t('crumb.splits') }
        ]
      }

      if (path.startsWith('/ledger/budgets') || name === 'ledger-budgets') {
        return [
          homeItem,
          ledgerDomainItem,
          { label: t('crumb.budgets') }
        ]
      }
    }

    // Fallback Console
    return [
      homeItem,
      { label: t('crumb.console') }
    ]
  })

  return { breadcrumbs }
}
