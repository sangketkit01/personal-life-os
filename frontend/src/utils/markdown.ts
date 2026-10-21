/**
 * Lightweight, zero-dependency, safe Markdown to HTML parser
 * Supports: Headers (h1-h4), bold, italic, code blocks, inline code,
 * bullet lists, blockquotes, horizontal rules, and links.
 */
export function renderMarkdown(raw: string): string {
  if (!raw) return ''

  // 1. Basic HTML sanitization
  let html = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 2. Fenced Code Blocks: ```code```
  html = html.replace(/```([\s\S]*?)```/g, (_match, code) => {
    return `<pre class="my-2 p-2.5 rounded bg-zinc-950 border border-zinc-800 text-[11px] font-mono text-zinc-300 overflow-x-auto"><code>${code.trim()}</code></pre>`
  })

  // 3. Inline Code: `code`
  html = html.replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-zinc-800 text-blue-300 font-mono text-[11px] border border-zinc-700/50">$1</code>')

  // 4. Headers: #, ##, ###, ####
  html = html.replace(/^#### (.*$)/gim, '<h4 class="text-xs font-semibold text-zinc-200 mt-2 mb-1">$1</h4>')
  html = html.replace(/^### (.*$)/gim, '<h3 class="text-sm font-semibold text-zinc-100 mt-3 mb-1">$1</h3>')
  html = html.replace(/^## (.*$)/gim, '<h2 class="text-base font-bold text-zinc-100 mt-3.5 mb-1.5 border-b border-zinc-800/60 pb-1">$1</h2>')
  html = html.replace(/^# (.*$)/gim, '<h1 class="text-lg font-bold text-zinc-50 mt-4 mb-2 border-b border-zinc-800 pb-1">$1</h1>')

  // 5. Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="text-zinc-100 font-semibold">$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em class="text-zinc-300 italic">$1</em>')

  // 6. Blockquotes: > quote
  html = html.replace(/^>\s+(.*$)/gim, '<blockquote class="border-l-2 border-blue-500/60 pl-3 py-0.5 text-zinc-400 italic my-1.5">$1</blockquote>')

  // 7. Horizontal Rules: ---
  html = html.replace(/^---$/gim, '<hr class="border-zinc-800 my-3"/>')

  // 8. Bullet points: - item or * item
  html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<li class="ml-4 list-disc text-zinc-300 my-0.5">$1</li>')

  // 9. Links: [label](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-400 hover:underline inline-flex items-center gap-0.5">$1</a>')

  // 10. Paragraph linebreaks (preserving spaces when not in block elements)
  html = html.replace(/\n\n+/g, '<div class="h-2"></div>')
  html = html.replace(/\n/g, '<br/>')

  return html
}
