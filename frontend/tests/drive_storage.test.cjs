const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const ts = require('typescript')
const vue = require('vue')
const pinia = require('pinia')

function evaluate(file, env, names, sfc = false) {
  let source = fs.readFileSync(file, 'utf8')
  if (sfc) source = require('@vue/compiler-sfc').parse(source).descriptor.scriptSetup.content
  const tree = ts.createSourceFile(file + '.ts', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
  source = ts.createPrinter().printList(ts.ListFormat.MultiLine, ts.factory.createNodeArray(tree.statements.filter(s => !ts.isImportDeclaration(s))), tree)
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const bindings = names.map(name => `${name}: typeof ${name} !== 'undefined' ? ${name} : exports.${name}`).join(',')
  return new Function(...Object.keys(env), 'exports', output + '\nreturn {' + bindings + '};')(...Object.values(env), {})
}

function harness(overrides = {}) {
  pinia.setActivePinia(pinia.createPinia())
  const calls = { initiate: [], complete: [], delete: [] }
  const row = { id: 'registered', drive_file_id: 'drive1', domain: 'finance', target_id: 'bill1',
    category: 'SLIP', payment_history_id: '', pending_payment: true }
  const env = { ...vue, ...pinia,
    useToastStore: () => ({ error() {}, success() {} }),
    getGoogleDriveStatus: async () => ({ is_connected: true }),
    initiateResumableUpload: async p => { calls.initiate.push(p); return { upload_url: 'fixture', upload_token: 'proof' } },
    uploadBytesDirectToGoogle: async () => ({ id: 'drive1' }),
    completeResumableUpload: async p => { calls.complete.push(p); return row },
    getFileByDriveId: async () => null,
    deleteFileByDriveId: async (...args) => calls.delete.push(args),
    getGoogleAuthUrl() {}, googleAuthCallback() {}, disconnectGoogleDrive() {},
    setTimeout: fn => { fn(); return 1 },
    ...overrides }
  const { useStorageStore } = evaluate('src/stores/storage.ts', env, ['useStorageStore'])
  return { store: useStorageStore(), calls, row }
}
const file = { name: 'receipt.png', type: 'image/png', size: 10 }
const options = { category: 'SLIP', defer_attachment: true }

test('upload sends the same target, payment context and category before and after transfer', async () => {
  const { store, calls } = harness()
  await store.uploadDirect(file, 'finance', 'bill1', undefined, options)
  assert.equal(calls.initiate[0].target_id, 'bill1')
  assert.equal(calls.initiate[0].category, 'SLIP')
  assert.equal(calls.initiate[0].defer_attachment, true)
  assert.equal(calls.complete[0].target_id, 'bill1')
  assert.equal(calls.complete[0].upload_token, 'proof')
  assert.equal(calls.complete[0].category, 'SLIP')
  assert.equal(calls.delete.length, 0)
})

test('a dropped registration response recovers only a file with matching context', async () => {
  const saved = { id: 'registered', domain: 'finance', target_id: 'bill1', category: 'SLIP', payment_history_id: '', pending_payment: true }
  const { store, calls } = harness({ completeResumableUpload: async () => { throw new Error('Response lost') }, getFileByDriveId: async () => saved })
  const result = await store.uploadDirect(file, 'finance', 'bill1', undefined, options)
  assert.equal(result.id, 'registered')
  assert.equal(calls.delete.length, 0)
})

test('mismatched registered metadata is never presented as upload success', async () => {
  const { store, calls } = harness({ completeResumableUpload: async () => { throw new Error('Invalid target') },
    getFileByDriveId: async () => ({ id: 'registered', domain: 'finance', target_id: 'wrong-bill' }) })
  await assert.rejects(store.uploadDirect(file, 'finance', 'bill1', undefined, options), /Invalid target/)
  assert.deepEqual(calls.delete, [['drive1', 'proof']])
})

test('an unavailable registration check still attempts cleanup using the signed session', async () => {
  const { store, calls } = harness({ completeResumableUpload: async () => { throw new Error('Unavailable') },
    getFileByDriveId: async () => { throw new Error('Still unavailable') } })
  await assert.rejects(store.uploadDirect(file, 'finance', 'bill1', undefined, options), /Unavailable/)
  assert.deepEqual(calls.delete, [['drive1', 'proof']])
  assert.equal(store.uploadProgress, null)
})

test('file management waits for an explicit preview and sends its token when moving', async () => {
  const calls = []
  const row = { id: 'row1', file_name: 'receipt.png', folder_path: [], references: [], unreferenced: true }
  const env = { ...vue, locale: vue.ref('en'), useToastStore: () => ({ success() {} }),
    deleteDriveFile: async () => assert.fail('moving must not delete files'),
    api: { get: async url => {
      calls.push(['get', url]); return { data: url.includes('organization')
        ? { state: 'move', move_token: 'preview-proof', current_parents: ['old'], destination: ['Finance', 'Rent'] }
        : { results: [row], count: 1, page: 1 } }
    }, post: async (url, data) => calls.push(['post', url, data]) } }
  const m = evaluate('src/components/settings/DriveFileManager.vue', env,
    ['load', 'inspect', 'askMove', 'execute', 'action', 'previews'], true)
  assert.equal(calls.length, 0)
  await m.load(1)
  assert.equal(calls.some(c => c[1].includes('organization')), false)
  await m.inspect(row)
  assert.equal(calls.some(c => c[0] === 'post'), false)
  m.askMove(row)
  assert.equal(calls.some(c => c[0] === 'post'), false)
  await m.execute()
  assert.deepEqual(calls.find(c => c[0] === 'post'), ['post', '/storage/files/row1/organization/', { move_token: 'preview-proof' }])
  assert.equal(m.action.value, null)
})
