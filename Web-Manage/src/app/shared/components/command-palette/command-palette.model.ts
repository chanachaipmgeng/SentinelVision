import { Menu } from '../../services/nav.service';

export interface PaletteEntry {
  path: string;
  /** Menu title key (English source string). */
  key: string;
  /** Title in the current UI language. */
  label: string;
  /** Section heading in the current UI language. */
  section: string;
  icon?: string;
  /** Lower-cased search text: every known translation + path. */
  haystack: string;
}

/** Resolve a translation key across languages; returns all distinct non-empty values. */
export type TitleResolver = (key: string) => string[];

/**
 * Flatten an already permission-filtered menu tree into palette entries.
 * `resolveAll` returns every known translation of a key (e.g. th + en);
 * `resolveCurrent` returns the label in the active UI language.
 */
export function flattenMenu(
  items: readonly Menu[],
  resolveCurrent: (key: string) => string,
  resolveAll: TitleResolver,
): PaletteEntry[] {
  const out: PaletteEntry[] = [];
  const seen = new Set<string>();
  let section = '';

  const visit = (item: Menu, parentLabel: string) => {
    if (item.headTitle) {
      section = resolveCurrent(item.headTitle);
      return;
    }
    if (item.path && item.type !== 'sub' && !seen.has(item.path)) {
      seen.add(item.path);
      const key = item.title || item.path;
      const names = new Set<string>([key, ...resolveAll(key)]);
      const parentNames = parentLabel ? [parentLabel] : [];
      out.push({
        path: item.path,
        key,
        label: resolveCurrent(key),
        section: parentLabel || section,
        icon: item.icon,
        haystack: [...names, ...parentNames, item.path].join(' ').toLowerCase(),
      });
    }
    const childParent = item.title ? resolveCurrent(item.title) : parentLabel;
    for (const child of item.children || []) {
      visit(child, childParent);
    }
  };

  for (const item of items) {
    visit(item, '');
  }
  return out;
}

/**
 * Multi-token "every token must match" filter. Entries whose label starts with
 * the query rank first, then label matches, then path/translation matches.
 */
export function filterPaletteEntries(
  entries: readonly PaletteEntry[],
  query: string,
  limit = 12,
): PaletteEntry[] {
  const q = (query || '').trim().toLowerCase();
  if (!q) {
    return entries.slice(0, limit);
  }
  const tokens = q.split(/\s+/).filter(Boolean);
  const scored: { e: PaletteEntry; score: number; i: number }[] = [];
  entries.forEach((e, i) => {
    if (!tokens.every((t) => e.haystack.includes(t))) return;
    const label = e.label.toLowerCase();
    let score = 3;
    if (label.startsWith(q)) score = 0;
    else if (label.includes(q)) score = 1;
    else if (e.key.toLowerCase().includes(q)) score = 2;
    scored.push({ e, score, i });
  });
  scored.sort((a, b) => a.score - b.score || a.i - b.i);
  return scored.slice(0, limit).map((s) => s.e);
}

/** True when a keyboard event originates from a text-entry control. */
export function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el || !el.tagName) return false;
  const tag = el.tagName.toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
  return !!el.isContentEditable;
}

/** `g <key>` chord targets. */
export const CHORD_ROUTES: Record<string, string> = {
  d: '/company/dashboard',
  t: '/company/timestamp-log',
  a: '/company/approval-inbox',
  s: '/company/sentinel-center',
};
