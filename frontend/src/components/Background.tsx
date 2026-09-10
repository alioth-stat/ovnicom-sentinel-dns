import { usePrefersReducedMotion } from '@/hooks/use-prefers-reduced-motion'
import GradientWaves from './GradientWaves'

// Decorative backdrop: a raymarched gradient-wave shader (React Bits'
// GradientWaves, via `ogl`) tinted to the app's own palette -- fades from the
// dark navy background color into a slightly lighter blue wave body, with a
// light-blue crest highlight. Skipped entirely under prefers-reduced-motion
// (it's a continuously-animated WebGL canvas, not a one-off transition).
export function Background() {
  const reducedMotion = usePrefersReducedMotion()

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-background">
      {!reducedMotion && (
        <GradientWaves
          horizonColor="#050a16"
          waveColor="#12233d"
          crestColor="#7dd3fc"
          speed={0.12}
          amplitude={2.2}
          waveScale={0.55}
          swell={22}
          turbulence={14}
          brightness={1.1}
          opacity={0.85}
          mouseInteraction
          parallaxStrength={0.4}
          grain
          grainIntensity={0.03}
        />
      )}
    </div>
  )
}
