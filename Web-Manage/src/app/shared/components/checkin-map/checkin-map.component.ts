import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
  ViewEncapsulation,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import * as L from 'leaflet';

export interface CheckinMapPoint {
  latitude?: number | null;
  longitude?: number | null;
  employeeName?: string;
  locationName?: string;
  timestamp?: string | Date;
  timestampType?: number;
  approvalStatus?: string;
}

export interface CompanyMapLocation {
  locationId?: string;
  locationName?: string;
  latitude?: number | null;
  longitude?: number | null;
  radius?: number;
  locationType?: number;
}

@Component({
    selector: 'app-checkin-map',
    imports: [CommonModule],
    template: `
    <div class="dpu-checkin-map" [style.height]="height">
      <div #mapHost class="dpu-checkin-map__host"></div>
      <div *ngIf="showEmpty" class="dpu-checkin-map__empty">
        ยังไม่มีพิกัดบริษัทหรือการลงเวลาบนแผนที่
      </div>
    </div>
  `,
    styles: [
        `
      .dpu-checkin-map {
        position: relative;
        width: 100%;
        border-radius: 0.85rem;
        overflow: hidden;
        background: #e2e8f0;
      }
      .dpu-checkin-map__host {
        width: 100%;
        height: 100%;
        min-height: inherit;
        z-index: 0;
      }
      .dpu-checkin-map__empty {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        pointer-events: none;
        color: #64748b;
        font-size: 0.88rem;
        font-weight: 600;
        background: rgba(248, 250, 252, 0.55);
        z-index: 400;
      }
      .dpu-pin {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        border: 2px solid #fff;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.35);
      }
      .dpu-pin--ok {
        background: #0f766e;
      }
      .dpu-pin--warn {
        background: #c2410c;
      }
      .dpu-pin--hq {
        width: 22px;
        height: 22px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        background: #0f766e;
        border: 2px solid #fff;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .dpu-pin--hq > i {
        transform: rotate(45deg);
        color: #fff;
        font-size: 11px;
        line-height: 1;
        font-style: normal;
      }
      .dpu-pin--hq-dot {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #0b4f4a;
        border: 3px solid #fff;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.45);
      }
      .leaflet-popup-content {
        margin: 0.55rem 0.7rem;
        font-size: 0.8rem;
        line-height: 1.35;
      }
      .leaflet-container {
        font: inherit;
        background: #e2e8f0;
      }
    `,
    ],
    encapsulation: ViewEncapsulation.None
})
export class CheckinMapComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('mapHost', { static: true }) mapHost!: ElementRef<HTMLDivElement>;

  @Input() points: CheckinMapPoint[] = [];
  @Input() companyLocations: CompanyMapLocation[] = [];
  @Input() height = '360px';

  showEmpty = true;

  private map?: L.Map;
  private checkinLayer?: L.LayerGroup;
  private companyLayer?: L.LayerGroup;
  private viewReady = false;
  private didSetInitialView = false;
  private resizeObserver?: ResizeObserver;

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.initMap();
    this.renderAll();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.viewReady) return;
    if (changes['points'] || changes['companyLocations']) {
      this.renderAll();
    }
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.map?.remove();
    this.map = undefined;
  }

  private initMap(): void {
    if (this.map || !this.mapHost?.nativeElement) return;

    const host = this.mapHost.nativeElement;
    this.map = L.map(host, {
      zoomControl: true,
      attributionControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap',
    }).addTo(this.map);

    this.companyLayer = L.layerGroup().addTo(this.map);
    this.checkinLayer = L.layerGroup().addTo(this.map);

    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => {
        this.map?.invalidateSize({ animate: false });
      });
      this.resizeObserver.observe(host);
    }

    setTimeout(() => this.map?.invalidateSize({ animate: false }), 120);
  }

  private renderAll(): void {
    if (!this.map || !this.checkinLayer || !this.companyLayer) return;

    this.companyLayer.clearLayers();
    this.checkinLayer.clearLayers();

    const companies = this.validCoords(this.companyLocations || []);
    const checkins = this.validCoords(this.points || []);
    this.showEmpty = companies.length === 0 && checkins.length === 0;

    for (const { raw, lat, lng } of companies) {
      const loc = raw as CompanyMapLocation;
      const icon = L.divIcon({
        className: 'dpu-marker-wrap',
        html: `<div class="dpu-pin--hq-dot" title="${this.escape(loc.locationName || 'บริษัท')}"></div>`,
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      });
      const radius = Number(loc.radius);
      if (Number.isFinite(radius) && radius > 0) {
        // radius stored in km
        L.circle([lat, lng], {
          radius: radius * 1000,
          color: '#0f766e',
          weight: 1.5,
          fillColor: '#0f766e',
          fillOpacity: 0.08,
        }).addTo(this.companyLayer);
      }
      L.marker([lat, lng], { icon, zIndexOffset: 200 })
        .bindPopup(
          `<strong>${this.escape(loc.locationName || 'พื้นที่บริษัท')}</strong><br>` +
            `<span style="color:#64748b">หมุดบริษัท</span>`
        )
        .addTo(this.companyLayer);
    }

    for (const { raw, lat, lng } of checkins) {
      const p = raw as CheckinMapPoint;
      const inArea = Number(p.timestampType) === 1;
      const icon = L.divIcon({
        className: 'dpu-marker-wrap',
        html: `<div class="dpu-pin ${inArea ? 'dpu-pin--ok' : 'dpu-pin--warn'}"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });
      const when = p.timestamp ? new Date(p.timestamp).toLocaleString('th-TH') : '—';
      L.marker([lat, lng], { icon, zIndexOffset: 400 })
        .bindPopup(
          `<strong>${this.escape(p.employeeName || 'พนักงาน')}</strong><br>` +
            `${this.escape(p.locationName || (inArea ? 'ในพื้นที่' : 'นอกพื้นที่'))}<br>` +
            `<span style="color:#64748b">${when}</span>`
        )
        .addTo(this.checkinLayer);
    }

    this.applyView(companies, checkins);
    setTimeout(() => this.map?.invalidateSize({ animate: false }), 80);
  }

  private applyView(
    companies: { lat: number; lng: number }[],
    checkins: { lat: number; lng: number }[]
  ): void {
    if (!this.map) return;

    // First paint: start at company pin(s). Check-in markers stay on the map.
    if (!this.didSetInitialView) {
      if (companies.length === 1) {
        this.map.setView([companies[0].lat, companies[0].lng], 14);
        this.didSetInitialView = true;
        return;
      }
      if (companies.length > 1) {
        this.map.fitBounds(
          L.latLngBounds(companies.map((c) => [c.lat, c.lng] as L.LatLngTuple)),
          { padding: [48, 48], maxZoom: 15 }
        );
        this.didSetInitialView = true;
        return;
      }
      if (checkins.length === 1) {
        this.map.setView([checkins[0].lat, checkins[0].lng], 15);
        this.didSetInitialView = true;
        return;
      }
      if (checkins.length > 1) {
        this.map.fitBounds(
          L.latLngBounds(checkins.map((c) => [c.lat, c.lng] as L.LatLngTuple)),
          { padding: [36, 36], maxZoom: 16 }
        );
        this.didSetInitialView = true;
        return;
      }
      this.map.setView([13.7563, 100.5018], 11);
      return;
    }

    // Later polls: keep camera stable (do not jump away from company view).
  }

  private validCoords<T extends { latitude?: number | null; longitude?: number | null }>(
    items: T[]
  ): { raw: T; lat: number; lng: number }[] {
    const out: { raw: T; lat: number; lng: number }[] = [];
    for (const item of items || []) {
      const lat = Number(item.latitude);
      const lng = Number(item.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
      if (Math.abs(lat) > 90 || Math.abs(lng) > 180) continue;
      // Ignore null-island noise
      if (lat === 0 && lng === 0) continue;
      out.push({ raw: item, lat, lng });
    }
    return out;
  }

  private escape(value: string): string {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}
