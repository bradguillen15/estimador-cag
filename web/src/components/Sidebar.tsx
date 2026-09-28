import { useEffect, useState } from 'react'

import { API_LABEL, checkHealth, getPromptContext } from '../api/client'
import type { PromptContext, ResponseLanguage } from '../api/types'
import type { Theme } from '../hooks/useTheme'
import { Chevron } from './icons'
import { LanguageToggle } from './LanguageToggle'
import { Markdown } from './Markdown'
import { ThemeToggle } from './ThemeToggle'

interface SidebarProps {
  streaming: boolean
  onStreamingChange: (streaming: boolean) => void
  language: ResponseLanguage
  onLanguageChange: (language: ResponseLanguage) => void
  theme: Theme
  onThemeChange: (theme: Theme) => void
}

export function Sidebar({ streaming, onStreamingChange, language, onLanguageChange, theme, onThemeChange }: SidebarProps) {
  return (
    <aside className="flex flex-col gap-7 border-b border-line bg-sidebar px-4 py-5 md:sticky md:top-0 md:h-screen md:gap-8 md:overflow-y-auto md:border-r md:border-b-0 md:px-[22px] md:py-7">
      <div className="flex items-center gap-2.5 font-semibold tracking-[-0.01em]">
        <span className="grid size-[26px] place-items-center rounded-[10px] bg-btn text-[13px] font-bold text-btn-ink">E</span>
        Estimador CAG
      </div>

      <section>
        <SectionTitle>API</SectionTitle>
        <ApiStatus />
        <label className="mt-3.5 flex cursor-pointer items-center justify-between gap-3 text-[13.5px]">
          Streaming (SSE)
          <input
            type="checkbox"
            role="switch"
            checked={streaming}
            onChange={(event) => onStreamingChange(event.target.checked)}
            className="relative h-[19px] w-8 flex-none cursor-pointer appearance-none rounded-full bg-faint transition-colors duration-150 after:absolute after:top-[2.5px] after:left-[2.5px] after:size-3.5 after:rounded-full after:bg-white after:shadow-sm after:transition-transform after:duration-200 after:ease-out-strong after:content-[''] checked:bg-btn checked:after:translate-x-[13px] checked:after:bg-btn-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-reduce:after:transition-none"
          />
        </label>
        <p className="mt-2 text-[12.5px] text-muted">
          {streaming ? 'SSE' : 'JSON'} — mismo formulario, distinto endpoint.
        </p>
      </section>

      <section>
        <SectionTitle>Contexto CAG</SectionTitle>
        <p className="text-[12.5px] text-muted">Ejemplos inyectados en el system prompt del servidor.</p>
        <CagExamples />
      </section>

      <div className="flex flex-col gap-7 md:mt-auto md:gap-6">
        <section>
          <SectionTitle>Idioma de respuesta</SectionTitle>
          <LanguageToggle value={language} onChange={onLanguageChange} />
          <p className="mt-2 text-[12.5px] text-muted">Se aplica a la siguiente estimación.</p>
        </section>

        <section>
          <SectionTitle>Apariencia</SectionTitle>
          <ThemeToggle value={theme} onChange={onThemeChange} />
        </section>
      </div>
    </aside>
  )
}

function SectionTitle({ children }: { children: string }) {
  return <h3 className="mb-3 text-[11px] font-semibold tracking-[0.09em] text-faint uppercase">{children}</h3>
}

type Health = 'checking' | 'up' | 'down'

function ApiStatus() {
  const [health, setHealth] = useState<Health>('checking')

  useEffect(() => {
    let active = true
    checkHealth().then((ok) => active && setHealth(ok ? 'up' : 'down'))
    return () => {
      active = false
    }
  }, [])

  const dot = {
    checking: 'bg-faint',
    up: 'bg-ok shadow-[0_0_0_3px_color-mix(in_srgb,var(--ok)_18%,transparent),0_0_10px_color-mix(in_srgb,var(--ok)_60%,transparent)]',
    down: 'bg-danger',
  }[health]
  const label = { checking: 'Comprobando API', up: 'API disponible', down: 'API no disponible' }[health]

  return (
    <span
      title={label}
      className="inline-flex max-w-full items-center gap-2 rounded-full bg-field px-2.5 py-[5px] font-mono text-xs text-muted shadow-[0_0_0_1px_var(--line)]"
    >
      <i className={`size-1.5 flex-none rounded-full ${dot}`} aria-hidden="true" />
      <span className="truncate">{API_LABEL}</span>
      <span className="sr-only">{label}</span>
    </span>
  )
}

function CagExamples() {
  const [context, setContext] = useState<PromptContext | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getPromptContext()
      .then(setContext)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))
  }, [])

  return (
    <details className="group mt-3 rounded-[14px] bg-field shadow-[0_0_0_1px_var(--line)]">
      <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2.5 text-[13.5px] font-medium [&::-webkit-details-marker]:hidden">
        <span>
          Ejemplos estáticos
          {context && <span className="ml-2 font-mono text-[11px] font-normal text-faint">{context.prompt_version}</span>}
        </span>
        <Chevron className="size-3 text-faint transition-transform duration-200 ease-out-strong group-open:rotate-180 motion-reduce:transition-none" />
      </summary>
      <div className="max-h-[46vh] overflow-y-auto border-t border-line px-3 pt-1 pb-3">
        {error && <p className="pt-2 text-xs text-danger">{error}</p>}
        {!error && !context && <p className="pt-2 text-xs text-faint">Cargando ejemplos…</p>}
        {context && <Markdown className="md-compact" breaks={false}>{context.examples_markdown}</Markdown>}
      </div>
    </details>
  )
}
