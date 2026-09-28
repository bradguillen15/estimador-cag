import { useState } from 'react'

import { EstimateForm } from './components/EstimateForm'
import { EstimationResult } from './components/EstimationResult'
import { Sidebar } from './components/Sidebar'
import { useEstimation } from './hooks/useEstimation'
import { useResponseLanguage } from './hooks/useResponseLanguage'
import { useTheme } from './hooks/useTheme'

export default function App() {
  const [theme, setTheme] = useTheme()
  const [language, setLanguage] = useResponseLanguage()
  const [streaming, setStreaming] = useState(false)
  const { state, run } = useEstimation()
  const busy = state.status === 'loading' || state.status === 'streaming'

  return (
    <div className="grid min-h-screen md:grid-cols-[288px_1fr]">
      <Sidebar
        streaming={streaming}
        onStreamingChange={setStreaming}
        language={language}
        onLanguageChange={setLanguage}
        theme={theme}
        onThemeChange={setTheme}
      />

      <main className="min-w-0 px-4 pt-9 pb-20 md:px-12 md:pt-[76px] md:pb-32">
        <div className="mx-auto max-w-[740px]">
          <div className="mb-[18px] inline-flex animate-enter items-center gap-2 rounded-full bg-field py-1 pr-2.5 pl-1.5 font-mono text-[11.5px] text-muted shadow-[0_0_0_1px_var(--line)]">
            <span className="rounded-full bg-accent px-1.5 py-px text-btn-ink">CAG</span>
            Cache-Augmented Generation
          </div>
          <h1 className="animate-enter text-[34px] leading-[1.05] font-bold tracking-[-0.035em] [animation-delay:30ms] md:text-[42px]">
            Estimador de <em className="text-accent not-italic">software</em>
          </h1>
          <p className="mt-3.5 mb-9 max-w-[560px] animate-enter text-[15.5px] text-muted [animation-delay:60ms]">
            Describe el proyecto y elige tipo, detalle y formato. El formulario construye un{' '}
            <code className="rounded-md bg-accent-soft px-1.5 py-px font-mono text-[12.5px] text-ink">EstimationRequest</code> y lo
            envía al servicio.
          </p>

          <EstimateForm busy={busy} onSubmit={(input) => run({ ...input, language }, streaming)} />
          <EstimationResult state={state} />
        </div>
      </main>
    </div>
  )
}
