/**
 * Shared helpers for rich inline HTML used inside NotionBlockEditor blocks.
 * Block content is sanitized inline HTML limited to safe formatting tags.
 */

const ALLOWED_TAGS = new Set([
  'B', 'STRONG', 'I', 'EM', 'U', 'S', 'STRIKE', 'DEL', 'CODE', 'A', 'SPAN', 'MARK', 'BR'
])

const ALLOWED_STYLE_PROPS = new Set(['color', 'background-color'])

function isSafeHref(href: string): boolean {
  return /^(https?:\/\/|mailto:)/i.test(href)
}

function cleanAttributes(el: Element): Element {
  const clone = el.cloneNode(false) as Element
  const tag = el.tagName

  for (const attr of Array.from(el.attributes)) {
    const name = attr.name.toLowerCase()
    const value = attr.value

    if (tag === 'A' && name === 'href' && isSafeHref(value)) {
      clone.setAttribute('href', value)
      clone.setAttribute('target', '_blank')
      clone.setAttribute('rel', 'noopener noreferrer')
    } else if ((tag === 'SPAN' || tag === 'MARK') && name === 'style') {
      const safeDecls = value
        .split(';')
        .map(decl => decl.trim())
        .filter(Boolean)
        .filter(decl => ALLOWED_STYLE_PROPS.has(decl.split(':')[0].trim().toLowerCase()))
        .join('; ')
      if (safeDecls) clone.setAttribute('style', safeDecls)
    } else if ((tag === 'SPAN' || tag === 'MARK') && (name === 'data-color' || name === 'data-bg')) {
      clone.setAttribute(name, value)
    }
  }
  return clone
}

function cleanChildren(source: Node, target: Node) {
  for (const node of Array.from(source.childNodes)) {
    if (node.nodeType === Node.TEXT_NODE) {
      target.appendChild(document.createTextNode(node.textContent || ''))
      continue
    }
    if (node.nodeType === Node.COMMENT_NODE) continue
    if (node.nodeType !== Node.ELEMENT_NODE) continue

    const el = node as Element

    // Some browsers emit <font color="..."> from execCommand('foreColor');
    // normalize it into an allowed <span style="color: ...">.
    if (el.tagName === 'FONT') {
      const span = document.createElement('span')
      const color = el.getAttribute('color')
      if (color) {
        span.setAttribute('style', `color: ${color}`)
      }
      target.appendChild(span)
      cleanChildren(el, span)
      continue
    }

    if (ALLOWED_TAGS.has(el.tagName)) {
      const clone = cleanAttributes(el)
      target.appendChild(clone)
      cleanChildren(el, clone)
    } else {
      // Unwrap disallowed tags but keep their text content
      cleanChildren(el, target)
    }
  }
}

/** Sanitize inline rich HTML down to a strict whitelist of tags and attributes. */
export function sanitizeRichHTML(html: string): string {
  if (!html) return ''
  const source = document.createElement('div')
  source.innerHTML = html
  const output = document.createElement('div')
  cleanChildren(source, output)
  return output.innerHTML
}

/** Strip all HTML tags and unescape entities to plain text. */
export function stripHtml(html: string): string {
  if (!html) return ''
  const div = document.createElement('div')
  div.innerHTML = html
  return (div.textContent || '').replace(/\s+/g, ' ').trim()
}

export function isEmptyHtml(html: string): boolean {
  return stripHtml(html) === ''
}
