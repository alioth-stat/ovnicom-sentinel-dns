import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface GlassPanelProps {
  children: ReactNode
  className?: string
}

// The one floating glass surface in the app. Nothing should stack
// blur-on-blur on top of this -- content inside stays solid-colored for
// legibility over the translucent material. No "Glass Surface" primitive
// exists in the shadcn registry (checked), so this is hand-built: heavy
// blur + saturation for a surface this size, a brighter top edge and an
// inset highlight so it reads as light catching real glass, not a flat tint.
export function GlassPanel({ children, className }: GlassPanelProps) {
  return (
    <div
      className={cn(
        'w-full max-w-xl rounded-2xl border border-white/40 border-t-white/80 bg-gradient-to-b from-white/16 to-white/6 p-8 backdrop-blur-2xl backdrop-saturate-150 shadow-[0_24px_70px_-24px_rgba(15,23,42,0.35),inset_0_1px_0_rgba(255,255,255,0.65)] md:p-10',
        className,
      )}
    >
      {children}
    </div>
  )
}
