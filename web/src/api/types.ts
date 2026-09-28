// Mirrors app/schemas/estimations.py — keep both in sync.

export type ProjectType = 'mobile_app' | 'web_saas' | 'internal_tool' | 'data_pipeline'
export type DetailLevel = 'summary' | 'medium' | 'detailed'
export type OutputFormat = 'phases_table' | 'line_items' | 'narrative'
/** Language the model answers in. The API falls back to 'es' for anything else. */
export type ResponseLanguage = 'es' | 'en'

/** What the form collects; the response language comes from the sidebar. */
export interface EstimationInput {
  description: string
  project_type: ProjectType
  detail_level: DetailLevel
  output_format: OutputFormat
}

export interface EstimationRequest extends EstimationInput {
  language: ResponseLanguage
}

export interface EstimationResponse {
  text: string
  prompt_version: string
}

export interface PromptContext {
  prompt_version: string
  examples_markdown: string
}

/** Payload of the SSE `done` event. */
export interface GenerationMeta {
  model?: string
  provider?: string
  input_tokens?: number | null
  output_tokens?: number | null
  latency_seconds?: number | null
  prompt_version: string
}

export type StreamEvent =
  | { type: 'token'; text: string }
  | { type: 'done'; meta: GenerationMeta }
  | { type: 'error'; detail: string }

export const DESCRIPTION_MIN = 20
export const DESCRIPTION_MAX = 2000

export const DEFAULT_RESPONSE_LANGUAGE: ResponseLanguage = 'es'

export const RESPONSE_LANGUAGES: { value: ResponseLanguage; label: string }[] = [
  { value: 'es', label: 'Español' },
  { value: 'en', label: 'English' },
]

export const PROJECT_TYPES: { value: ProjectType; label: string }[] = [
  { value: 'mobile_app', label: 'App móvil' },
  { value: 'web_saas', label: 'Web / SaaS' },
  { value: 'internal_tool', label: 'Herramienta interna' },
  { value: 'data_pipeline', label: 'Pipeline de datos' },
]

export const DETAIL_LEVELS: { value: DetailLevel; label: string }[] = [
  { value: 'summary', label: 'Resumen' },
  { value: 'medium', label: 'Medio' },
  { value: 'detailed', label: 'Detallado' },
]

export const OUTPUT_FORMATS: { value: OutputFormat; label: string }[] = [
  { value: 'phases_table', label: 'Tabla por fases' },
  { value: 'line_items', label: 'Partidas / line items' },
  { value: 'narrative', label: 'Narrativo' },
]
