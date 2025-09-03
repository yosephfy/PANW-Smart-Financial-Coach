import React from 'react'

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'

export function Badge({ children, variant = 'neutral', title }: { children: React.ReactNode; variant?: Variant; title?: string }) {
  const cls = {
    default: 'bg-slate-700 text-slate-100 border-slate-600',
    success: 'bg-emerald-700/60 text-emerald-100 border-emerald-600/60',
    warning: 'bg-amber-700/60 text-amber-100 border-amber-600/60',
    danger: 'bg-red-700/60 text-red-100 border-red-600/60',
    info: 'bg-blue-700/60 text-blue-100 border-blue-600/60',
    neutral: 'bg-slate-700/60 text-slate-100 border-slate-600/60',
  }[variant]
  return (
    <span title={title} className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${cls}`}>
      {children}
    </span>
  )
}

