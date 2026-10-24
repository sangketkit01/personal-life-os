/**
 * Shared lucide icon presets for project / note icon pickers.
 * Persisted keys stay backward compatible (emoji glyphs are gone).
 */
import type { Component } from 'vue'
import {
  BookOpen,
  Briefcase,
  ClipboardList,
  FileText,
  House,
  Palette,
  Rocket,
  Target,
  TrendingUp,
  Wrench
} from 'lucide-vue-next'

export interface IconPreset {
  key: string
  label: string
  icon: Component
}

export const PROJECT_ICON_PRESETS: IconPreset[] = [
  { key: 'briefcase', label: 'Work', icon: Briefcase },
  { key: 'rocket', label: 'Launch', icon: Rocket },
  { key: 'target', label: 'Goal', icon: Target },
  { key: 'book', label: 'Study', icon: BookOpen },
  { key: 'wrench', label: 'Build', icon: Wrench },
  { key: 'home', label: 'Home', icon: House },
  { key: 'chart', label: 'Market', icon: TrendingUp },
  { key: 'palette', label: 'Creative', icon: Palette }
]

export const NOTE_ICON_PRESETS: IconPreset[] = [
  { key: 'file-text', label: 'Note', icon: FileText },
  { key: 'clipboard', label: 'Checklist', icon: ClipboardList },
  { key: 'target', label: 'Goal', icon: Target },
  { key: 'book', label: 'Study', icon: BookOpen },
  { key: 'rocket', label: 'Launch', icon: Rocket },
  { key: 'home', label: 'Home', icon: House },
  { key: 'chart', label: 'Market', icon: TrendingUp },
  { key: 'palette', label: 'Creative', icon: Palette }
]

const ALL_PRESETS = [...PROJECT_ICON_PRESETS, ...NOTE_ICON_PRESETS]

export function iconComponentFor(key: string): Component {
  return ALL_PRESETS.find(p => p.key === key)?.icon || FileText
}
