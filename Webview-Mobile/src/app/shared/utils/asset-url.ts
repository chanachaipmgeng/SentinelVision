/** Resolve static asset paths that work under /mobile/ base-href in production. */
export function assetUrl(path: string): string {
  const cleaned = path.replace(/^\.\/?/, '').replace(/^\//, '');
  const base = document.querySelector('base')?.getAttribute('href') || '/';
  const normalizedBase = base.endsWith('/') ? base : `${base}/`;
  return `${normalizedBase}${cleaned}`;
}
