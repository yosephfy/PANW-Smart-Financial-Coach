export const fmtCurrency = (n: number, currency = 'USD') =>
  new Intl.NumberFormat(undefined, { style: 'currency', currency, maximumFractionDigits: 2 }).format(n)

export const fmtPct = (n: number) => `${n.toFixed(2)}%`

