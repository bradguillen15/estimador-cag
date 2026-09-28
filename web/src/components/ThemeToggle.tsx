import type { ReactNode } from 'react'

import type { Theme } from '../hooks/useTheme'

interface ThemeToggleProps {
  value: Theme
  onChange: (theme: Theme) => void
}

const OPTIONS: { value: Theme; label: string; icon: ReactNode }[] = [
  {
    value: 'light',
    label: 'Claro',
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" className="size-[13px]">
        <circle cx="8" cy="8" r="3" />
        <path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1" />
      </svg>
    ),
  },
  {
    value: 'dark',
    label: 'Oscuro',
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" className="size-[13px]">
        <path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7Z" />
      </svg>
    ),
  },
]

export function ThemeToggle({ value, onChange }: ThemeToggleProps) {
  return (
    <div role="radiogroup" aria-label="Tema" className="grid grid-cols-2 rounded-full bg-field p-[3px] shadow-[0_0_0_1px_var(--line)]">
      {OPTIONS.map((option) => (
        <label key={option.value} className="relative">
          <input
            type="radio"
            name="theme"
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
