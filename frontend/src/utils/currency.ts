/**
 * Currency symbol helper.
 * Returns the display symbol for a currency code.
 */
export function currencySymbol(code?: string | null): string {
  return (code || '').toUpperCase() === 'USD' ? '$' : '\u0e3f'
}

/**
 * Format an amount with the correct currency symbol.
 */
export function formatCurrency(amount: number | string | null | undefined, currency?: string | null): string {
  const num = Number(amount || 0)
  return `${currencySymbol(currency)}${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
