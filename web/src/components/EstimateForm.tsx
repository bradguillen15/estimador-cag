import { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'

import {
  DESCRIPTION_MAX,
  DESCRIPTION_MIN,
  DETAIL_LEVELS,
  OUTPUT_FORMATS,
  PROJECT_TYPES,
} from '../api/types'
import type { DetailLevel, EstimationRequest, OutputFormat, ProjectType } from '../api/types'
import { Chevron } from './icons'

interface EstimateFormProps {
  busy: boolean
  onSubmit: (request: EstimationRequest) => void
}

export function EstimateForm({ busy, onSubmit }: EstimateFormProps) {
  const [description, setDescription] = useState('')
  const [projectType, setProjectType] = useState<ProjectType>('mobile_app')
  const [detailLevel, setDetailLevel] = useState<DetailLevel>('medium')
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('phases_table')

  const length = description.trim().length
  const valid = length >= DESCRIPTION_MIN && length <= DESCRIPTION_MAX

  const submit = () => {
    if (!valid || busy) return
    onSubmit({
      description: description.trim(),
      project_type: projectType,
      detail_level: detailLevel,
      output_format: outputFormat,
    })
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    submit()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="animate-enter rounded-[22px] bg-surface p-5 shadow-card [animation-delay:90ms] md:p-7"
    >
      <label htmlFor="description" className="mb-2 flex items-baseline justify-between text-[13px] font-medium">
        Descripción del proyecto
        <span className={`font-mono text-xs font-normal tabular-nums ${length > 0 && !valid ? 'text-danger' : 'text-faint'}`}>
          {length} / {DESCRIPTION_MAX}
          {length > 0 && length < DESCRIPTION_MIN && ` · mínimo ${DESCRIPTION_MIN}`}
        </span>
      </label>
      <textarea
        id="description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        onKeyDown={handleKeyDown}
        maxLength={DESCRIPTION_MAX}
        placeholder="Ej.: Necesitamos un MVP web de e-commerce con catálogo, carrito, pagos y panel de administración…"
        className={`${CONTROL} block min-h-[150px] resize-y px-3.5 py-3 leading-relaxed placeholder:text-faint`}
      />

      <div className="mt-5 grid gap-3.5 md:grid-cols-3">
        <Select id="project_type" label="Tipo de proyecto" value={projectType} options={PROJECT_TYPES} onChange={setProjectType} />
        <Select id="detail_level" label="Nivel de detalle" value={detailLevel} options={DETAIL_LEVELS} onChange={setDetailLevel} />
        <Select id="output_format" label="Formato de salida" value={outputFormat} options={OUTPUT_FORMATS} onChange={setOutputFormat} />
      </div>

      <div className="mt-6 flex items-center justify-between gap-4">
        <span className="hidden text-xs text-faint sm:inline">
          <Kbd>⌘</Kbd> <Kbd>↵</Kbd> para generar
        </span>
        <button
          type="submit"
          disabled={!valid || busy}
          className="ml-auto inline-flex h-11 cursor-pointer items-center gap-2.5 rounded-full bg-btn px-6 font-semibold text-btn-ink transition-[transform,opacity] duration-150 ease-out-strong focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-accent enabled:active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-35"
        >
          {busy && (
            <span
              aria-hidden="true"
              className="size-3.5 animate-spin rounded-full border-2 border-current border-r-transparent [animation-duration:600ms]"
            />
          )}
          {busy ? 'Generando…' : 'Generar estimación'}
        </button>
      </div>
    </form>
  )
}

const CONTROL =
  'w-full rounded-[14px] bg-field outline-none transition-shadow duration-150 hover:shadow-[0_0_0_1px_var(--line-strong)] focus:shadow-[0_0_0_1px_var(--accent),0_0_0_4px_var(--accent-soft)]'

interface SelectProps<T extends string> {
  id: string
  label: string
  value: T
  options: { value: T; label: string }[]
  onChange: (value: T) => void
}

function Select<T extends string>({ id, label, value, options, onChange }: SelectProps<T>) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-[13px] font-medium">
        {label}
      </label>
      <div className="relative">
        <select
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value as T)}
          className={`${CONTROL} h-[42px] cursor-pointer appearance-none pr-9 pl-3`}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value} className="bg-field text-ink">
              {option.label}
            </option>
          ))}
        </select>
        <Chevron className="pointer-events-none absolute top-1/2 right-3 size-3 -translate-y-1/2 text-muted" />
      </div>
    </div>
  )
}

function Kbd({ children }: { children: string }) {
  return <kbd className="rounded-[5px] bg-field px-1.5 py-px font-mono text-[11px] shadow-[0_0_0_1px_var(--line-strong)]">{children}</kbd>
}
