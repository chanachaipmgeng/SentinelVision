import {
  ChangeDetectorRef,
  Component,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  OnInit,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { GoogleMapsModule, MapMarker } from '@angular/google-maps';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

declare global {
  interface Window {
    gm_authFailure?: () => void;
    __dpuMapsAuthFailed?: boolean;
  }
}

@Component({
  selector: 'app-location-map',
  standalone: true,
  imports: [CommonModule, GoogleMapsModule, MapMarker],
  templateUrl: './location-map.component.html',
  styleUrls: ['./location-map.component.css'],
})
export class LocationMapComponent implements OnInit, OnChanges, OnDestroy {
  @Input() lat = 13.7563;
  @Input() lng = 100.5018;
  @Input() zoom = 15;
  @Input() height = '280px';
  /** Opt-in only — Google Maps is skipped when API key/referrer is blocked. */
  @Input() preferGoogle = false;

  useGoogle = false;
  center: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  osmUrl: SafeResourceUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
    'about:blank'
  );

  private previousAuthFailure?: () => void;

  constructor(
    private sanitizer: DomSanitizer,
    private zone: NgZone,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.previousAuthFailure = window.gm_authFailure;
    window.gm_authFailure = () => {
      window.__dpuMapsAuthFailed = true;
      this.zone.run(() => {
        this.useGoogle = false;
        this.cdr.markForCheck();
      });
      this.previousAuthFailure?.();
    };

    this.syncCenter();
    this.useGoogle =
      this.preferGoogle &&
      !window.__dpuMapsAuthFailed &&
      this.isGoogleMapsUsable();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['lat'] || changes['lng'] || changes['zoom']) {
      this.syncCenter();
    }
    if (changes['preferGoogle']) {
      this.useGoogle =
        this.preferGoogle &&
        !window.__dpuMapsAuthFailed &&
        this.isGoogleMapsUsable();
    }
  }

  ngOnDestroy(): void {
    if (window.gm_authFailure) {
      window.gm_authFailure = this.previousAuthFailure;
    }
  }

  get mapsLink(): string {
    return `https://www.google.com/maps?q=${this.center.lat},${this.center.lng}`;
  }

  private syncCenter(): void {
    this.center = {
      lat: this.toCoord(this.lat, 13.7563),
      lng: this.toCoord(this.lng, 100.5018),
    };
    const z = Math.max(1, Math.min(18, Number(this.zoom) || 15));
    const delta = 0.01 / Math.pow(2, Math.max(0, z - 12));
    const left = this.center.lng - delta;
    const right = this.center.lng + delta;
    const top = this.center.lat + delta;
    const bottom = this.center.lat - delta;
    const url =
      `https://www.openstreetmap.org/export/embed.html?bbox=${left}%2C${bottom}%2C${right}%2C${top}` +
      `&layer=mapnik&marker=${this.center.lat}%2C${this.center.lng}`;
    this.osmUrl = this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }

  private isGoogleMapsUsable(): boolean {
    try {
      return !!(window as any).google?.maps?.Map;
    } catch {
      return false;
    }
  }

  private toCoord(value: unknown, fallback: number): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
}
