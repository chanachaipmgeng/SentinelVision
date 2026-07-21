import {
  AfterViewInit,
  Component,
  Input,
  OnChanges,
  SimpleChanges,
} from '@angular/core';

@Component({
  selector: 'app-dpu-location-map',
  templateUrl: './dpu-location-map.component.html',
  styleUrls: ['./dpu-location-map.component.scss'],
})
export class DpuLocationMapComponent implements AfterViewInit, OnChanges {
  @Input() latitude: number | string = 13.7563;
  @Input() longitude: number | string = 100.5018;
  @Input() zoom = 15;
  @Input() height = 320;
  @Input() active = true;

  map?: google.maps.Map;
  ready = false;

  get lat(): number {
    const value = Number(this.latitude);
    return Number.isFinite(value) ? value : 13.7563;
  }

  get lng(): number {
    const value = Number(this.longitude);
    return Number.isFinite(value) ? value : 100.5018;
  }

  ngAfterViewInit(): void {
    setTimeout(() => this.resizeMap(), 250);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (this.map && (changes['latitude'] || changes['longitude'] || changes['active'])) {
      setTimeout(() => this.resizeMap(), 50);
    }
  }

  onMapReady(map: google.maps.Map): void {
    this.map = map;
    this.ready = true;
    this.resizeMap();
  }

  resizeMap(): void {
    if (!this.map || !this.active) {
      return;
    }
    const center = { lat: this.lat, lng: this.lng };
    google.maps.event.trigger(this.map, 'resize');
    this.map.setCenter(center);
  }
}
