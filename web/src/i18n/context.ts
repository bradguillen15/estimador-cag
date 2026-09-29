import { createContext } from 'react'

import type { Locale, MessageKey } from './messages'

type Translate = (key: MessageKey, vars?: Record<string, string | number>) => string

export const LocaleContext = createContext<{ locale: Locale; t: Translate } | null>(null)
