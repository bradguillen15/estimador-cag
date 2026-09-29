/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Optional absolute API origin. Leave unset to use the same origin (dev proxy / FastAPI). */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
