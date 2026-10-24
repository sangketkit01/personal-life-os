/**
 * Reversible DOM translator: walks text nodes + translatable attributes and
 * swaps English chrome strings to Thai (or restores the original English).
 *
 * - WeakMap-backed originals survive repeated passes and Vue re-renders.
 * - User content is never touched: contenteditable areas, rich-editor blocks,
 *   code/pre/textarea, [data-no-i18n], plus anything without a dictionary
 *   match (numbers, currency, tickers, emails, URLs, arbitrary user text).
 */
import type { AppLocale, TranslatableAttr } from './types'
import { translatePhraseToThai } from './dictionaries'

const originalTextMap = new WeakMap<Text, string>()
const lastTextMap = new WeakMap<Text, string>()
const originalAttrMap = new WeakMap<Element, Record<string, string>>()
const lastAttrMap = new WeakMap<Element, Record<string, string>>()

const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE', 'TEXTAREA', 'NOSCRIPT', 'SVG'])

const SKIP_SELECTOR = [
  '[contenteditable="true"]',
  '.rich-editable',
  '[data-no-i18n]',
  'pre',
  'code',
  'textarea',
  'svg'
].join(', ')

const TRANSLATABLE_ATTRS: TranslatableAttr[] = ['placeholder', 'title', 'aria-label']

let activeLocale: AppLocale = 'en'
let observer: MutationObserver | null = null
let rafHandle: number | null = null
let isApplying = false

function shouldSkipElement(el: Element | null): boolean {
  if (!el) return true
  const tag = el.tagName
  if (SKIP_TAGS.has(tag)) return true
  if (el.closest(SKIP_SELECTOR)) return true
  return false
}

function processTextNode(node: Text, locale: AppLocale) {
  const parent = node.parentElement
  if (!parent || shouldSkipElement(parent)) return

  const current = node.nodeValue ?? ''
  if (!current.trim()) return

  // Vue re-rendered fresh content since our last write: refresh the original.
  if (!originalTextMap.has(node) || current !== lastTextMap.get(node)) {
    originalTextMap.set(node, current)
  }
  const sourceEn = originalTextMap.get(node) ?? current

  if (locale === 'en') {
    if (current !== sourceEn) {
      node.nodeValue = sourceEn
    }
    lastTextMap.set(node, sourceEn)
    return
  }

  // Preserve the surrounding whitespace of the ORIGINAL English node
  const leading = sourceEn.match(/^\s*/)?.[0] ?? ''
  const trailing = sourceEn.match(/\s*$/)?.[0] ?? ''
  const core = sourceEn.trim()
  const translatedCore = translatePhraseToThai(core)
  if (translatedCore === null) {
    // No dictionary match (numbers, currency, tickers, user content) - leave as is
    lastTextMap.set(node, current)
    return
  }

  const translated = leading + translatedCore + trailing
  if (translated !== current) {
    node.nodeValue = translated
  }
  lastTextMap.set(node, translated)
}

function processAttributes(el: Element, locale: AppLocale) {
  if (shouldSkipElement(el)) return

  for (const attr of TRANSLATABLE_ATTRS) {
    const current = el.getAttribute(attr)
    if (!current || !current.trim()) continue

    const originals = originalAttrMap.get(el) || {}
    const lastTranslated = lastAttrMap.get(el) || {}
    // Vue changed the attribute since our last write: refresh the original
    if (!(attr in originals) || (current !== originals[attr] && current !== lastTranslated[attr])) {
      originalAttrMap.set(el, { ...originals, [attr]: current })
    }

    const sourceEn = (originalAttrMap.get(el) || {})[attr] ?? current

    if (locale === 'en') {
      if (current !== sourceEn) {
        el.setAttribute(attr, sourceEn)
      }
      lastAttrMap.set(el, { ...(lastAttrMap.get(el) || {}), [attr]: sourceEn })
      continue
    }

    const translatedCore = translatePhraseToThai(sourceEn.trim())
    if (translatedCore === null) continue
    if (translatedCore !== current) {
      el.setAttribute(attr, translatedCore)
    }
    lastAttrMap.set(el, { ...(lastAttrMap.get(el) || {}), [attr]: translatedCore })
  }
}

function walkAndTranslate(locale: AppLocale) {
  // Text nodes (snapshot first - mutating nodeValue during a live walk is unsafe)
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  const textNodes: Text[] = []
  let node = walker.nextNode() as Text | null
  while (node) {
    textNodes.push(node)
    node = walker.nextNode() as Text | null
  }
  for (const textNode of textNodes) {
    processTextNode(textNode, locale)
  }

  // Translatable attributes
  const attrTargets = document.body.querySelectorAll<Element>('[placeholder], [title], [aria-label]')
  for (const el of attrTargets) {
    processAttributes(el, locale)
  }
}

/** Translate (or restore) the whole document for the given locale. */
export function applyDomTranslation(locale: AppLocale) {
  activeLocale = locale
  if (!document.body) return
  isApplying = true
  try {
    walkAndTranslate(locale)
  } finally {
    isApplying = false
  }
}

/** Observe Vue-driven DOM changes and re-translate with an rAF debounce. */
export function installI18nObserver() {
  if (observer) return
  observer = new MutationObserver((mutations) => {
    if (isApplying) return
    if (rafHandle !== null) return

    // Skip pure attribute flickers we caused ourselves; only react to real changes
    const relevant = mutations.some(m =>
      m.type === 'childList' ||
      m.type === 'characterData' ||
      (m.type === 'attributes' && m.target instanceof Element &&
        !m.target.closest(SKIP_SELECTOR))
    )
    if (!relevant) return

    rafHandle = requestAnimationFrame(() => {
      rafHandle = null
      applyDomTranslation(activeLocale)
    })
  })
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    attributeFilter: ['placeholder', 'title', 'aria-label']
  })
}
