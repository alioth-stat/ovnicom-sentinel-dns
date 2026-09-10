import { usePrefersReducedMotion } from '@/hooks/use-prefers-reduced-motion'
import { STEP_DURATION, STEP_EASE } from '@/lib/motion'

// Ordered (Bayer) dither, rendered once as an 8x8 SVG tile -- a nod to the
// halftone scan pattern on Philips diagnostic-monitor displays. It's the
// grain that separates this backdrop from the smooth frosted GlassPanel:
// felt texture behind, clean glass on top.
const BAYER_8X8 = [
  [0, 32, 8, 40, 2, 34, 10, 42],
  [48, 16, 56, 24, 50, 18, 58, 26],
  [12, 44, 4, 36, 14, 46, 6, 38],
  [60, 28, 52, 20, 62, 30, 54, 22],
  [3, 35, 11, 43, 1, 33, 9, 41],
  [51, 19, 59, 27, 49, 17, 57, 25],
  [15, 47, 7, 39, 13, 45, 5, 37],
  [63, 31, 55, 23, 61, 29, 53, 21],
]

const DITHER_TILE = (() => {
  // True ordered dithering: threshold the matrix into on/off dots at 1px
  // cells, not continuous per-cell opacity -- opacity-per-cell produced a
  // visible plaid/lattice instead of grain. One flat threshold (no input
  // gradient to dither) gives an even, irregular stipple.
  const threshold = 22 // ~34% of cells lit
  const dots = BAYER_8X8.flatMap((row, y) =>
    row.flatMap((v, x) => (v < threshold ? [`M${x} ${y}h1v1h-1z`] : [])),
  ).join('')
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='8' height='8'><path d='${dots}' fill='%231e3a5f'/></svg>`
  return { url: `url("data:image/svg+xml,${encodeURIComponent(svg)}")`, size: 8 }
})()

// px of dither drift per step index -- a transition cue tied to the step
// change (mirrors StepShell's translateX), not ambient looping motion, so it
// doesn't trip prefers-reduced-motion guidance for backgrounds that are
// visible the entire session. Skipped outright when reduced motion is on.
const SHIFT_PER_STEP = 360

interface BackgroundProps {
  step: number
}

// Decorative background: static gradient blobs plus a dither layer that
// pans right-to-left in lockstep with StepShell's slide, so the glass panel
// reads as sitting still while the world scrolls past underneath it.
export function Background({ step }: BackgroundProps) {
  const reducedMotion = usePrefersReducedMotion()

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-slate-50">
      <div className="absolute -top-32 -left-24 h-[600px] w-[600px] rounded-full bg-gradient-to-br from-sky-200 to-blue-400 opacity-40 blur-3xl" />
      <div className="absolute top-1/3 -right-40 h-[550px] w-[550px] rounded-full bg-gradient-to-br from-blue-100 to-sky-300 opacity-40 blur-3xl" />
      <div className="absolute -bottom-40 left-1/4 h-[500px] w-[500px] rounded-full bg-gradient-to-br from-sky-100 to-blue-200 opacity-30 blur-3xl" />
      <div
        className="absolute inset-0 opacity-[0.12] mix-blend-multiply"
        style={{
          backgroundImage: DITHER_TILE.url,
          backgroundSize: `${DITHER_TILE.size}px ${DITHER_TILE.size}px`,
          backgroundPositionX: reducedMotion ? 0 : -step * SHIFT_PER_STEP,
          transition: reducedMotion ? 'none' : `background-position-x ${STEP_DURATION}ms ${STEP_EASE}`,
        }}
      />
    </div>
  )
}
