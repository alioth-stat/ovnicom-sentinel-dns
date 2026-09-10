import { useEffect, useState } from 'react'
import { usePrefersReducedMotion } from '@/hooks/use-prefers-reduced-motion'
import { GLOSSARY } from '@/lib/glossary'
import { STRINGS, type Lang } from '@/lib/i18n'
import { cn } from '@/lib/utils'

interface VisibilityPanelProps {
  open: boolean
  onClose: () => void
  lang: Lang
}

const TRANSITION_MS = 200 // keep in sync with the `duration-200` Tailwind classes below

// A closable drawer explaining, in plain language, what this system does
// with the data it sees and what every technical term on the dashboard
// means -- the transparency requirement is as much a demo/judging need
// (see README's "Requisito técnico") as a real UX one.
export function VisibilityPanel({ open, onClose, lang }: VisibilityPanelProps) {
  const t = STRINGS[lang].panel
  const glossary = GLOSSARY[lang]
  const reducedMotion = usePrefersReducedMotion()

  // Two-phase mount so the exit gets a transition too: `open` going false
  // immediately starts the closing transform, and only unmounts the drawer
  // once that transition has actually finished playing.
  const [shouldRender, setShouldRender] = useState(open)
  const [visible, setVisible] = useState(open)

  useEffect(() => {
    if (open) {
      setShouldRender(true)
      const raf = requestAnimationFrame(() => setVisible(true))
      return () => cancelAnimationFrame(raf)
    }
    setVisible(false)
    const timeout = setTimeout(() => setShouldRender(false), TRANSITION_MS)
    return () => clearTimeout(timeout)
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!shouldRender) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label={t.close}
        className={cn(
          'absolute inset-0 bg-black/60 transition-opacity ease-out',
          reducedMotion ? 'duration-0' : 'duration-200',
          visible ? 'opacity-100' : 'opacity-0',
        )}
        onClick={onClose}
      />
      <div
        className={cn(
          'relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-border bg-card p-6 shadow-2xl transition-transform ease-out md:p-8',
          reducedMotion ? 'duration-0' : 'duration-200',
          reducedMotion || visible ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-primary">{t.title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground active:scale-[0.97]"
          >
            {t.close} ✕
          </button>
        </div>

        <section className="mb-6">
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-foreground uppercase">{t.howItWorksHeading}</h3>
          <ol className="space-y-3 text-sm text-muted-foreground">
            {t.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>

        <p className="mb-8 rounded-md bg-accent/40 p-3 text-xs text-muted-foreground">{t.dataNote}</p>

        <section>
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-foreground uppercase">{t.glossaryHeading}</h3>
          <dl className="space-y-3 text-sm">
            {glossary.map(({ term, definition }) => (
              <div key={term}>
                <dt className="font-medium text-foreground">{term}</dt>
                <dd className="text-muted-foreground">{definition}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </div>
  )
}
