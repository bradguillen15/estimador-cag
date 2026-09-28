import { RESPONSE_LANGUAGES } from '../api/types'
import type { ResponseLanguage } from '../api/types'
import { SegmentedControl } from './SegmentedControl'
import type { SegmentOption } from './SegmentedControl'

interface LanguageToggleProps {
  value: ResponseLanguage
  onChange: (language: ResponseLanguage) => void
}

const OPTIONS: SegmentOption<ResponseLanguage>[] = RESPONSE_LANGUAGES.map(({ value, label }) => ({
  value,
  label,
  icon: (
    <span aria-hidden="true" className="font-mono text-[10px] tracking-wide uppercase opacity-70">
      {value}
    </span>
  ),
}))

export function LanguageToggle({ value, onChange }: LanguageToggleProps) {
  return (
    <SegmentedControl name="response-language" label="Idioma de respuesta" value={value} options={OPTIONS} onChange={onChange} />
  )
}
