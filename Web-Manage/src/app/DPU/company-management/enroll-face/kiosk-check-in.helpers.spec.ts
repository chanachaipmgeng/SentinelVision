import {
  FaceTrack,
  buildCheckInFeedRecord,
  buildKioskStatusMessage,
  mergeOverlappingFaceTracks,
  normalizeTimestampType,
  resolveAttendanceLabel,
  resolveStationModeHudUpdate,
} from './kiosk-check-in.helpers';

describe('kiosk-check-in.helpers', () => {
  it('normalizes numeric and string timestamp types', () => {
    expect(normalizeTimestampType(2)).toBe(2);
    expect(normalizeTimestampType('4')).toBe(4);
    expect(normalizeTimestampType('WARNING')).toBe(0);
    expect(normalizeTimestampType('CHECK_OUT')).toBe(2);
    expect(normalizeTimestampType('BREAK_OUT')).toBe(4);
    expect(normalizeTimestampType('BREAK_IN')).toBe(5);
    expect(normalizeTimestampType(undefined)).toBe(1);
  });

  it('formats attendance labels for late, OT, breaks, and warnings', () => {
    expect(
      resolveAttendanceLabel({
        isWarning: true,
        tsTypeNum: 0,
        isLate: false,
        lateMinutes: 0,
        overtimeMinutes: 0,
      }),
    ).toContain('Warning');

    expect(
      resolveAttendanceLabel({
        isWarning: false,
        tsTypeNum: 2,
        isLate: false,
        lateMinutes: 0,
        overtimeMinutes: 45,
      }),
    ).toContain('OT 45');

    expect(
      resolveAttendanceLabel({
        isWarning: false,
        tsTypeNum: 1,
        isLate: true,
        lateMinutes: 12,
        overtimeMinutes: 0,
      }),
    ).toContain('สาย 12');
  });

  it('resolves HUD updates for VIP arrival and door unlock', () => {
    const hud = resolveStationModeHudUpdate(
      {
        accessGranted: true,
        identityType: 'VIP',
        subjectName: 'Dr. Somchai',
        welcomeMessage: 'Welcome VIP',
        seatNumber: 'A-12',
      },
      false,
    );
    expect(hud.doorStatus).toBe('unlocked');
    expect(hud.vipArrivalName).toBe('Dr. Somchai');
    expect(hud.welcomeBanner).toBe('Welcome VIP');
    expect(hud.seatNumber).toBe('A-12');
  });

  it('builds normalized check-in feed item and toast', () => {
    const res = buildCheckInFeedRecord({
      response: {
        employee: { fullName: 'Narin W.', employeeId: 'EMP-001', department: 'Eng' },
        confidencePercent: 98.7,
        timestamp: { timestampId: 'ts-1', timestampType: 1, isLate: false },
      },
      frames: ['data:image/jpeg;base64,AAA'],
      stationMode: 'ATTENDANCE',
      showAttendancePanel: true,
      isDuplicate: false,
      baseUrl: '',
      resolveAuthedImage: (f) => `/img/${f}`,
    });
    expect(res.item.id).toBe('ts-1');
    expect(res.item.employeeName).toBe('Narin W.');
    expect(res.item.statusKind).toBe('success');
    expect(res.toastKind).toBe('success');
  });

  it('builds status messages for camera, GPS, and active faces', () => {
    const msg = buildKioskStatusMessage({
      adminPreviewMode: false,
      cameraFailed: false,
      cameraRecoveryTitle: '',
      gpsRequired: false,
      hasValidLocation: true,
      errorMessage: null,
      tracks: [{ label: 'Alice' }, { label: 'Bob' }],
      wsConnected: true,
      serverDetectActive: true,
      checkingInCount: 1,
      stationMode: 'ATTENDANCE',
      queuePending: 3,
    });
    expect(msg).toContain('พบ 2 ใบหน้า');
    expect(msg).toContain('Alice, Bob');
    expect(msg).toContain('คิว GPU 3');
  });

  it('merges overlapping ghost tracks while preferring identified track', () => {
    const mk = (id: number, memberId: string | null): FaceTrack => ({
      id,
      box: { x: 10, y: 10, width: 100, height: 100 },
      targetBox: { x: 12, y: 12, width: 100, height: 100 },
      firstSeenAt: id * 100,
      lastSeenAt: 500,
      label: memberId ? 'Identified' : null,
      memberId,
      confidence: memberId ? 95 : null,
      phase: 'watching',
      lastIdentifyAt: 0,
      identifyInFlight: false,
      captureFrames: [],
      captureTimer: null,
      retryAfter: 0,
      statusText: null,
    });
    const dropped: number[] = [];
    const merged = mergeOverlappingFaceTracks([mk(1, null), mk(2, 'm-1')], 0.45, (t) =>
      dropped.push(t.id),
    );
    expect(merged.length).toBe(1);
    expect(merged[0].id).toBe(2);
    expect(dropped).toEqual([1]);
  });
});
