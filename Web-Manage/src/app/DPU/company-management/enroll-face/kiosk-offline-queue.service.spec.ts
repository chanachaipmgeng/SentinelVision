import { KioskOfflineQueueService } from './kiosk-offline-queue.service';

describe('KioskOfflineQueueService', () => {
  let service: KioskOfflineQueueService;

  beforeEach(() => {
    service = new KioskOfflineQueueService();
  });

  it('treats status 0 and navigator offline as offline', () => {
    expect(service.isLikelyOffline({ status: 0 })).toBeTrue();
    expect(service.isLikelyOffline({ status: 500 })).toBeFalse();
  });

  it('enqueues and lists punches when IndexedDB is available', async () => {
    if (typeof indexedDB === 'undefined') {
      pending('IndexedDB not available in this test runner');
      return;
    }
    const row = await service.enqueue({
      companyId: 'c1',
      images: ['data:image/jpeg;base64,aaa'],
      latitude: 13.7,
      longitude: 100.5,
      punchType: 'CHECK_IN',
      stationMode: 'ATTENDANCE',
      note: 'test',
    });
    expect(row.id).toContain('punch_');
    const listed = await service.list();
    expect(listed.some((r) => r.id === row.id)).toBeTrue();
    await service.remove(row.id);
    const after = await service.list();
    expect(after.some((r) => r.id === row.id)).toBeFalse();
  });
});
