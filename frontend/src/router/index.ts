import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/',
      component: () => import('../layouts/DashboardLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'overview',
          component: () => import('../views/OverviewView.vue'),
        },
        // Financial Radar Domain Routes (Separation of Concerns)
        {
          path: 'finance',
          redirect: '/finance/overview',
        },
        {
          path: 'finance/overview',
          name: 'finance-overview',
          component: () => import('../views/finance/FinanceRadarOverviewView.vue'),
        },
        {
          path: 'finance/installments',
          name: 'finance-installments',
          component: () => import('../views/finance/InstallmentsView.vue'),
        },
        {
          path: 'finance/installments/new',
          name: 'finance-installments-new',
          component: () => import('../views/finance/InstallmentCreateView.vue'),
        },
        {
          path: 'finance/installments/:id',
          name: 'finance-installments-detail',
          component: () => import('../views/finance/InstallmentDetailView.vue'),
        },
        {
          path: 'finance/bnpl',
          name: 'finance-bnpl',
          component: () => import('../views/finance/BNPLView.vue'),
        },
        {
          path: 'finance/bnpl/new',
          name: 'finance-bnpl-new',
          component: () => import('../views/finance/BNPLAccountCreateView.vue'),
        },
        {
          path: 'finance/bnpl/:id',
          name: 'finance-bnpl-detail',
          component: () => import('../views/finance/BNPLAccountDetailView.vue'),
        },
        {
          path: 'finance/bnpl/:id/new-order',
          name: 'finance-bnpl-new-order',
          component: () => import('../views/finance/BNPLOrderCreateView.vue'),
        },
        {
          path: 'finance/subscriptions',
          name: 'finance-subscriptions',
          component: () => import('../views/finance/SubscriptionsView.vue'),
        },
        {
          path: 'finance/subscriptions/new',
          name: 'finance-subscriptions-new',
          component: () => import('../views/finance/SubscriptionCreateView.vue'),
        },
        {
          path: 'finance/subscriptions/:id',
          name: 'finance-subscriptions-detail',
          component: () => import('../views/finance/SubscriptionDetailView.vue'),
        },
        {
          path: 'finance/debts',
          name: 'finance-debts',
          component: () => import('../views/finance/DebtsView.vue'),
        },
        {
          path: 'finance/debts/new',
          name: 'finance-debts-new',
          component: () => import('../views/finance/DebtCreateView.vue'),
        },
        {
          path: 'finance/debts/:id',
          name: 'finance-debts-detail',
          component: () => import('../views/finance/DebtDetailView.vue'),
        },

        // Wealth & Portfolio Domain Routes (Separation of Concerns)
        {
          path: 'portfolio',
          redirect: '/portfolio/overview',
        },
        {
          path: 'portfolio/overview',
          name: 'portfolio-overview',
          component: () => import('../views/portfolio/PortfolioOverviewView.vue'),
        },
        {
          path: 'portfolio/accounts',
          name: 'portfolio-accounts',
          component: () => import('../views/portfolio/PortfolioAccountsView.vue'),
        },
        {
          path: 'portfolio/accounts/new',
          name: 'portfolio-accounts-new',
          component: () => import('../views/portfolio/PortfolioAccountCreateView.vue'),
        },
        {
          path: 'portfolio/accounts/:id',
          name: 'portfolio-accounts-detail',
          component: () => import('../views/portfolio/PortfolioAccountDetailView.vue'),
        },
        {
          path: 'portfolio/watchlist',
          name: 'portfolio-watchlist',
          component: () => import('../views/portfolio/PortfolioWatchlistView.vue'),
        },
        {
          path: 'portfolio/executions',
          name: 'portfolio-executions',
          component: () => import('../views/portfolio/PortfolioExecutionsView.vue'),
        },
        {
          path: 'portfolio/executions/import',
          name: 'portfolio-executions-import',
          component: () => import('../views/portfolio/PortfolioExecutionsImportView.vue'),
        },
        {
          path: 'portfolio/executions/dividends',
          name: 'portfolio-executions-dividends',
          component: () => import('../views/portfolio/PortfolioDividendsView.vue'),
        },
        {
          path: 'portfolio/news',
          name: 'portfolio-news',
          component: () => import('../views/portfolio/PortfolioNewsView.vue'),
        },
        {
          path: 'portfolio/asset/:ticker',
          name: 'portfolio-asset-detail',
          component: () => import('../views/StockDetailView.vue'),
        },
        {
          path: 'portfolio/news/:id',
          name: 'portfolio-news-detail',
          component: () => import('../views/NewsDetailView.vue'),
        },
        {
          path: 'workspace',
          name: 'workspace',
          component: () => import('../views/WorkspaceView.vue'),
        },
        // Cash Flow & Ledger Domain Routes
        {
          path: 'ledger',
          name: 'ledger-overview',
          component: () => import('../views/ledger/LedgerOverviewView.vue'),
        },
        {
          path: 'ledger/overview',
          redirect: '/ledger',
        },
        {
          path: 'ledger/transactions',
          name: 'ledger-transactions',
          component: () => import('../views/ledger/LedgerTransactionsView.vue'),
        },
        {
          path: 'ledger/accounts',
          name: 'ledger-accounts',
          component: () => import('../views/ledger/LedgerAccountsView.vue'),
        },
        {
          path: 'ledger/accounts/:id',
          name: 'ledger-account-detail',
          component: () => import('../views/ledger/LedgerAccountDetailView.vue'),
        },
        {
          path: 'ledger/splits',
          name: 'ledger-splits',
          component: () => import('../views/ledger/LedgerSplitsView.vue'),
        },
        {
          path: 'ledger/budgets',
          name: 'ledger-budgets',
          component: () => import('../views/ledger/LedgerBudgetsView.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('../views/SettingsView.vue'),
        },
        {
          path: 'auth/google/callback',
          name: 'google-auth-callback',
          component: () => import('../views/GoogleAuthCallbackView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach(async (to, _from) => {
  const authStore = useAuthStore()

  // Check session via cookie if still initializing
  if (authStore.isLoading) {
    await authStore.fetchMe()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    return { name: 'overview' }
  }
})

export default router
