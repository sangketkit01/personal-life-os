/** Core types for the bilingual (EN / TH) i18n engine. */

export type AppLocale = 'en' | 'th'

export type TranslationParams = Record<string, string | number>

/** A single dynamic-phrase rule: regex match -> Thai translation. */
export interface PatternRule {
  /** Matched against the trimmed text node core. */
  pattern: RegExp
  /** Builds the Thai translation from the regex match. */
  translate: (match: RegExpMatchArray) => string
}

/** DOM attribute names that get reversibly translated. */
export type TranslatableAttr = 'placeholder' | 'title' | 'aria-label'
