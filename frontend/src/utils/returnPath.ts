/** Preserve an authenticated app deep link without accepting external redirects. */
export function safeReturnPath(value: unknown): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u0020]/.test(value)) return '/'
  if (/^\/(login|register)(?:[/?#]|$)/.test(value)) return '/'
  return value
}
