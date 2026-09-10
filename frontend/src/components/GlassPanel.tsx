import type { ReactNode } from 'react'
import GlassSurface from './GlassSurface'

interface GlassPanelProps {
  children: ReactNode
  className?: string
}

// The one floating glass surface in the app, built on React Bits' GlassSurface
// (SVG backdrop-displacement glassmorphism, with a CSS blur fallback for
// browsers that don't support it). height="auto" works because GlassSurface's
// own ResizeObserver re-measures and rebuilds its displacement map whenever
// content height changes (e.g. the alerts table gaining/losing rows).
export function GlassPanel({ children, className }: GlassPanelProps) {
  return (
    <GlassSurface
      width="100%"
      height="auto"
      borderRadius={24}
      backgroundOpacity={0.1}
      saturation={1.6}
      blur={14}
      className={className}
    >
      {children}
    </GlassSurface>
  )
}
