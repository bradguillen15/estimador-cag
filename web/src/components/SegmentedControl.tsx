import type { ReactNode } from 'react'

export interface SegmentOption<T extends string> {
  value: T
  label: string
  icon?: ReactNode
}

interface SegmentedControlProps<T extends string> {
  /** Radio group name; must be unique on the page. */
  name: string
  label: string
  value: T
  options: SegmentOption<T>[]
  onChange: (value: T) => void
}

/** Pill-shaped radio group used for the sidebar preferences (theme, response language). */
export function SegmentedControl<T extends string>({ name, label, value, options, onChange }: SegmentedControlProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="grid auto-cols-fr grid-flow-col rounded-full bg-field p-[3px] shadow-[0_0_0_1px_var(--line)]"
    >
      {options.map((option) => (
        <label key={option.value} className="relative">
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
            className="peer absolute opacity-0"
          />
          <span className="flex h-7 cursor-pointer items-center justify-center gap-1.5 rounded-full text-[12.5px] text-muted transition-colors duration-150 peer-checked:bg-accent-soft peer-checked:text-accent peer-checked:shadow-[0_0_0_1px_color-mix(in_srgb,var(--accent)_35%,transparent)] peer-focus-visible:outline-2 peer-focus-visible:outline-offset-1 peer-focus-visible:outline-accent hover:text-ink">
            {option.icon}
            {option.label}
          </span>
        </label>
      ))}
    </div>
  )
}
