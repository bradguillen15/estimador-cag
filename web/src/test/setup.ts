import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

import { setLocale } from '../i18n/locale'

afterEach(() => {
  cleanup()
  localStorage.clear()
  setLocale('es')
  document.documentElement.lang = 'es'
  delete document.documentElement.dataset.theme
})
