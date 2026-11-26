import {
  describeGeolocationErrorCode,
  filterLocationsWithinRadius,
  hasFix,
  haversineDistanceKm,
} from './kiosk-geo.service';

describe('kiosk-geo.service', () => {
  it('validates geolocation fix presence', () => {
    expect(hasFix(0, 0)).toBeFalse();
    expect(hasFix(null, 100.5)).toBeFalse();
    expect(hasFix(13.7563, 100.5018)).toBeTrue();
  });

  it('computes haversine distance accurately in km', () => {
    expect(haversineDistanceKm(13.7563, 100.5018, 13.7563, 100.5018)).toBeCloseTo(0, 5);
    // ~1.11 km per 0.01 deg latitude
    const d = haversineDistanceKm(13.7563, 100.5018, 13.7663, 100.5018);
    expect(d).toBeGreaterThan(1.0);
    expect(d).toBeLessThan(1.2);
  });

  it('filters locations within configured radius', () => {
    const locations = [
      { id: 'near', latitude: 13.7563, longitude: 100.5018, radius: 0.5 },
      { id: 'far', latitude: 14.0, longitude: 100.9, radius: 0.5 },
    ];
    const inside = filterLocationsWithinRadius(13.7565, 100.5019, locations);
    expect(inside.map((x) => x.id)).toEqual(['near']);
  });

  it('describes standard geolocation error codes', () => {
    expect(describeGeolocationErrorCode(1)).toContain('ปฏิเสธ');
    expect(describeGeolocationErrorCode(2)).toContain('GPS');
    expect(describeGeolocationErrorCode(3)).toContain('หมดเวลา');
    expect(describeGeolocationErrorCode(99)).toContain('ไม่สำเร็จ');
  });
});
