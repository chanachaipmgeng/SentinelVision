/** Browser geolocation helpers for the kiosk. */
export function hasFix(lat: number | null | undefined, lng: number | null | undefined): boolean {
  return lat != null && lng != null && !(lat === 0 && lng === 0);
}
