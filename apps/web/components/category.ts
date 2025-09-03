export type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'

const MAP: Record<string, Variant> = {
  groceries: 'success',
  coffee: 'warning',
  restaurants: 'info',
  fast_food: 'danger',
  rideshare: 'info',
  gas: 'warning',
  shopping: 'default',
  pharmacy: 'info',
  utilities: 'info',
  telecom: 'info',
  insurance: 'neutral',
  bank_fees: 'danger',
  rent: 'neutral',
  income: 'success',
  subscriptions: 'default',
  food_delivery: 'warning',
  airfare: 'info',
  travel: 'info',
  p2p: 'default',
}

export function categoryVariant(cat?: string | null): Variant {
  if (!cat) return 'neutral'
  const key = cat.toLowerCase()
  return MAP[key] || 'default'
}

