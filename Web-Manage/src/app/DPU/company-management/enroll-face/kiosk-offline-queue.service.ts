import { Injectable } from '@angular/core';

export interface OfflinePunchPayload {
  id: string;
  companyId: string;
  images: string[];
  latitude: number;
  longitude: number;
  punchType: string;
  stationMode: string;
  zoneId?: string | null;
  eventId?: string | null;
  enableDoorRelay?: boolean;
  totpOrPin?: string | null;
  note: string;
  createdAt: number;
  attempts: number;
  lastError?: string;
}

const DB_NAME = 'dpu-kiosk-offline';
const STORE = 'punch-queue';
const DB_VERSION = 1;

/** IndexedDB queue for kiosk punches that fail while offline; reconcile when back online. */
@Injectable({ providedIn: 'root' })
export class KioskOfflineQueueService {
  private dbPromise: Promise<IDBDatabase> | null = null;

  private openDb(): Promise<IDBDatabase> {
    if (this.dbPromise) {
      return this.dbPromise;
    }
    this.dbPromise = new Promise((resolve, reject) => {
      if (typeof indexedDB === 'undefined') {
        reject(new Error('IndexedDB unavailable'));
        return;
      }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'id' });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('IndexedDB open failed'));
    });
    return this.dbPromise;
  }

  async enqueue(
    payload: Omit<OfflinePunchPayload, 'id' | 'createdAt' | 'attempts'>,
  ): Promise<OfflinePunchPayload> {
    const row: OfflinePunchPayload = {
      ...payload,
      id: `punch_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`,
      createdAt: Date.now(),
      attempts: 0,
    };
    const db = await this.openDb();
    await this.idbReq(db.transaction(STORE, 'readwrite').objectStore(STORE).put(row));
    return row;
  }

  async list(): Promise<OfflinePunchPayload[]> {
    const db = await this.openDb();
    const rows = (await this.idbReq<OfflinePunchPayload[]>(
      db.transaction(STORE, 'readonly').objectStore(STORE).getAll(),
    )) as OfflinePunchPayload[];
    return (rows || []).sort((a, b) => a.createdAt - b.createdAt);
  }

  async count(): Promise<number> {
    const db = await this.openDb();
    return (await this.idbReq<number>(
      db.transaction(STORE, 'readonly').objectStore(STORE).count(),
    )) as number;
  }

  async remove(id: string): Promise<void> {
    const db = await this.openDb();
    await this.idbReq(db.transaction(STORE, 'readwrite').objectStore(STORE).delete(id));
  }

  async markAttempt(id: string, error?: string): Promise<void> {
    const db = await this.openDb();
    const tx = db.transaction(STORE, 'readwrite');
    const store = tx.objectStore(STORE);
    const row = (await this.idbReq<OfflinePunchPayload | undefined>(store.get(id))) as
      | OfflinePunchPayload
      | undefined;
    if (!row) {
      return;
    }
    row.attempts += 1;
    row.lastError = error || row.lastError;
    await this.idbReq(store.put(row));
  }

  isLikelyOffline(err?: { status?: number; message?: string } | null): boolean {
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      return true;
    }
    if (!err) {
      return false;
    }
    // Angular HttpClient network failures often have status 0
    return err.status === 0;
  }

  private idbReq<T = unknown>(request: IDBRequest): Promise<T> {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result as T);
      request.onerror = () => reject(request.error || new Error('IndexedDB request failed'));
    });
  }
}
