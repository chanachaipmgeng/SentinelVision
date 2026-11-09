import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
  ViewEncapsulation,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import * as L from 'leaflet';

export interface GeofencePosition {
  lat: number;
  lng: number;
}

/**
 * Leaflet OSM marker + radius circle for company punch geofences.
 * Radius input is kilometres (same as company_location API); circle uses metres.
 */
@Component({
  selector: 'app-geofence-map',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="dpu-geofence-map" [style.height]="height">
      <div #mapHost class="dpu-geofence-map__host"></div>
      <div *ngIf="editable" class="dpu-geofence-map__hint">
        คลิกแผนที่เพื่อปักหมุด
      </div>
    </div>
  `,
  styles: [
    `
      .dpu-geofence-map {
        position: relative;
        width: 100%;
        border-radius: 0.85rem;
        overflow: hidden;
        background: #e2e8f0;
      }
      .dpu-geofence-map__host {
        width: 100%;
        height: 100%;
        min-height: inherit;
        z-index: 0;
      }
      .dpu-geofence-map__hint {
        position: absolute;
        left: 0.65rem;
        bottom: 0.65rem;
        z-index: 450;
        pointer-events: none;
        padding: 0.28rem 0.55rem;
        border-radius: 0.5rem;
        font-size: 0.72rem;
        font-weight: 700;
        color: #0b4f4a;
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(15, 118, 110, 0.25);
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
      }
      .dpu-geofence-pin {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #0b4f4a;
        border: 3px solid #fff;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.45);
      }
      .dpu-geofence-map .leaflet-container {
        font: inherit;
        background: #e2e8f0;
        cursor: inherit;
      }
      .dpu-geofence-map--editable .leaflet-container {
        cursor: crosshair;
      }
    `,
  ],
  encapsulation: ViewEncapsulation.None,
  host: {
    '[class.dpu-geofence-map--editable]': 'editable',
  },
})
export class GeofenceMapComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('mapHost', { static: true }) mapHost!: ElementRef<HTMLDivElement>;

  @Input() lat = 13.7563;
  @Input() lng = 100.5018;
  /** Geofence radius in kilometres (API field). */
  @Input() radiusKm = 0;
  @Input() zoom = 14;
  @Input() height = '300px';
  @Input() editable = false;

  @Output() positionChange = new EventEmitter<GeofencePosition>();

  private map?: L.Map;
  private marker?: L.Marker;
  private circle?: L.Circle;
  private viewReady = false;
  private resizeObserver?: ResizeObserver;
  private clickHandler?: (e: L.LeafletMouseEvent) => void;

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.initMap();
    this.syncOverlay(true);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.viewReady || !this.map) return;

    if (changes['editable']) {
      this.bindClickHandler();
    }

    if (
      changes['lat'] ||
      changes['lng'] ||
      changes['radiusKm'] ||
      changes['zoom']
    ) {
      this.syncOverlay(!!(changes['lat'] || changes['lng'] || changes['zoom']));
    }
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    if (this.map && this.clickHandler) {
      this.map.off('click', this.clickHandler);
    }
    this.map?.remove();
    this.map = undefined;
    this.marker = undefined;
    this.circle = undefined;
  }

  /** Call after a hidden host (e.g. modal) becomes visible. */
  invalidateSize(): void {
    this.map?.invalidateSize({ animate: false });
  }

  private initMap(): void {
    if (this.map || !this.mapHost?.nativeElement) return;

    const host = this.mapHost.nativeElement;
    const { lat, lng } = this.resolvedCenter();
    this.map = L.map(host, {
      zoomControl: true,
      attributionControl: true,
    }).setView([lat, lng], this.resolvedZoom());

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap',
    }).addTo(this.map);

    this.bindClickHandler();

    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => {
        this.map?.invalidateSize({ animate: false });
      });
      this.resizeObserver.observe(host);
    }

    setTimeout(() => this.map?.invalidateSize({ animate: false }), 120);
    setTimeout(() => this.map?.invalidateSize({ animate: false }), 400);
  }

  private bindClickHandler(): void {
    if (!this.map) return;
    if (this.clickHandler) {
      this.map.off('click', this.clickHandler);
      this.clickHandler = undefined;
    }
    if (!this.editable) return;

    this.clickHandler = (e: L.LeafletMouseEvent) => {
      const lat = e.latlng.lat;
      const lng = e.latlng.lng;
      this.positionChange.emit({ lat, lng });
      // Optimistic local move; parent ngModel will also push updated inputs.
      this.applyPosition(lat, lng, false);
    };
    this.map.on('click', this.clickHandler);
  }

  private syncOverlay(panToCenter: boolean): void {
    if (!this.map) return;
    const { lat, lng } = this.resolvedCenter();
    this.applyPosition(lat, lng, panToCenter);
    if (panToCenter) {
      this.map.setView([lat, lng], this.resolvedZoom());
    }
    setTimeout(() => this.map?.invalidateSize({ animate: false }), 80);
  }

  private applyPosition(lat: number, lng: number, _pan: boolean): void {
    if (!this.map) return;

    const icon = L.divIcon({
      className: 'dpu-marker-wrap',
      html: `<div class="dpu-geofence-pin" title="Geofence center"></div>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });

    if (!this.marker) {
      this.marker = L.marker([lat, lng], {
        icon,
        draggable: false,
        zIndexOffset: 400,
      }).addTo(this.map);
    } else {
      this.marker.setLatLng([lat, lng]);
      this.marker.setIcon(icon);
    }

    const radiusM = Math.max(0, this.resolvedRadiusKm()) * 1000;
    if (!this.circle) {
      this.circle = L.circle([lat, lng], {
        radius: radiusM,
        color: '#0f766e',
        weight: 2,
        opacity: 0.7,
        fillColor: '#0f766e',
        fillOpacity: 0.15,
      }).addTo(this.map);
    } else {
      this.circle.setLatLng([lat, lng]);
      this.circle.setRadius(radiusM);
    }
  }

  private resolvedCenter(): GeofencePosition {
    return {
      lat: this.toCoord(this.lat, 13.7563),
      lng: this.toCoord(this.lng, 100.5018),
    };
  }

  private resolvedRadiusKm(): number {
    const n = Number(this.radiusKm);
    return Number.isFinite(n) && n >= 0 ? n : 0;
  }

  private resolvedZoom(): number {
    const z = Number(this.zoom);
    return Number.isFinite(z) ? Math.max(1, Math.min(19, z)) : 14;
  }

  private toCoord(value: unknown, fallback: number): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
}
