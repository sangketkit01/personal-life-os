const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')
const vue = require('vue')
const pinia = require('pinia')

function evaluate(file, env, names, sfc = false) {
  let source = fs.readFileSync(path.resolve(file), 'utf8')
  if (sfc) source = require('@vue/compiler-sfc').parse(source).descriptor.scriptSetup.content
  const tree = ts.createSourceFile(file + '.ts', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
  source = ts.createPrinter().printList(ts.ListFormat.MultiLine, ts.factory.createNodeArray(tree.statements.filter(s => !ts.isImportDeclaration(s))), tree)
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const bindings = names.map(name => `${name}: typeof ${name} !== 'undefined' ? ${name} : exports.${name}`).join(',')
  return new Function(...Object.keys(env), 'exports', output + '\nreturn {' + bindings + '};')(...Object.values(env), {})
}
const tick = () => new Promise(resolve => setImmediate(resolve))
const overview = value => ({ total_market_value: value, usd_to_thb_rate: 35, holdings: [], quotes: {} })

function storeHarness(api) {
  pinia.setActivePinia(pinia.createPinia())
  let timer = null
  const document = { hidden: false }
  const env = { ...vue, ...pinia, apiClient: api, useToastStore: () => ({ error() {}, success() {} }), document,
    setTimeout: fn => { timer = fn; return 1 }, clearTimeout: () => { timer = null } }
  const module = evaluate('src/stores/portfolio.ts', env, ['usePortfolioStore'])
  return { store: module.usePortfolioStore(), document, timer: () => timer }
}

test('a late snapshot response cannot replace a more recent portfolio response', async () => {
  const responses = []
  const { store } = storeHarness({ get: () => new Promise(resolve => responses.push(resolve)) })
  const older = store.fetchOverview(), newer = store.fetchOverview()
  responses[1]({ data: overview(200) }); await newer
  responses[0]({ data: overview(100) }); await older
  assert.equal(store.overview.total_market_value, 200)
})

test('late holdings responses and failures cannot overwrite a newly selected portfolio', async () => {
  const pending = []
  const { store } = storeHarness({ get: (_url, options) => new Promise((resolve, reject) => pending.push({ resolve, reject, options })) })
  const old = store.fetchHoldings({ silent: true })
  store.selectedPortfolioId = 'new'
  const newer = store.fetchHoldings()
  pending[1].resolve({ data: [{ id: 'new-holding' }] }); await newer
  pending[0].resolve({ data: [{ id: 'old-holding' }] }); await old
  assert.equal(store.holdings[0].id, 'new-holding')
  const failed = store.fetchHoldings({ silent: true }).catch(() => {})
  store.selectedAssetType = 'CRYPTO'
  const crypto = store.fetchHoldings()
  pending[3].resolve({ data: [] }); await crypto
  pending[2].reject({ response: { data: { detail: 'old failure' } } }); await failed
  assert.deepEqual(store.holdings, [])
  assert.equal(store.error, null)
  assert.equal(store.isLoading, false)
})

test('shared polling reads snapshots once per cycle, pauses when hidden and stops after all views release', async () => {
  const calls = []
  const api = { get: async url => { calls.push(url); return { data: url.includes('overview') ? overview(100) : [] } }, post: () => assert.fail('polling must not request a forced quote refresh') }
  const h = storeHarness(api)
  const first = h.store.startQuotePolling(), second = h.store.startQuotePolling()
  await tick()
  assert.equal(calls.filter(u => u.includes('overview')).length, 1)
  assert.ok(h.timer())
  const count = calls.length
  h.document.hidden = true; await h.timer()()
  assert.equal(calls.length, count)
  first(); assert.ok(h.timer())
  second(); assert.equal(h.timer(), null)
})

test('a manual quote refresh finishing after a portfolio switch cannot fetch old holdings over the new request', async () => {
  let finishRefresh
  const calls = []
  const { store } = storeHarness({ post: () => new Promise(resolve => { finishRefresh = resolve }), get: async (_url, options) => { calls.push(options.params); return { data: [{ id: 'new' }] } } })
  const old = store.refreshMarketPrices(true)
  store.selectedPortfolioId = 'new-portfolio'
  await store.fetchHoldings()
  finishRefresh({ data: overview(100) }); await old
  assert.equal(calls.length, 1)
  assert.equal(store.holdings[0].id, 'new')
})

test('price rule form starts blank and editing restores the selected actual rule', () => {
  const props = {}
  const m = evaluate('src/components/portfolio/PriceAlertsPanel.vue', { ...vue, watch: () => {}, defineProps: () => props,
    useToastStore: () => ({}), api: {} }, ['begin', 'form'], true)
  m.begin()
  assert.deepEqual(m.form.value, { ticker: '', currency: '', condition: '', target_price: '' })
  m.begin({ id: 'id', ticker: 'V', currency: 'USD', condition: 'LTE', target_price: '100' })
  assert.equal(m.form.value.target_price, '100')
  assert.equal(m.form.value.condition, 'LTE')
})

test('notification settings clear both quiet times as null and prevent duplicate saves', async () => {
  let resolve, count = 0, sent
  const api = { patch: (_url, data) => { count++; sent = data; return new Promise(r => { resolve = r }) } }
  const m = evaluate('src/components/settings/NotificationSettings.vue', { ...vue, onMounted: () => {}, api,
    useToastStore: () => ({ success() {} }) }, ['prefs', 'save'], true)
  m.prefs.value = { quiet_start: '', quiet_end: '', timezone: 'Asia/Bangkok' }
  const pending = m.save(); await m.save()
  assert.equal(count, 1)
  assert.equal(sent.quiet_start, null)
  assert.equal(sent.quiet_end, null)
  resolve({ data: sent }); await pending
})

test('login return paths preserve app links and reject external redirects', () => {
  const { safeReturnPath } = evaluate('src/utils/returnPath.ts', {}, ['safeReturnPath'])
  assert.equal(safeReturnPath('/workspace/calendar?event_id=abc'), '/workspace/calendar?event_id=abc')
  for (const bad of ['https://evil.test', '//evil.test', '/\\evil.test', '/login?redirect=x', '/register', '/\nmalicious']) assert.equal(safeReturnPath(bad), '/')
})

test('draft UI preserves initial load, typing and clearing with the actual Vue scheduler', async () => {
  const renderer = vue.createRenderer({ createElement: t => ({ t }), createComment: s => ({ s }), createText: s => ({ s }), insert() {}, remove() {}, setElementText() {}, setText() {}, setComment() {}, parentNode: () => null, nextSibling: () => null, patchProp() {} })
  const draft = amount => ({ cycle_key: '2026-11', items: [{ id: 'd', name: 'Usage', type: 'DYNAMIC', amount }] })
  const ob = amount => ({ id: 'sub', type: 'SUBSCRIPTION', metadata: { is_itemized: true, current_cycle: draft(amount) }, summary: { cycle_key: '2026-11', current_cycle: draft(amount) } })
  for (const mode of ['initial', 'typed', 'cleared']) {
    let result, resolve, timer, saved
    const state = vue.reactive({ open: false, obligation: mode === 'initial' ? null : ob(25) })
    const Child = { props: ['isOpen', 'obligation'], setup(props) {
      result = evaluate('src/components/finance/PayModal.vue', { ...vue, onMounted() {}, defineProps: () => props, defineEmits: () => () => {}, useBodyScrollLock() {},
        useFinanceStore: () => ({ fetchCycleBill: () => new Promise(r => { resolve = r }), saveCycleBillDraft: async (_id, items) => { saved = items } }),
        useLedgerStore: () => ({ accounts: [] }), useStorageStore: () => ({}), useToastStore: () => ({ error() {} }),
        setTimeout: fn => { timer = fn; return 1 }, clearTimeout() {} }, ['cycleDynamicItems', 'onDynamicAmountChange'], true)
      return () => null
    } }
    const app = renderer.createApp({ setup: () => () => vue.h(Child, { isOpen: state.open, obligation: state.obligation }) })
    app.mount({})
    if (mode === 'initial') state.obligation = ob(null)
    state.open = true; await vue.nextTick()
    if (mode !== 'initial') { result.cycleDynamicItems.value[0].amount = mode === 'typed' ? '99' : ''; result.onDynamicAmountChange('d') }
    resolve(draft(25)); await tick()
    assert.equal(result.cycleDynamicItems.value[0].amount, mode === 'initial' ? '25' : mode === 'typed' ? '99' : '')
    if (mode === 'cleared') { await timer(); assert.equal(saved[0].amount, null) }
    app.unmount()
  }
})

test('asset navigation ignores the previous ticker response after switching assets', async () => {
  const pending = {}
  const route = vue.reactive({ params: { ticker: 'V' }, query: {} })
  const store = { selectedPortfolioId: 'ALL', hasLoadedWatchlist: true, getWatchlistMutationTime: () => 0, isWatchlisted: () => false,
    fetchHoldingByTicker: ticker => new Promise(resolve => { pending[ticker] = resolve }),
    fetchNews: async ({ ticker }) => [{ id: ticker + '-news' }] }
  const env = { ...vue, onMounted() {}, onUnmounted() {}, watch() {}, useBodyScrollLock() {}, useRoute: () => route, useRouter: () => ({}),
    usePortfolioStore: () => store, useToastStore: () => ({}), t: key => key, isTickerMatch: (a, b) => a === b }
  const source = fs.readFileSync(path.resolve('src/views/StockDetailView.vue'), 'utf8')
  const script = require('@vue/compiler-sfc').parse(source).descriptor.scriptSetup.content
  const tree = ts.createSourceFile('stock.ts', script, ts.ScriptTarget.Latest, true)
  for (const node of tree.statements) if (ts.isImportDeclaration(node) && node.moduleSpecifier.text === 'lucide-vue-next') {
    for (const item of node.importClause.namedBindings.elements) env[item.name.text] = () => null
  }
  const m = evaluate('src/views/StockDetailView.vue', env, ['loadAssetData', 'holding', 'assetNews'], true)
  const old = m.loadAssetData()
  route.params.ticker = 'NVDA'
  const current = m.loadAssetData()
  pending.NVDA({ id: 'nvda', ticker: 'NVDA', currency: 'USD', is_held: false })
  await current
  pending.V({ id: 'visa', ticker: 'V', currency: 'USD', is_held: false })
  await old
  assert.equal(m.holding.value.ticker, 'NVDA')
  assert.equal(m.assetNews.value[0].id, 'NVDA-news')
})
