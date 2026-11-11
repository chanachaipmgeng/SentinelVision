import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  ViewEncapsulation,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import * as L from 'leaflet';
import { firstValueFrom } from 'rxjs';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { AuthedImageService } from '../../../shared/services/authed-image.service';
import { TokenService } from '../../../shared/services/token.service';

export type EmapPinKind = 'camera' | 'zone' | 'kiosk';

export interface SiteFloorRow {
  siteFloorId: string;
  companyId: string;
  name: string;
  buildingLabel?: string | null;
  floorLabel?: string | null;
  planImageKey?: string | null;
  planImageUrl?: string | null;
  widthPx?: number | null;
  heightPx?: number | null;
  sortOrder?: number;
}

export interface EmapPin {
  kind: EmapPinKind;
  id: string;
  name: string;
  siteFloorId?: string | null;
  mapPosX?: number | null;
  mapPosY?: number | null;
}

interface DirtyPin {
  kind: EmapPinKind;
  id: string;
  siteFloorId: string | null;
  mapPosX: number | null;
  mapPosY: number | null;
}

@Component({
    selector: 'app-company-e-map',
    imports: [CommonModule, FormsModule, TranslateModule, PageToolbarComponent, EmptyStateComponent],
    templateUrl: './e-map.component.html',
    styleUrls: ['../../../shared/styles/dpu-list-page.css', './e-map.component.css'],
    encapsulation: ViewEncapsulation.None
})
export class EMapComponent implements AfterViewInit, OnDestroy {
  @ViewChild('mapHost', { static: false }) mapHost?: ElementRef<HTMLDivElement>;

  companyId = '';
  loading = false;
  saving = false;
  floors: SiteFloorRow[] = [];
  selectedFloorId = '';
  floor: SiteFloorRow | null = null;
  pins: EmapPin[] = [];
  unassigned: EmapPin[] = [];
  showCreate = false;
  draft = { name: '', buildingLabel: '', floorLabel: '' };
  errorMessage = '';
  dirty = new Map<string, DirtyPin>();

  private map: L.Map | null = null;
  private imageLayer: L.ImageOverlay | null = null;
  private markers = new Map<string, L.Marker>();
  private readonly bounds: L.LatLngBoundsExpression = [
    [0, 0],
    [1, 1],
  ];

