import { describe, it, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import apiClient from '../src/api/client'
import {
  usePortfolioStore,
  normalizeTicker,
  isTickerMatch
} from '../src/stores/portfolio'
import type { StockWatchlistItem } from '../src/types/portfolio'

describe('Portfolio Search & Watchlist Regression Tests', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('1. Ticker Normalization & Symmetrical Matching', () => {
    it('normalizes tickers correctly', () => {
      assert.strictEqual(normalizeTicker('nvda'), 'NVDA')
      assert.strictEqual(normalizeTicker(' ptt.bk  '), 'PTT.BK')
      assert.strictEqual(normalizeTicker('btc-usd'), 'BTC-USD')
      assert.strictEqual(normalizeTicker(null), '')
      assert.strictEqual(normalizeTicker(undefined), '')
    })

    it('matches Thai stock .BK variants symmetrically', () => {
      assert.strictEqual(isTickerMatch('PTT', 'PTT.BK'), true)
      assert.strictEqual(isTickerMatch('PTT.BK', 'PTT'), true)
      assert.strictEqual(isTickerMatch('ptt', 'PTT.BK'), true)
      assert.strictEqual(isTickerMatch('DELTA.BK', 'delta'), true)
      assert.strictEqual(isTickerMatch('PTTEP', 'PTT'), false)
    })

    it('matches Crypto -USD variants symmetrically', () => {
      assert.strictEqual(isTickerMatch('BTC', 'BTC-USD'), true)
      assert.strictEqual(isTickerMatch('BTC-USD', 'BTC'), true)
      assert.strictEqual(isTickerMatch('eth-usd', 'ETH'), true)
      assert.strictEqual(isTickerMatch('SOL', 'BTC-USD'), false)
    })

    it('handles identical symbols and case insensitivity', () => {
      assert.strictEqual(isTickerMatch('AAPL', 'aapl'), true)
      assert.strictEqual(isTickerMatch('GOOGL', 'googl'), true)
      assert.strictEqual(isTickerMatch('AAPL', 'MSFT'), false)
      assert.strictEqual(isTickerMatch('', 'AAPL'), false)
    })
  })

  describe('2. Universal Asset Search Sequence & Race Conditions', () => {
    it('ignores older in-flight search responses when newer query returns earlier', async () => {
      let searchSeq = 0
      let displayedResults: any[] = []
      let isSearching = false

      // Simulated searchAssets with controllable latencies
      const mockSearchAssets = async (query: string): Promise<any[]> => {
        if (query === 'A') {
          // Slow response for earlier query
          await new Promise(r => setTimeout(r, 60))
          return [{ ticker: 'A', name: 'Agilent Technologies' }]
        }
        if (query === 'AAPL') {
          // Fast response for newer query
          await new Promise(r => setTimeout(r, 10))
          return [{ ticker: 'AAPL', name: 'Apple Inc.' }]
        }
        return []
      }

      // Simulate input sequence in UniversalAssetSearch
      const runSearch = (q: string) => {
        const seq = ++searchSeq
        isSearching = true
        mockSearchAssets(q).then((data) => {
          if (seq !== searchSeq) return // Sequence guard!
          displayedResults = data
          isSearching = false
        })
      }

      // 1. User types "A" (slow 60ms)
      runSearch('A')
      // 2. User quickly finishes typing "AAPL" (fast 10ms)
      runSearch('AAPL')

      // Wait 30ms: "AAPL" should have resolved
      await new Promise(r => setTimeout(r, 30))
      assert.strictEqual(displayedResults.length, 1)
      assert.strictEqual(displayedResults[0].ticker, 'AAPL')

      // Wait another 50ms: "A" finishes now (at 60ms mark), but must be DISCARDED
      await new Promise(r => setTimeout(r, 50))
      assert.strictEqual(displayedResults.length, 1)
      assert.strictEqual(displayedResults[0].ticker, 'AAPL', 'Older response for "A" must not overwrite "AAPL"')
    })

    it('discards in-flight responses when search is cleared', async () => {
      let searchSeq = 0
      let displayedResults: any[] = []
      let showResults = false

      const mockSearchAssets = async (query: string) => {
        await new Promise(r => setTimeout(r, 40))
        return [{ ticker: query, name: `${query} Corp` }]
      }

      // Dispatch search for "NVDA"
      const seq = ++searchSeq
      showResults = true
      mockSearchAssets('NVDA').then((data) => {
        if (seq !== searchSeq) return
        displayedResults = data
      })

      // User immediately clicks clear button
      searchSeq++
      displayedResults = []
      showResults = false

      // Wait 60ms for "NVDA" promise to settle
      await new Promise(r => setTimeout(r, 60))
      assert.strictEqual(displayedResults.length, 0, 'Results must stay empty after clearing')
      assert.strictEqual(showResults, false, 'Dropdown must stay closed after clearing')
    })
  })

  describe('3. Watchlist Store Mutations & Race Condition Prevention', () => {
    it('prevents stale fetchHoldingByTicker from reverting an immediate user toggle', async () => {
      const store = usePortfolioStore()

      // Mock apiClient.post for toggle
      const originalPost = apiClient.post
      const originalGet = apiClient.get

      apiClient.post = async (url: string, data?: any) => {
        if (url === '/portfolio/watchlist/toggle/') {
          await new Promise(r => setTimeout(r, 20))
          return {
            data: {
              is_watchlisted: true,
              ticker: data.ticker,
              data: {
                id: 'wl-1',
                ticker: data.ticker,
                name: 'Apple Inc.',
                asset_type: 'STOCK',
                currency: 'USD'
              }
            }
          } as any
        }
        return originalPost.call(apiClient, url, data)
      }

      // Mock apiClient.get for fetchWatchlist
      apiClient.get = async (url: string) => {
        if (url === '/portfolio/watchlist/') {
          return { data: store.watchlist } as any
        }
        return originalGet.call(apiClient, url)
      }

      // 1. Initial state: AAPL is NOT in watchlist
      assert.strictEqual(store.isWatchlisted('AAPL'), false)

      // 2. Simulated loadAssetData() starts slow fetch (takes 70ms)
      const requestStartedAt = Date.now()
      const slowFetchHoldingPromise = (async () => {
        await new Promise(r => setTimeout(r, 70))
        return {
          ticker: 'AAPL',
          name: 'Apple Inc.',
          is_watchlisted: false // Backend snapshot was computed before toggle!
        }
      })()

      // 3. User immediately clicks toggle button (after 10ms)
      await new Promise(r => setTimeout(r, 10))
      const togglePromise = store.toggleWatchlist('AAPL')
      const toggleResult = await togglePromise
      assert.strictEqual(toggleResult, true)
      assert.strictEqual(store.isWatchlisted('AAPL'), true)

      // 4. Now the slow fetchHolding arrives (at 70ms mark) with is_watchlisted: false
      const fetchedHolding = await slowFetchHoldingPromise
      assert.strictEqual(fetchedHolding.is_watchlisted, false)

      // StockDetailView logic check:
      const lastMutation = store.getWatchlistMutationTime('AAPL')
      assert.ok(lastMutation >= requestStartedAt, 'Mutation must be detected as newer than fetch start time')

      if (lastMutation >= requestStartedAt) {
        fetchedHolding.is_watchlisted = store.isWatchlisted('AAPL')
      }

      // Assert that fetchedHolding.is_watchlisted was corrected and store stays true
      assert.strictEqual(fetchedHolding.is_watchlisted, true)
      assert.strictEqual(store.isWatchlisted('AAPL'), true, 'Watchlist star must remain active!')

      // Restore apiClient
      apiClient.post = originalPost
      apiClient.get = originalGet
    })

    it('deduplicates rapid toggle clicks and shares the in-flight promise', async () => {
      const store = usePortfolioStore()
      let callCount = 0

      const originalPost = apiClient.post
      const originalGet = apiClient.get

      apiClient.post = async (url: string, data?: any) => {
        if (url === '/portfolio/watchlist/toggle/') {
          callCount++
          await new Promise(r => setTimeout(r, 40))
          return {
            data: {
              is_watchlisted: true,
              ticker: data.ticker
            }
          } as any
        }
        return originalPost.call(apiClient, url, data)
      }

      apiClient.get = async (url: string) => {
        if (url === '/portfolio/watchlist/') {
          return { data: store.watchlist } as any
        }
        return originalGet.call(apiClient, url)
      }

      // Fire 3 toggle calls in quick succession for NVDA
      const p1 = store.toggleWatchlist('NVDA')
      assert.strictEqual(store.isTickerToggling('NVDA'), true)

      const p2 = store.toggleWatchlist('NVDA')
      const p3 = store.toggleWatchlist('NVDA')

      const [res1, res2, res3] = await Promise.all([p1, p2, p3])

      assert.strictEqual(res1, true)
      assert.strictEqual(res2, true)
      assert.strictEqual(res3, true)
      assert.strictEqual(callCount, 1, 'Only exactly 1 network POST request should have been dispatched')
      assert.strictEqual(store.isTickerToggling('NVDA'), false, 'Toggling flag should clear after resolution')
      assert.strictEqual(store.isWatchlisted('NVDA'), true)

      apiClient.post = originalPost
      apiClient.get = originalGet
    })

    it('does not mutate store on network/server error', async () => {
      const store = usePortfolioStore()

      const originalPost = apiClient.post
      apiClient.post = async (url: string) => {
        if (url === '/portfolio/watchlist/toggle/') {
          await new Promise(r => setTimeout(r, 10))
          throw new Error('500 Internal Server Error')
        }
        return originalPost.call(apiClient, url)
      }

      await assert.rejects(async () => {
        await store.toggleWatchlist('FAIL_TICKER')
      }, /500 Internal Server Error/)

      assert.strictEqual(store.isWatchlisted('FAIL_TICKER'), false, 'Failed toggle must not add item')
      assert.strictEqual(store.isTickerToggling('FAIL_TICKER'), false, 'Toggling flag must be reset on error')

      apiClient.post = originalPost
    })

    it('seeds watchlist store on direct asset navigation when store has not yet loaded watchlist', () => {
      const store = usePortfolioStore()
      assert.strictEqual(store.hasLoadedWatchlist, false)
      assert.strictEqual(store.watchlist.length, 0)

      // Direct load arrives with is_watchlisted: true
      store.seedWatchlist('DELTA.BK', {
        ticker: 'DELTA.BK',
        name: 'Delta Electronics',
        asset_type: 'STOCK',
        currency: 'THB'
      })

      assert.strictEqual(store.isWatchlisted('DELTA.BK'), true)
      assert.strictEqual(store.isWatchlisted('DELTA'), true, 'Matching helper must recognize DELTA and DELTA.BK')
    })
  })
})
