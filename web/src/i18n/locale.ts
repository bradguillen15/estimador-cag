import { DEFAULT_RESPONSE_LANGUAGE } from '../api/types'
import type { Locale, MessageKey } from './messages'
import { translate } from './messages'

/** Module locale for non-React callers (e.g. api/client). Synced by LocaleProvider. */
let currentLocale: Locale = DEFAULT_RESPONSE_LANGUAGE

export function getLocale(): Locale {
  return currentLocale
}

export function setLocale(locale: Locale): void {
  currentLocale = locale
}

/** Translate using the current module locale. Prefer useT() inside React. */
export function t(key: MessageKey, vars?: Record<string, string | number>): string {
  return translate(currentLocale, key, vars)
}
