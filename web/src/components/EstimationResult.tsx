import type { ReactNode } from 'react'

import type { GenerationMeta } from '../api/types'
import type { EstimationState } from '../hooks/useEstimation'
import { useT } from '../i18n/useLocale'
import { Markdown } from './Markdown'

export function EstimationResult({ state }: { state: EstimationState }) {
  const t = useT()

  if (state.status === 'idle') return null

  if (state.status === 'error') {
    return (
      <div
        role="alert"
        className="mt-5 animate-enter rounded-[14px] bg-danger-soft px-4 py-3.5 text-[13.5px] text-danger shadow-[0_0_0_1px_color-mix(in_srgb,var(--danger)_25%,transparent)]"
      >
        {state.error}
      </div>
    )
  }

  return (
    <section
      className="mt-12 animate-enter"
      aria-labelledby="estimation-heading"
      aria-live="polite"
      aria-busy={state.status !== 'done'}
    >
      <div className="mb-3.5 flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="estimation-heading" className="text-[26px] font-bold tracking-[-0.03em]">
          {t('result.heading')}
        </h2>
        {state.meta && <MetaChips meta={state.meta} />}
      </div>
      <article className="rounded-[22px] bg-surface p-5 shadow-card md:p-7">
        {state.status === 'loading' ? (
          <Skeleton label={t('result.generating')} />
        ) : (
          <Markdown className={state.status === 'streaming' ? 'caret' : ''}>{state.text}</Markdown>
        )}
      </article>
    </section>
  )
}

function MetaChips({ meta }: { meta: GenerationMeta }) {
  const chips: ReactNode[] = [
    <>
      prompt_version <b className="font-medium text-ink">{meta.prompt_version}</b>
    </>,
  ]
  if (meta.model) chips.push(meta.model)
  if (meta.input_tokens != null && meta.output_tokens != null) {
    chips.push(`${meta.input_tokens}→${meta.output_tokens} tok${meta.latency_seconds != null ? ` · ${meta.latency_seconds.toFixed(2)}s` : ''}`)
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {chips.map((chip, index) => (
        <span key={index} className="rounded-full bg-field px-[9px] py-[3px] font-mono text-[11.5px] text-muted shadow-[0_0_0_1px_var(--line)]">
          {chip}
        </span>
      ))}
    </div>
  )
}

function Skeleton({ label }: { label: string }) {
  const bar = 'h-3 rounded-md bg-[linear-gradient(90deg,var(--accent-soft),transparent_60%,var(--accent-soft))] bg-size-[200%_100%] animate-shimmer'
  return (
    <div className="grid gap-2.5" aria-label={label}>
      <span className={`${bar} h-[18px] w-[45%]`} />
      <span className={`${bar} w-[90%]`} />
      <span className={`${bar} w-3/4`} />
      <span className={`${bar} w-[82%]`} />
    </div>
  )
}
