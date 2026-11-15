/** Shared reduced-motion helper for router config and motion directives. */
export function preferReducedMotion(): boolean {
  return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
}
