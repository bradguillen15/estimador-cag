export function Chevron({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 12 12" fill="none" aria-hidden="true" className={className}>
      <path d="M3 4.5 6 7.5l3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

/** Measuring ruler with tick marks: "sizing the scope". Decorative, used in the brand badge. */
export function RulerMeasure({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden="true" className={className}>
      <rect x="1.5" y="5" width="13" height="6" rx="1.2" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M4.5 5v2.5M7 5v1.6M9.5 5v2.5M12 5v1.6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}