  constructor(
    private http: HttpClient,
    private token: TokenService,
    private images: AuthedImageService
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngAfterViewInit(): void {
    void this.reloadFloors();
  }

  ngOnDestroy(): void {
    this.destroyMap();
  }

  get selectedFloor(): SiteFloorRow | null {
    return this.floors.find((f) => f.siteFloorId === this.selectedFloorId) || this.floor;
  }

  get hasDirty(): boolean {
    return this.dirty.size > 0;
  }

  get noFloors(): boolean {
    return !this.loading && this.floors.length === 0;
  }

  get needsPlan(): boolean {
    return !!this.selectedFloor && !this.selectedFloor.planImageKey;
  }

  async reloadFloors(): Promise<void> {
    if (!this.companyId) {
      return;
    }
    this.loading = true;
    this.errorMessage = '';
    try {
      this.floors =
        (await firstValueFrom(
          this.http.get<SiteFloorRow[]>(`/site-floors/company/${this.companyId}/floors`)
        )) || [];
      if (!this.selectedFloorId && this.floors.length) {
        this.selectedFloorId = this.floors[0].siteFloorId;
      }
      if (this.selectedFloorId) {
        await this.loadEmap();
      } else {
        this.floor = null;
        this.pins = [];
        this.unassigned = [];
        this.destroyMap();
      }
    } catch {
      this.errorMessage = 'emap.loadError';
      this.floors = [];
    } finally {
      this.loading = false;
    }
  }

  async onFloorChange(): Promise<void> {
    this.dirty.clear();
    await this.loadEmap();
  }

  async loadEmap(): Promise<void> {
    if (!this.companyId || !this.selectedFloorId) {
      return;
    }
    this.loading = true;
    this.errorMessage = '';
    try {
      const payload = await firstValueFrom(
        this.http.get<{
          floor: SiteFloorRow;
          pins: { cameras: EmapPin[]; zones: EmapPin[]; kiosks: EmapPin[] };
          unassigned: { cameras: EmapPin[]; zones: EmapPin[]; kiosks: EmapPin[] };
        }>(`/site-floors/company/${this.companyId}/floors/${this.selectedFloorId}/emap`)
      );
      this.floor = payload.floor;
      this.pins = [
        ...(payload.pins?.cameras || []),
        ...(payload.pins?.zones || []),
        ...(payload.pins?.kiosks || []),
      ];
      this.unassigned = [
        ...(payload.unassigned?.cameras || []),
        ...(payload.unassigned?.zones || []),
        ...(payload.unassigned?.kiosks || []),
      ];
      await this.renderMap();
    } catch {
      this.errorMessage = 'emap.loadError';
    } finally {
      this.loading = false;
    }
  }

  async createFloor(): Promise<void> {
    const name = (this.draft.name || '').trim();
    if (!name || !this.companyId) {
      return;
    }
    this.saving = true;
    try {
      const created = await firstValueFrom(
        this.http.post<SiteFloorRow>(`/site-floors/company/${this.companyId}/floors`, {
          name,
          buildingLabel: (this.draft.buildingLabel || '').trim() || null,
          floorLabel: (this.draft.floorLabel || '').trim() || null,
        })
      );
      this.showCreate = false;
      this.draft = { name: '', buildingLabel: '', floorLabel: '' };
      this.floors = [...this.floors, created];
      this.selectedFloorId = created.siteFloorId;
      await this.loadEmap();
    } catch {
      this.errorMessage = 'emap.saveError';
    } finally {
      this.saving = false;
    }
  }

  async onPlanSelected(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !this.companyId || !this.selectedFloorId) {
      return;
    }
    const form = new FormData();
    form.append('file', file);
    this.saving = true;
    try {
      const dims = await this.readImageDims(file);
      if (dims) {
        form.append('widthPx', String(dims.w));
        form.append('heightPx', String(dims.h));
      }
      const updated = await firstValueFrom(
        this.http.post<SiteFloorRow>(
          `/site-floors/company/${this.companyId}/floors/${this.selectedFloorId}/plan-image`,
          form
        )
      );
      this.floor = updated;
      this.floors = this.floors.map((f) => (f.siteFloorId === updated.siteFloorId ? updated : f));
      await this.renderMap();
    } catch {
      this.errorMessage = 'emap.uploadError';
    } finally {
      this.saving = false;
      input.value = '';
    }
  }

  placeUnassigned(pin: EmapPin): void {
    if (!this.selectedFloorId || !this.map) {
      return;
    }
    const next: EmapPin = {
      ...pin,
      siteFloorId: this.selectedFloorId,
      mapPosX: 0.5,
      mapPosY: 0.5,
    };
    this.unassigned = this.unassigned.filter((p) => !(p.kind === pin.kind && p.id === pin.id));
    this.pins = [...this.pins.filter((p) => !(p.kind === pin.kind && p.id === pin.id)), next];
    this.markDirty(next);
    this.upsertMarker(next);
  }

  clearPin(pin: EmapPin): void {
    const cleared: EmapPin = {
      ...pin,
      siteFloorId: null,
      mapPosX: null,
      mapPosY: null,
    };
    this.pins = this.pins.filter((p) => !(p.kind === pin.kind && p.id === pin.id));
    this.unassigned = [...this.unassigned.filter((p) => !(p.kind === pin.kind && p.id === pin.id)), cleared];
    this.markDirty(cleared);
    const key = this.pinKey(pin);
    const marker = this.markers.get(key);
    if (marker) {
      marker.remove();
      this.markers.delete(key);
    }
  }

