import { marked } from 'marked'

marked.setOptions({
  gfm: true,
  breaks: true,
})

// Basic XSS sanitize: strip <script>, event handlers, and javascript: URLs
function sanitize(html) {
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<script\b[^>]*\/>/gi, '')
    .replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
    .replace(/\son\w+\s*=\s*'[^']*'/gi, '')
    .replace(/\son\w+\s*=\s*\S+/gi, '')
    .replace(/href\s*=\s*"javascript:[^"]*"/gi, 'href="#"')
    .replace(/href\s*=\s*'javascript:[^']*'/gi, 'href="#"')
}

export function renderMarkdown(text) {
  if (!text) return ''
  const html = marked.parse(text)
  return sanitize(html)
}
