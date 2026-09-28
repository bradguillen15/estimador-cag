import ReactMarkdown from 'react-markdown'
import remarkBreaks from 'remark-breaks'
import remarkGfm from 'remark-gfm'

// GFM for the phases table. Breaks keep the LLM's closing "Total / Equipo / Duración" lines
// apart; hard-wrapped sources (the .j2 examples) should opt out so prose reflows.
const WITH_BREAKS = [remarkGfm, remarkBreaks]
const WITHOUT_BREAKS = [remarkGfm]

interface MarkdownProps {
  children: string
  className?: string
  breaks?: boolean
}

export function Markdown({ children, className = '', breaks = true }: MarkdownProps) {
  return (
    <div className={`md ${className}`}>
      <ReactMarkdown remarkPlugins={breaks ? WITH_BREAKS : WITHOUT_BREAKS}>{children}</ReactMarkdown>
    </div>
  )
}
