const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const ts = require('typescript')
const vue = require('vue')
const pinia = require('pinia')

function evaluate(file, env, names, sfc = false) {
  let source = fs.readFileSync(file, 'utf8')
  if (sfc) source = require('@vue/compiler-sfc').parse(source).descriptor.scriptSetup.content
  const tree = ts.createSourceFile(file+'.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS)
  source = ts.createPrinter().printList(ts.ListFormat.MultiLine,ts.factory.createNodeArray(tree.statements.filter(s=>!ts.isImportDeclaration(s))),tree)
  if (!names) names=tree.statements.flatMap(s=>ts.isVariableStatement(s) ? s.declarationList.declarations.filter(d=>ts.isIdentifier(d.name)).map(d=>d.name.text) : ts.isFunctionDeclaration(s) && s.name ? [s.name.text] : [])
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText
  return new Function(...Object.keys(env),'exports',code+';return {'+names.map(n=>`${n}:typeof ${n} !== 'undefined' ? ${n} : exports.${n}`).join(',')+'};')(...Object.values(env),{})
}

function dashboardHarness(api) {
  const pushed=[]
  const module=evaluate('src/views/ledger/LedgerOverviewView.vue',{...vue,watch(){},onMounted(){},onUnmounted(){},ledgerApi:api,
    useRouter:()=>({push:x=>pushed.push(x)}),useLedgerStore:()=>({accounts:[]}),useToastStore:()=>({error(){}})},
    ['load','data','month','currency','error','loading','transactionsLink','openCategory','chartMode','openChartPeriod'],true)
  return {...module,pushed}
}

test('dashboard ignores old currency responses and exposes failures instead of zero balances',async()=>{
  const pending=[]
  const m=dashboardHarness({getDashboard:()=>new Promise((resolve,reject)=>pending.push({resolve,reject}))})
  const thb=m.load(); m.currency.value='USD'; const usd=m.load()
  pending[1].resolve({currency:'USD'}); await usd
  pending[0].resolve({currency:'THB'}); await thb
  assert.equal(m.data.value.currency,'USD')
  m.month.value='2026-09';const failed=m.load()
  assert.equal(m.data.value,null)
  pending[2].reject(new Error('offline'));await failed
  assert.ok(m.error.value)
  assert.equal(m.data.value,null)
  assert.equal(m.loading.value,false)
  const stale=m.load();m.month.value='';await m.load()
  pending[3].resolve({currency:'USD'});await stale
  assert.equal(m.data.value,null)
  assert.ok(m.error.value)
})

test('dashboard drilldowns retain category, currency, dates and the calculation basis',()=>{
  const m=dashboardHarness({})
  m.currency.value='USD'
  m.data.value={period:{start:'2026-10-01',end:'2026-10-15'},daily:[{date:'2026-10-10'}],history:[{month:'2026-09'},{month:'2026-10'}]}
  m.openCategory('EXPENSE','food')
  assert.deepEqual(m.pushed.pop().query,{start_date:'2026-10-01',end_date:'2026-10-15',currency:'USD',report_kind:'EXPENSE',category:'food'})
  m.openCategory('INCOME',null)
  assert.equal(m.pushed.pop().query.uncategorized,'true')
  m.openChartPeriod(0)
  assert.equal(m.pushed.pop().query.start_date,'2026-10-10')
  m.chartMode.value='6';m.openChartPeriod(1)
  assert.equal(m.pushed.pop().query.end_date,'2026-10-15')
})

test('late transaction and budget requests cannot replace a newer period',async()=>{
  pinia.setActivePinia(pinia.createPinia())
  const tx=[],budgets=[]
  const m=evaluate('src/stores/ledger.ts',{...vue,...pinia,useToastStore:()=>({}),ledgerApi:{
    getTransactions:()=>new Promise(resolve=>tx.push(resolve)),getBudgets:()=>new Promise(resolve=>budgets.push(resolve))}},['useLedgerStore'])
  const store=m.useLedgerStore()
  const old=store.fetchTransactions({currency:'THB'}),current=store.fetchTransactions({currency:'USD'})
  tx[1]({results:[{id:'usd'}],count:1});await current
  tx[0]({results:[{id:'thb'}],count:100});await old
  assert.equal(store.transactions[0].id,'usd');assert.equal(store.totalTransactionsCount,1)
  const previousBudget=store.fetchBudgets('2026-09'),latestBudget=store.fetchBudgets('2026-10')
  budgets[1]([{id:'oct'}]);await latestBudget
  budgets[0]([{id:'sept'}]);await previousBudget
  assert.equal(store.budgets[0].id,'oct')
})

test('transaction editing persists report classification, prevents double submission and emits updated only',async()=>{
  let finish,sent,count=0
  const events=[]
  const props={isOpen:true,transactionToEdit:{id:'loan',account:'bank',title:'Borrowed',gross_amount:2000,transaction_type:'INFLOW',transaction_date:'2026-10-10',reporting_kind:'LOAN'}}
  const m=evaluate('src/components/ledger/TransactionModal.vue',{...vue,defineProps:()=>props,defineEmits:()=>x=>events.push(x),
    window:{addEventListener(){},removeEventListener(){}},
    onMounted(){},onUnmounted(){},useBodyScrollLock(){},useToastStore:()=>({}),useStorageStore:()=>({}),
    useLedgerStore:()=>({accounts:[{id:'bank',currency:'USD'}],categories:[{id:'existing'}],updateTransaction:(_id,payload)=>{count++;sent=payload;return new Promise(resolve=>{finish=resolve})}})},
    ['form','handleSubmit','transactionCurrency'],true)
  assert.equal(m.form.reporting_kind,'LOAN')
  assert.equal(m.transactionCurrency.value,'USD')
  const first=m.handleSubmit();await m.handleSubmit()
  assert.equal(count,1);assert.equal(sent.reporting_kind,'LOAN')
  finish({});await first
  assert.deepEqual(events,['updated','close'])
})

test('the actual dashboard template renders loaded and empty states without a browser',async()=>{
  const {compile}=require('@vue/compiler-dom')
  const {renderToString}=require('@vue/server-renderer')
  const descriptor=require('@vue/compiler-sfc').parse(fs.readFileSync('src/views/ledger/LedgerOverviewView.vue','utf8')).descriptor
  const render=new Function('Vue',compile(descriptor.template.content,{mode:'function'}).code)(vue)
  const metrics={income:'1000',expense:'400',surplus:'600',cash_in:'1000',cash_out:'1200',cash_flow:'-200'}
  for (const entries of [false,true]) {
    const state=evaluate('src/views/ledger/LedgerOverviewView.vue',{...vue,watch(){},onMounted(){},onUnmounted(){},ledgerApi:{},
      useRouter:()=>({}),useLedgerStore:()=>({accounts:[]}),useToastStore:()=>({})},null,true)
    state.data.value={period:{month:'2026-10',start:'2026-10-01',end:'2026-10-15',previous_start:'2026-09-01',previous_end:'2026-09-15'},
      currency:'THB',currencies:['THB'],as_of:'2026-10-15T05:00:00Z',metrics,comparison:metrics,liquid_balance:'5000',credit_debt:'400',pending_split_amount:'800',
      income_sources:[],expense_categories:[],budgets:[],accounts:[],daily:[],history:[],uncategorized_count:0,
      forecast:{as_of:'2026-10-15',bills:[],windows:{'7':{known_due:'0',remaining:'5000',pending_dynamic_count:0,conditional_amount:'0'}}},
      recent:entries ? [{id:'one',title:'Recorded',date:'2026-10-10',account_name:'Bank',transaction_type:'OUTFLOW',kind:'EXPENSE',gross_amount:'400'}] : [],largest_expenses:[]}
    const app=vue.createSSRApp({setup:()=>state,render})
    app.component('RouterLink',{props:['to'],setup:(_props,{slots})=>()=>vue.h('a',{},slots.default?.())})
    for (const name of ['TransactionModal','TransferModal','DashboardChart','DashboardCategories']) app.component(name,{render:()=>null})
    const html=await renderToString(app)
    assert.ok(html.includes('THB 1,000.00'))
    assert.ok(html.includes('THB 5,000.00'))
    assert.ok(html.includes(entries ? 'Recorded' : 'ยังไม่มีรายการที่บันทึกในช่วงนี้'))
    assert.ok(!html.includes('NaN'))
  }
})
