const {test}=require('node:test')
const assert=require('node:assert/strict')
const fs=require('node:fs')
const ts=require('typescript')
const vue=require('vue')
const {parse}=require('@vue/compiler-sfc')

function evaluate(file,env,names,sfc=true) {
  const original=fs.readFileSync(file,'utf8')
  const source=sfc ? parse(original).descriptor.scriptSetup.content : original
  const tree=ts.createSourceFile(file+'.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS)
  for (const s of tree.statements) if (ts.isImportDeclaration(s) && s.moduleSpecifier.text==='lucide-vue-next') {
    for (const item of s.importClause.namedBindings.elements) env[item.name.text]=()=>null
  }
  names ||= tree.statements.flatMap(s=>ts.isVariableStatement(s) ? s.declarationList.declarations.filter(d=>ts.isIdentifier(d.name)).map(d=>d.name.text) : ts.isFunctionDeclaration(s)&&s.name ? [s.name.text] : [])
  const stripped=ts.createPrinter().printList(ts.ListFormat.MultiLine,ts.factory.createNodeArray(tree.statements.filter(s=>!ts.isImportDeclaration(s))),tree)
  const code=ts.transpileModule(stripped,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText
  return new Function(...Object.keys(env),'exports',code+';return {'+names.map(n=>`${n}:typeof ${n} !== 'undefined' ? ${n} : exports.${n}`).join(',')+'};')(...Object.values(env),{})
}
const messages=evaluate('src/i18n/messages.ts',{},['MESSAGES'],false).MESSAGES
const t=(key,params={})=>Object.entries(params).reduce((text,[key,value])=>text.replaceAll('{'+key+'}',value),messages.th[key] || key)
const base=()=>({...vue,t,onMounted(){},useBodyScrollLock(){},useToastStore:()=>({success(){},error(){}})})

test('shared portfolio creation remains blank, prevents duplicate creates and navigates to the created portfolio once',async()=>{
  let finish,count=0,lock
  const events=[]
  const m=evaluate('src/components/portfolio/CreatePortfolioModal.vue',{...base(),defineProps:()=>({isOpen:true,inline:true}),defineEmits:()=>(...args)=>events.push(args),
    useBodyScrollLock:fn=>{lock=fn},usePortfolioStore:()=>({createPortfolio:()=>{count++;return new Promise(resolve=>{finish=resolve})}})},['form','handleSubmit','errorMessage'])
  assert.equal(lock(),false)
  assert.equal(m.form.value.name,'');assert.equal(m.form.value.currency,'')
  await m.handleSubmit();assert.equal(count,0)
  m.form.value.name='Long term';await m.handleSubmit();assert.equal(count,0)
  m.form.value.currency='USD'
  const first=m.handleSubmit();await m.handleSubmit();assert.equal(count,1)
  finish({id:'created',name:'Long term'});await first
  assert.deepEqual(events.map(e=>e[0]),['created','close'])
  const paths=[]
  const page=evaluate('src/views/portfolio/PortfolioAccountCreateView.vue',{...base(),useRouter:()=>({push:path=>paths.push(path)})},['handleCreated','goBack'])
  page.handleCreated(events[0][1]);page.goBack()
  assert.deepEqual(paths,['/portfolio/accounts/created'])
})

test('editing a portfolio updates the existing id and can clear its description without creating another portfolio',async()=>{
  let finish,sent,id,count=0
  const events=[]
  const m=evaluate('src/components/portfolio/EditPortfolioModal.vue',{...base(),defineProps:()=>({isOpen:true,portfolio:{id:'existing',name:'Name',description:'Old description',currency:'USD',color:'#3B82F6'}}),
    defineEmits:()=>event=>events.push(event),usePortfolioStore:()=>({createPortfolio:()=>assert.fail('Editing must never create a portfolio'),
      updatePortfolio:(key,payload)=>{id=key;sent=payload;count++;return new Promise(resolve=>{finish=resolve})}})},['form','handleSubmit'])
  m.form.value.description=''
  const first=m.handleSubmit();await m.handleSubmit()
  assert.equal(count,1);assert.equal(id,'existing');assert.equal(sent.description,'')
  finish({id});await first
  assert.deepEqual(events,['saved','close'])
})

async function renderView(file,state,custom={}) {
  const {compile}=require('@vue/compiler-dom')
  const {renderToString}=require('@vue/server-renderer')
  const template=parse(fs.readFileSync(file,'utf8')).descriptor.template.content
  const render=new Function('Vue',compile(template,{mode:'function',prefixIdentifiers:true}).code)(vue)
  const app=vue.createSSRApp({setup:()=>({...state,t,getPortfolioColor:()=>''}),render})
  for (const tag of new Set([...template.matchAll(/<([A-Z]\w*)\b/g)].map(m=>m[1]))) if(tag!=='RouterLink') app.component(tag,custom[tag] || {render:()=>null})
  app.component('RouterLink',{props:['to'],setup:(_props,{slots})=>()=>vue.h('a',{},slots.default?.())})
  return renderToString(app)
}

test('portfolio detail opens the edit component with its actual portfolio and exposes deletion only in details',async()=>{
  let captured
  const portfolio={id:'existing',name:'Long term',currency:'USD',description:'',created_at:'2026-01-01',is_default:false}
  const state=evaluate('src/views/portfolio/PortfolioAccountDetailView.vue',{...base(),useRoute:()=>({params:{id:'existing'}}),useRouter:()=>({}),
    getPortfolioColor:()=>'',usePortfolioStore:()=>({portfolios:[portfolio],transactions:[],holdings:[]})})
  state.isLoading.value=false;state.activeTab.value='STRATEGY';state.accountOverview.value={holdings:[]}
  state.openEditModal()
  const html=await renderView('src/views/portfolio/PortfolioAccountDetailView.vue',state,{
    EditPortfolioModal:{props:['isOpen','portfolio'],setup:props=>{captured=props;return ()=>null}},
    CreatePortfolioModal:{render:()=>assert.fail('Details must not mount a creation form')}
  })
  assert.equal(captured.isOpen,true);assert.equal(captured.portfolio.id,'existing')
  assert.ok(html.includes('แก้ไขพอร์ต'));assert.ok(html.includes('ลบพอร์ต'))
  assert.ok(!/Brokerage Account|Sub-Account Basket|Account Dossier|โดสซิเอร์บัญชี/.test(html))
})

test('portfolio list has one create action and leaves edit/delete actions to portfolio details',async()=>{
  const portfolio={id:'existing',name:'Long term',currency:'USD',description:'',is_default:false}
  const state=evaluate('src/views/portfolio/PortfolioAccountsView.vue',{...base(),watch(){},useRoute:()=>({query:{}}),useRouter:()=>({}),
    getPortfolioColor:()=>'',usePortfolioStore:()=>({selectedPortfolioId:'existing',selectedAssetType:'ALL',displayCurrency:'USD',portfolios:[portfolio],holdings:[],transactions:[],overview:null})})
  const html=await renderView('src/views/portfolio/PortfolioAccountsView.vue',state)
  const buttons=[...html.matchAll(/<button\b[^>]*>([\s\S]*?)<\/button>/g)]
  assert.equal(buttons.filter(button=>button[1].replace(/<[^>]+>/g,'').includes('สร้างพอร์ต')).length,1)
  assert.ok(html.includes('ดูรายละเอียดพอร์ต'))
  assert.ok(!html.includes('แก้ไขพอร์ต'));assert.ok(!html.includes('ลบพอร์ต'))
})

test('overview portfolio cards go straight to details and breadcrumbs use portfolio wording only in that domain',()=>{
  const pushed=[]
  const state=evaluate('src/views/portfolio/PortfolioOverviewView.vue',{...base(),useRouter:()=>({push:path=>pushed.push(path)}),
    getPortfolioColor:()=>'',usePortfolioStore:()=>({setSelectedPortfolio(){}})},['goToPortfolio'])
  state.goToPortfolio('existing');state.goToPortfolio('ALL')
  assert.deepEqual(pushed,[{path:'/portfolio/accounts/existing'},{path:'/portfolio/accounts'}])
  const route=vue.reactive({path:'/portfolio/accounts/existing',name:'portfolio-accounts-detail',params:{id:'existing'},query:{}})
  const {useBreadcrumbs}=evaluate('src/composables/useBreadcrumbs.ts',{...vue,t,useRoute:()=>route},['useBreadcrumbs'],false)
  const result=useBreadcrumbs()
  assert.equal(result.breadcrumbs.value.at(-1).label,messages.th['crumb.portfolioDetails'])
  route.path='/ledger/accounts/existing';route.name='ledger-account-detail'
  assert.equal(result.breadcrumbs.value.at(-1).label,messages.th['crumb.accountStatement'])
})
