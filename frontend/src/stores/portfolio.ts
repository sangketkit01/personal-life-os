import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import { useToastStore } from './toast'
import type {
  PortfolioOverview,
  StockHolding,
  StockTransaction,
  CreateTransactionPayload,
  UpdateTransactionPayload,
  UpdateHoldingPayload,
  StockNewsArticle,
  StockWatchlistItem,
  InvestmentPortfolio,
  CreatePortfolioPayload,
  MarketAssetSearchResult,
  MarketStatusResponse,
  StockChartData
} from '../types/portfolio'

export function normalizeTicker(ticker?: string | null): string {
  if (!ticker) return ''
  return ticker.trim().toUpperCase()
}

export function isTickerMatch(a?: string | null, b?: string | null): boolean {
  const cleanA = normalizeTicker(a)
  const cleanB = normalizeTicker(b)
  if (!cleanA || !cleanB) return false
  if (cleanA === cleanB) return true
  if (`${cleanA}.BK` === cleanB || `${cleanB}.BK` === cleanA) return true
  if (`${cleanA}-USD` === cleanB || `${cleanB}-USD` === cleanA) return true
  return false
}

export const usePortfolioStore = defineStore('portfolio', () => {
  const overview = ref<PortfolioOverview | null>(null)
  const holdings = ref<StockHolding[]>([])
  const transactions = ref<StockTransaction[]>([])
  const news = ref<StockNewsArticle[]>([])
  const newsTotalCount = ref<number>(0)
  const watchlist = ref<StockWatchlistItem[]>([])
  const isLoadingWatchlist = ref<boolean>(false)
  const hasLoadedWatchlist = ref<boolean>(false)
  const watchlistMutationTimestamps = ref<Record<string, number>>({})
  const activeWatchlistToggles = ref<Record<string, Promise<boolean> | undefined>>({})
  const portfolios = ref<InvestmentPortfolio[]>([])
  const selectedPortfolioId = ref<string>('ALL')
  const selectedAssetType = ref<string>('ALL')
  const savedCurrency = (typeof window !== 'undefined' ? localStorage.getItem('preferred_portfolio_currency') : null) as 'THB' | 'USD' | null
  const displayCurrency = ref<'THB' | 'USD'>(savedCurrency === 'USD' ? 'USD' : 'THB')
  const usdToThbRate = ref<number>(34.00)
  const marketStatus = ref<MarketStatusResponse | null>(null)
  const lastPriceSyncTime = ref<Date | null>(null)
  const isLoading = ref<boolean>(false)
  const isSubmitting = ref<boolean>(false)
  const isRefreshing = ref<boolean>(false)
  const isLoadingNews = ref<boolean>(false)
  const isSyncingNews = ref<boolean>(false)
  const error = ref<string | null>(null)

  async function fetchPortfolios() {
    try {
      const res = await apiClient.get<InvestmentPortfolio[]>('/portfolio/portfolios/')
      // The ViewSet response is DRF-paginated ({count, next, previous, results}).
      // Storing the raw dict made v-for iterate next/previous (null) and crash
      // the whole render tree with "Cannot read properties of null (reading 'id')".
      const data = res.data as any
      portfolios.value = Array.isArray(data) ? data : (data?.results || [])
      return portfolios.value
    } catch (err: any) {
      console.error('Failed to load portfolios', err)
      throw err
    }
  }

  async function createPortfolio(payload: CreatePortfolioPayload) {
    isLoading.value = true
    try {
      const res = await apiClient.post<InvestmentPortfolio>('/portfolio/portfolios/', payload)
      await Promise.all([fetchPortfolios(), fetchOverview()])
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to create portfolio'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function updatePortfolio(id: string, payload: Partial<CreatePortfolioPayload>) {
    isLoading.value = true
    try {
      const res = await apiClient.patch<InvestmentPortfolio>(`/portfolio/portfolios/${id}/`, payload)
      await Promise.all([fetchPortfolios(), fetchOverview()])
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to update portfolio'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function deletePortfolio(id: string) {
    try {
      await apiClient.delete(`/portfolio/portfolios/${id}/`)
      if (selectedPortfolioId.value === id) {
        selectedPortfolioId.value = 'ALL'
      }
      await Promise.all([fetchPortfolios(), fetchOverview(), fetchHoldings()])
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to delete portfolio'
      throw err
    }
  }

  async function searchAssets(query: string, assetType?: string): Promise<MarketAssetSearchResult[]> {
    try {
      const params: Record<string, string> = { q: query }
      if (assetType && assetType !== 'ALL') {
        params.asset_type = assetType
      }
      const res = await apiClient.get<MarketAssetSearchResult[]>('/portfolio/search/', { params })
      return res.data
    } catch (err) {
      console.error('Failed to search assets', err)
      return []
    }
  }

  async function fetchOverview(options?: { currency?: 'THB' | 'USD'; portfolioId?: string; assetType?: string }) {
    try {
      const targetCurr = options?.currency || displayCurrency.value
      const targetPf = options?.portfolioId !== undefined ? options.portfolioId : selectedPortfolioId.value
      const targetType = options?.assetType !== undefined ? options.assetType : selectedAssetType.value

      const params: Record<string, string> = {
        currency: targetCurr
      }
      if (targetPf && targetPf !== 'ALL') {
        params.portfolio_id = targetPf
      }
      if (targetType && targetType !== 'ALL') {
        params.asset_type = targetType
      }

      const res = await apiClient.get<PortfolioOverview>('/portfolio/overview/', { params })
      overview.value = res.data
      if (res.data.usd_to_thb_rate) {
        usdToThbRate.value = res.data.usd_to_thb_rate
      }
      if (res.data.available_portfolios) {
        portfolios.value = res.data.available_portfolios
      }
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to load portfolio overview'
      throw err
    }
  }

  function setDisplayCurrency(curr: 'THB' | 'USD') {
    displayCurrency.value = curr
    if (typeof window !== 'undefined') {
      localStorage.setItem('preferred_portfolio_currency', curr)
    }
    return fetchOverview({ currency: curr })
  }

  function setSelectedPortfolio(id: string) {
    selectedPortfolioId.value = id
    return Promise.all([
      fetchOverview({ portfolioId: id }),
      fetchHoldings({ portfolioId: id }),
      fetchTransactions({ portfolioId: id })
    ])
  }

  function setSelectedAssetType(type: string) {
    selectedAssetType.value = type
    return Promise.all([
      fetchOverview({ assetType: type }),
      fetchHoldings({ assetType: type })
    ])
  }

  async function fetchHoldings(options?: { portfolioId?: string; assetType?: string }) {
    isLoading.value = true
    try {
      const params: Record<string, string> = {}
      const targetPf = options?.portfolioId !== undefined ? options.portfolioId : selectedPortfolioId.value
      const targetType = options?.assetType !== undefined ? options.assetType : selectedAssetType.value

      if (targetPf && targetPf !== 'ALL') {
        params.portfolio_id = targetPf
      }
      if (targetType && targetType !== 'ALL') {
        params.asset_type = targetType
      }

      const res = await apiClient.get<{ results: StockHolding[] } | StockHolding[]>('/portfolio/holdings/', { params })
      const list = Array.isArray(res.data) ? res.data : res.data.results || []
      holdings.value = list
      return list
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to load holdings'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTransactions(options?: { holdingId?: string; portfolioId?: string; ticker?: string }) {
    isLoading.value = true
    try {
      const params: Record<string, string> = {}
      if (options?.holdingId) params.holding_id = options.holdingId
      if (options?.ticker) params.ticker = options.ticker
      const targetPf = options?.portfolioId !== undefined ? options.portfolioId : selectedPortfolioId.value
      if (targetPf && targetPf !== 'ALL') {
        params.portfolio_id = targetPf
      }

      const res = await apiClient.get<{ results: StockTransaction[] } | StockTransaction[]>('/portfolio/transactions/', { params })
      const list = Array.isArray(res.data) ? res.data : res.data.results || []
      transactions.value = list
      return list
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to load transactions'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchHoldingByTicker(ticker: string, options?: { holdingId?: string; portfolioId?: string }): Promise<StockHolding> {
    const params: Record<string, string> = {}
    if (options?.holdingId) params.holding_id = options.holdingId
    if (options?.portfolioId && options.portfolioId !== 'ALL') params.portfolio_id = options.portfolioId

    const res = await apiClient.get<StockHolding>(`/portfolio/holdings/by-ticker/${encodeURIComponent(ticker)}/`, { params })
    return res.data
  }

  async function fetchNewsArticle(id: string): Promise<StockNewsArticle> {
    const res = await apiClient.get<StockNewsArticle>(`/portfolio/news/${id}/`)
    return res.data
  }

  async function fetchStockChart(ticker: string, period = '1D'): Promise<StockChartData> {
    const res = await apiClient.get<StockChartData>(`/portfolio/holdings/by-ticker/${encodeURIComponent(ticker)}/chart/`, {
      params: { period }
    })
    return res.data
  }

  async function fetchNews(options?: { ticker?: string; today_only?: boolean; held_only?: boolean; watchlist_only?: boolean; page?: number }) {
    isLoadingNews.value = true
    try {
      const params: Record<string, any> = {}
      if (options?.ticker) params.ticker = options.ticker
      if (options?.today_only) params.today_only = 'true'
      if (options?.held_only) params.held_only = 'true'
      if (options?.watchlist_only) params.watchlist_only = 'true'
      if (options?.page) params.page = options.page

      const res = await apiClient.get<{ count: number; results: StockNewsArticle[] } | StockNewsArticle[]>('/portfolio/news/', { params })
      if (Array.isArray(res.data)) {
        news.value = res.data
        newsTotalCount.value = res.data.length
      } else {
        news.value = res.data.results || []
        newsTotalCount.value = res.data.count || 0
      }
      return news.value
    } catch (err: any) {
      console.error('Failed to load portfolio news', err)
      throw err
    } finally {
      isLoadingNews.value = false
    }
  }

  function getWatchlistMutationTime(ticker: string): number {
    const clean = normalizeTicker(ticker)
    return watchlistMutationTimestamps.value[clean] || 0
  }

  function recordWatchlistMutation(ticker: string, time?: number) {
    const clean = normalizeTicker(ticker)
    if (!clean) return
    const t = time || Date.now()
    watchlistMutationTimestamps.value[clean] = t
    if (clean.endsWith('.BK')) {
      watchlistMutationTimestamps.value[clean.slice(0, -3)] = t
    } else {
      watchlistMutationTimestamps.value[`${clean}.BK`] = t
    }
    if (clean.endsWith('-USD')) {
      watchlistMutationTimestamps.value[clean.slice(0, -4)] = t
    } else {
      watchlistMutationTimestamps.value[`${clean}-USD`] = t
    }
  }

  function isTickerToggling(ticker: string): boolean {
    const clean = normalizeTicker(ticker)
    return Boolean(activeWatchlistToggles.value[clean])
  }

  function isWatchlisted(ticker: string): boolean {
    return watchlist.value.some(w => isTickerMatch(w.ticker, ticker))
  }

  function seedWatchlist(ticker: string, data?: Partial<StockWatchlistItem>) {
    if (isWatchlisted(ticker)) return
    const clean = normalizeTicker(ticker)
    if (!clean) return
    watchlist.value.push({
      id: `seed-${clean}-${Date.now()}`,
      ticker: clean,
      name: data?.name || clean,
      asset_type: data?.asset_type || 'STOCK',
      currency: data?.currency || 'USD',
      ...data
    } as StockWatchlistItem)
  }

  async function fetchWatchlist(): Promise<StockWatchlistItem[]> {
    isLoadingWatchlist.value = true
    const fetchStart = Date.now()
    try {
      const res = await apiClient.get<StockWatchlistItem[] | { results: StockWatchlistItem[] }>('/portfolio/watchlist/')
      const items = Array.isArray(res.data) ? res.data : (res.data.results || [])

      // Preserve local mutations that occurred while fetch was in flight
      const reconciled = items.filter(serverItem => {
        const mutTime = getWatchlistMutationTime(serverItem.ticker)
        if (mutTime >= fetchStart) {
          return isWatchlisted(serverItem.ticker)
        }
        return true
      })

      for (const localItem of watchlist.value) {
        const mutTime = getWatchlistMutationTime(localItem.ticker)
        if (mutTime >= fetchStart && isWatchlisted(localItem.ticker)) {
          if (!reconciled.some(r => isTickerMatch(r.ticker, localItem.ticker))) {
            reconciled.push(localItem)
          }
        }
      }

      watchlist.value = reconciled
      hasLoadedWatchlist.value = true
      return reconciled
    } catch (err: any) {
      console.error('Failed to fetch watchlist', err)
      return []
    } finally {
      isLoadingWatchlist.value = false
    }
  }

  async function toggleWatchlist(ticker: string): Promise<boolean> {
    const clean = normalizeTicker(ticker)
    if (!clean) return false

    const existing = activeWatchlistToggles.value[clean]
    if (existing) {
      return existing
    }

    const togglePromise = (async () => {
      const mutationTime = Date.now()
      recordWatchlistMutation(clean, mutationTime)

      try {
        const res = await apiClient.post<{
          is_watchlisted: boolean
          ticker: string
          data?: StockWatchlistItem
          message?: string
        }>('/portfolio/watchlist/toggle/', { ticker: clean })

        const serverStatus = res.data.is_watchlisted
        const serverTicker = res.data.ticker || clean

        recordWatchlistMutation(serverTicker, Date.now())
        recordWatchlistMutation(clean, Date.now())

        if (serverStatus) {
          if (!isWatchlisted(serverTicker)) {
            const newItem: StockWatchlistItem = res.data.data || {
              id: `wl-${serverTicker}-${Date.now()}`,
              ticker: serverTicker,
              name: serverTicker,
              asset_type: 'STOCK',
              currency: 'USD'
            } as StockWatchlistItem
            watchlist.value.push(newItem)
          }
        } else {
          watchlist.value = watchlist.value.filter(
            w => !isTickerMatch(w.ticker, serverTicker) && !isTickerMatch(w.ticker, clean)
          )
        }

        hasLoadedWatchlist.value = true
        fetchWatchlist().catch(() => {})

        return serverStatus
      } catch (err: any) {
        console.error('Failed to toggle watchlist', err)
        throw err
      } finally {
        delete activeWatchlistToggles.value[clean]
      }
    })()

    activeWatchlistToggles.value[clean] = togglePromise
    return togglePromise
  }

  async function syncNews() {
    isSyncingNews.value = true
    try {
      const res = await apiClient.post('/portfolio/news/sync/')
      await fetchNews()
      return res.data
    } catch (err: any) {
      console.error('Failed to sync portfolio news', err)
      throw err
    } finally {
      isSyncingNews.value = false
    }
  }

  async function translateArticle(id: string) {
    try {
      const res = await apiClient.post<StockNewsArticle>(`/portfolio/news/${id}/translate/`)
      // Update in-place in local list
      const idx = news.value.findIndex(item => item.id === id)
      if (idx !== -1) {
        news.value[idx] = res.data
      }
      return res.data
    } catch (err: any) {
      console.error('Failed to translate article', err)
      throw err
    }
  }

  async function fetchMarketStatus(): Promise<MarketStatusResponse> {
    try {
      const res = await apiClient.get<MarketStatusResponse>('/portfolio/market-status/')
      marketStatus.value = res.data
      return res.data
    } catch (err: any) {
      console.error('Failed to load market status', err)
      throw err
    }
  }

  async function refreshMarketPrices(force = false) {
    isRefreshing.value = true
    const requestedPf = selectedPortfolioId.value
    const requestedType = selectedAssetType.value
    const requestedCurr = displayCurrency.value

    const payload: Record<string, any> = { force }
    if (requestedPf && requestedPf !== 'ALL') {
      payload.portfolio_id = requestedPf
    }
    if (requestedType && requestedType !== 'ALL') {
      payload.asset_type = requestedType
    }
    if (requestedCurr) {
      payload.currency = requestedCurr
    }

    try {
      const res = await apiClient.post<PortfolioOverview>('/portfolio/refresh/', payload)
      // Only update when filter state matches request to prevent fast-switching race condition
      if (selectedPortfolioId.value === requestedPf && selectedAssetType.value === requestedType) {
        overview.value = res.data
        lastPriceSyncTime.value = new Date()
      }
      await fetchHoldings({ portfolioId: requestedPf, assetType: requestedType })
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to refresh market prices'
      throw err
    } finally {
      isRefreshing.value = false
    }
  }

  async function addTransaction(payload: CreateTransactionPayload) {
    isSubmitting.value = true
    try {
      const res = await apiClient.post<StockTransaction>('/portfolio/transactions/', payload)
      // Refresh state in background without throwing if non-critical endpoints fail
      Promise.allSettled([
        fetchOverview(),
        fetchHoldings(),
        fetchTransactions(),
        fetchNews()
      ]).catch(syncErr => console.warn('Background sync after trade encountered warning:', syncErr))
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to save transaction'
      throw err
    } finally {
      isSubmitting.value = false
    }
  }

  async function updateTransaction(id: string, payload: UpdateTransactionPayload) {
    isSubmitting.value = true
    try {
      const res = await apiClient.patch<StockTransaction>(`/portfolio/transactions/${id}/`, payload)
      // Background sync after transaction update
      Promise.allSettled([
        fetchOverview(),
        fetchHoldings(),
        fetchTransactions()
      ]).catch(syncErr => console.warn('Background sync after update encountered warning:', syncErr))
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to update transaction'
      throw err
    } finally {
      isSubmitting.value = false
    }
  }

  async function updateHolding(id: string, payload: UpdateHoldingPayload) {
    isLoading.value = true
    try {
      const res = await apiClient.patch<StockHolding>(`/portfolio/holdings/${id}/`, payload)
      try {
        await Promise.all([fetchOverview(), fetchHoldings(), fetchTransactions()])
      } catch (refreshErr) {
        console.warn('Post-update holding refresh failed:', refreshErr)
        const toast = useToastStore()
        toast.error('Holding updated, but failed to refresh portfolio.', 6000, {
          label: 'Retry refresh',
          onClick: () => { Promise.all([fetchOverview(), fetchHoldings(), fetchTransactions()]) }
        })
      }
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to update holding'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function moveHolding(id: string, targetPortfolioId: string) {
    isLoading.value = true
    try {
      const res = await apiClient.post(`/portfolio/holdings/${id}/move/`, {
        target_portfolio_id: targetPortfolioId
      })
      try {
        await Promise.all([fetchPortfolios(), fetchOverview(), fetchHoldings(), fetchTransactions()])
      } catch (refreshErr) {
        console.warn('Post-move holding refresh failed:', refreshErr)
        const toast = useToastStore()
        toast.error('Asset moved, but failed to refresh portfolio.', 6000, {
          label: 'Retry refresh',
          onClick: () => { Promise.all([fetchPortfolios(), fetchOverview(), fetchHoldings(), fetchTransactions()]) }
        })
      }
      return res.data
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to move asset'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function deleteTransaction(id: string) {
    try {
      await apiClient.delete(`/portfolio/transactions/${id}/`)
      try {
        await Promise.all([fetchOverview(), fetchHoldings(), fetchTransactions()])
      } catch (refreshErr) {
        console.warn('Post-delete transaction refresh failed:', refreshErr)
        const toast = useToastStore()
        toast.error('Transaction deleted, but failed to refresh data.', 6000, {
          label: 'Retry refresh',
          onClick: () => { Promise.all([fetchOverview(), fetchHoldings(), fetchTransactions()]) }
        })
      }
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to delete transaction'
      throw err
    }
  }

  async function deleteHolding(id: string) {
    try {
      await apiClient.delete(`/portfolio/holdings/${id}/`)
      try {
        await Promise.all([fetchOverview(), fetchHoldings(), fetchTransactions()])
      } catch (refreshErr) {
        console.warn('Post-delete holding refresh failed:', refreshErr)
        const toast = useToastStore()
        toast.error('Asset deleted, but failed to refresh portfolio.', 6000, {
          label: 'Retry refresh',
          onClick: () => { Promise.all([fetchOverview(), fetchHoldings(), fetchTransactions()]) }
        })
      }
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'Failed to delete asset'
      throw err
    }
  }

  return {
    overview,
    holdings,
    transactions,
    news,
    newsTotalCount,
    watchlist,
    isLoadingWatchlist,
    hasLoadedWatchlist,
    isTickerToggling,
    getWatchlistMutationTime,
    recordWatchlistMutation,
    seedWatchlist,
    portfolios,
    selectedPortfolioId,
    selectedAssetType,
    displayCurrency,
    usdToThbRate,
    marketStatus,
    lastPriceSyncTime,
    isLoading,
    isSubmitting,
    isRefreshing,
    isLoadingNews,
    isSyncingNews,
    error,
    fetchPortfolios,
    createPortfolio,
    updatePortfolio,
    deletePortfolio,
    fetchWatchlist,
    toggleWatchlist,
    isWatchlisted,
    searchAssets,
    setSelectedPortfolio,
    setSelectedAssetType,
    setDisplayCurrency,
    fetchOverview,
    fetchHoldings,
    fetchHoldingByTicker,
    fetchTransactions,
    fetchNews,
    fetchNewsArticle,
    fetchStockChart,
    syncNews,
    translateArticle,
    fetchMarketStatus,
    refreshMarketPrices,
    addTransaction,
    updateTransaction,
    updateHolding,
    moveHolding,
    deleteTransaction,
    deleteHolding
  }
})
