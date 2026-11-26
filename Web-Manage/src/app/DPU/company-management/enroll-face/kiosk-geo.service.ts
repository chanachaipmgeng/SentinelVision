/** Browser geolocation and geofence distance helpers for the face kiosk. */
export function hasFix(lat: number | null | undefined, lng: number | null | undefined): boolean {
  return lat != null && lng != null && !(lat === 0 && lng === 0);
}

function toRad(value: number): number {
  return (value * Math.PI) / 180;
}

/** Haversine great-circle distance in kilometers between two WGS84 coordinates. */
export function haversineDistanceKm(
  lat1: number | string,
  lon1: number | string,
  lat2: number | string,
  lon2: number | string,
): number {
  const nLat1 = typeof lat1 === 'number' ? lat1 : parseFloat(lat1);
  const nLon1 = typeof lon1 === 'number' ? lon1 : parseFloat(lon1);
  const nLat2 = typeof lat2 === 'number' ? lat2 : parseFloat(lat2);
  const nLon2 = typeof lon2 === 'number' ? lon2 : parseFloat(lon2);
  if (![nLat1, nLon1, nLat2, nLon2].every((v) => Number.isFinite(v))) {
    return Number.POSITIVE_INFINITY;
  }
  const earthRadiusKm = 6371;
  const dLat = toRad(nLat2 - nLat1);
  const dLon = toRad(nLon2 - nLon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(nLat1)) *
      Math.cos(toRad(nLat2)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return earthRadiusKm * c;
}

export interface GeofenceTarget {
  latitude: number | string;
  longitude: number | string;
  radius: number;
}

/** Filter configured company geofence locations that contain the current kiosk coordinates. */
export function filterLocationsWithinRadius<T extends GeofenceTarget>(
  latitude: number,
  longitude: number,
  locations: readonly T[],
): T[] {
  return locations.filter(
    (loc) => haversineDistanceKm(latitude, longitude, loc.latitude, loc.longitude) <= loc.radius,
  );
}

/** Map browser GeolocationPositionError.code into a Thai operator message. */
export function describeGeolocationErrorCode(code: number): string {
  switch (code) {
    case 1:
      return 'ผู้ใช้ปฏิเสธการแชร์ตำแหน่ง — อนุญาต Location ในเบราว์เซอร์';
    case 2:
      return 'อ่านตำแหน่งไม่ได้ (เครื่องไม่มี GPS / สัญญาณไม่พอ)';
    case 3:
      return 'ขอตำแหน่งหมดเวลา — กด Retry GPS หรือรีเฟรชหน้า';
    default:
      return 'ขอตำแหน่งไม่สำเร็จ';
  }
}
