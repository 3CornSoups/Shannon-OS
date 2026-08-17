import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import nginx from 'highlight.js/lib/languages/nginx'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'
import dockerfile from 'highlight.js/lib/languages/dockerfile'
import sql from 'highlight.js/lib/languages/sql'
import ini from 'highlight.js/lib/languages/ini'
import plaintext from 'highlight.js/lib/languages/plaintext'
import css from 'highlight.js/lib/languages/css'
import shell from 'highlight.js/lib/languages/shell'
import typescript from 'highlight.js/lib/languages/typescript'
import markdown_lang from 'highlight.js/lib/languages/markdown'

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('sh', shell)
hljs.registerLanguage('shell', shell)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('nginx', nginx)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('yml', yaml)
hljs.registerLanguage('dockerfile', dockerfile)
hljs.registerLanguage('docker', dockerfile)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('ini', ini)
hljs.registerLanguage('conf', ini)
hljs.registerLanguage('plaintext', plaintext)
hljs.registerLanguage('text', plaintext)
hljs.registerLanguage('css', css)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('markdown', markdown_lang)
hljs.registerLanguage('md', markdown_lang)

marked.setOptions({
  gfm: true,
  breaks: true,
})

// 自定义 code renderer：使用 highlight.js 同步高亮
const renderer = new marked.Renderer()
renderer.code = function ({ text, lang, escaped }) {
  // 如果指定了语言且 hljs 支持，则高亮
  const language = lang && hljs.getLanguage(lang) ? lang : null

  if (language) {
    try {
      const highlighted = hljs.highlight(text, { language }).value
      return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
    } catch (e) {
      // 高亮失败则回退到无高亮
    }
  }

  // 没有指定语言或语言不支持：自动检测
  try {
    const result = hljs.highlightAuto(text, { language: language ? [language] : undefined })
    if (result.relevance > 3) {
      return `<pre><code class="hljs language-${result.language || ''}">${result.value}</code></pre>`
    }
  } catch (e) {
    // 自动检测失败则纯文本
  }

  // 最后回退：纯文本代码块
  const escapedText = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
  return `<pre><code class="hljs">${escapedText}</code></pre>`
}

marked.setOptions({ renderer })

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