  async savePins(): Promise<void> {
    if (!this.companyId || !this.dirty.size) {
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    try {
      const jobs = Array.from(this.dirty.values()).map((d) =>
        firstValueFrom(
          this.http.patch(`/site-floors/company/${this.companyId}/pins/${d.kind}/${d.id}`, {
            siteFloorId: d.siteFloorId,
            mapPosX: d.mapPosX,
            mapPosY: d.mapPosY,
          })
        )
      );
      await Promise.all(jobs);
      this.dirty.clear();
    } catch {
      this.errorMessage = 'emap.saveError';
    } finally {
      this.saving = false;
    }
  }

  kindLabel(kind: EmapPinKind): string {
    return `emap.kind.${kind}`;
  }

  private pinKey(pin: EmapPin): string {
    return `${pin.kind}:${pin.id}`;
  }

  private markDirty(pin: EmapPin): void {
    this.dirty.set(this.pinKey(pin), {
      kind: pin.kind,
      id: pin.id,
      siteFloorId: pin.siteFloorId ?? null,
      mapPosX: pin.mapPosX ?? null,
      mapPosY: pin.mapPosY ?? null,
    });
  }

  private async renderMap(): Promise<void> {
    await new Promise((r) => setTimeout(r, 0));
    const host = this.mapHost?.nativeElement;
    if (!host) {
      return;
    }
    if (!this.floor?.planImageKey) {
      this.destroyMap();
      return;
    }
    const url = await this.images.blobUrl(this.floor.planImageKey);
    if (!url) {
      return;
    }
    if (!this.map) {
      this.map = L.map(host, {
        crs: L.CRS.Simple,
        minZoom: -2,
        maxZoom: 4,
        zoomControl: true,
        attributionControl: false,
      });
    }
    if (this.imageLayer) {
      this.imageLayer.remove();
      this.imageLayer = null;
    }
    this.imageLayer = L.imageOverlay(url, this.bounds).addTo(this.map);
    this.map.fitBounds(this.bounds);
    for (const marker of this.markers.values()) {
      marker.remove();
    }
    this.markers.clear();
    for (const pin of this.pins) {
      if (pin.mapPosX == null || pin.mapPosY == null) {
        continue;
      }
      this.upsertMarker(pin);
    }
    setTimeout(() => this.map?.invalidateSize(), 50);
  }

  private upsertMarker(pin: EmapPin): void {
    if (!this.map || pin.mapPosX == null || pin.mapPosY == null) {
      return;
    }
    const key = this.pinKey(pin);
    const latlng = L.latLng(1 - pin.mapPosY, pin.mapPosX);
    let marker = this.markers.get(key);
    if (marker) {
      marker.setLatLng(latlng);
      return;
    }
    const icon = L.divIcon({
      className: `emap-pin emap-pin--${pin.kind}`,
      html: `<span title="${this.escape(pin.name)}">${this.escape(pin.name.slice(0, 12))}</span>`,
      iconSize: [88, 28],
      iconAnchor: [44, 14],
    });
    marker = L.marker(latlng, { draggable: true, icon }).addTo(this.map);
    marker.on('dragend', () => {
      const pos = marker!.getLatLng();
      const x = Math.min(1, Math.max(0, pos.lng));
      const y = Math.min(1, Math.max(0, 1 - pos.lat));
      const updated: EmapPin = {
        ...pin,
        siteFloorId: this.selectedFloorId,
        mapPosX: Number(x.toFixed(4)),
        mapPosY: Number(y.toFixed(4)),
      };
      this.pins = this.pins.map((p) => (this.pinKey(p) === key ? updated : p));
      this.markDirty(updated);
      marker!.setLatLng(L.latLng(1 - updated.mapPosY!, updated.mapPosX!));
    });
    this.markers.set(key, marker);
  }

  private destroyMap(): void {
    for (const marker of this.markers.values()) {
      marker.remove();
    }
    this.markers.clear();
    if (this.imageLayer) {
      this.imageLayer.remove();
      this.imageLayer = null;
    }
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  private escape(value: string): string {
    return value.replace(/[&<>"']/g, (ch) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch] || ch)
    );
  }

  private readImageDims(file: File): Promise<{ w: number; h: number } | null> {
    return new Promise((resolve) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        const w = img.naturalWidth;
        const h = img.naturalHeight;
        URL.revokeObjectURL(url);
        resolve(w && h ? { w, h } : null);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(null);
      };
      img.src = url;
    });
  }
}
