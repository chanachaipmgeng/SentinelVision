import { CommonModule } from '@angular/common';
import {
  Component,
  ElementRef,
  OnInit,
  ViewChild,
  ViewEncapsulation,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { SharedModule } from '../../../shared/shared.module';
import {
  GeofenceMapComponent,
  GeofencePosition,
} from '../../../shared/components/geofence-map/geofence-map.component';
import { CompanyLocationModel } from '../../models/company-location.model';
import { CompanyLocationService } from '../../services/company-location.service';
import { TokenService } from '../../../shared/services/token.service';
import swal from 'sweetalert';

@Component({
    selector: 'app-company-location',
    imports: [
        CommonModule,
        SharedModule,
        TranslateModule,
        NgSelectModule,
        FormsModule,
        GeofenceMapComponent,
    ],
    templateUrl: './company-location.component.html',
    styleUrl: './company-location.component.css',
    encapsulation: ViewEncapsulation.None
})
export class CompanyLocationComponent implements OnInit {
  @ViewChild('editGeofenceMap') editGeofenceMap?: GeofenceMapComponent;
  @ViewChild('closeModal') public childModal?: ElementRef;

  readonly pageSize = 8;

  action: 'add' | 'edit' = 'add';
  loading = false;
  saving = false;
  companyId = '';

  itemsList: CompanyLocationModel[] = [];
  filteredSource: CompanyLocationModel[] = [];
  pageItems: CompanyLocationModel[] = [];
  selectModel: CompanyLocationModel;
  selected?: CompanyLocationModel;

  selectedItems = new Map<string, boolean>();
  allSelected = false;
  someSelected = false;
  pageIndex = 0;
  typeFilter: '' | '0' | '1' = '';
  private _searchTerm = '';

  /** Map pan target for detail + edit (lat/lng). */
  center = { lat: 13.7563, lng: 100.5018 };
  zoom = 14;

  get searchTerm(): string {
    return this._searchTerm;
  }

  set searchTerm(val: string) {
    this._searchTerm = val;
    this.pageIndex = 0;
    this.applyFilter();
  }

  get totalAll(): number {
    return this.itemsList.length;
  }

  get permanentCount(): number {
    return this.itemsList.filter((x) => !this.isTemporary(x)).length;
  }

  get temporaryCount(): number {
    return this.itemsList.filter((x) => this.isTemporary(x)).length;
  }

  get totalFiltered(): number {
    return this.filteredSource.length;
  }

  get pageFrom(): number {
    if (!this.totalFiltered) return 0;
    return this.pageIndex * this.pageSize + 1;
  }

  get pageTo(): number {
    return Math.min((this.pageIndex + 1) * this.pageSize, this.totalFiltered);
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.totalFiltered / this.pageSize));
  }

  get mapCenter(): { lat: number; lng: number } {
    return {
      lat: this.toCoord(this.selectModel?.latitude, 13.7563),
      lng: this.toCoord(this.selectModel?.longitude, 100.5018),
    };
  }

  get selectedLat(): number {
    return this.toCoord(this.selected?.latitude, 13.7563);
  }

  get selectedLng(): number {
    return this.toCoord(this.selected?.longitude, 100.5018);
  }

  get selectedRadiusKm(): number {
    return Math.max(0, Number(this.selected?.radius) || 0);
  }

  get editRadiusKm(): number {
    return Math.max(0, Number(this.selectModel?.radius) || 0);
  }

  get mapsLink(): string {
    return `https://www.openstreetmap.org/?mlat=${this.selectedLat}&mlon=${this.selectedLng}#map=16/${this.selectedLat}/${this.selectedLng}`;
  }

  constructor(
    private comLocationService: CompanyLocationService,
    public translate: TranslateService,
    private tokenService: TokenService
  ) {
    this.selectModel = new CompanyLocationModel(undefined, this.translate);
    this.companyId = this.tokenService.getSelectCompany().companyId;
  }

  ngOnInit(): void {
    this.getLocation();
  }

  getLocation() {
    if (!this.companyId) return;
    this.loading = true;
    const keepId = this.selected?.locationId;
    this.comLocationService.getLists(this.companyId).subscribe({
      next: (result) => {
        this.itemsList = result || [];
        this.selectedItems.clear();
        this.allSelected = false;
        this.someSelected = false;
        this.applyFilter(keepId);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        swal('Error', 'โหลดสถานที่ไม่สำเร็จ', 'error');
      },
    });
  }

  applyFilter(preferId?: string) {
    const q = (this._searchTerm || '').trim().toLowerCase();
    let list = [...this.itemsList];

    if (this.typeFilter !== '') {
      const typeNum = Number(this.typeFilter);
      list = list.filter((x) => Number(x.locationType) === typeNum);
    }

    if (q) {
      list = list.filter((x) => this.matchesSearch(x, q));
    }

    this.filteredSource = list;
    const maxPage = Math.max(
      0,
      Math.ceil(this.filteredSource.length / this.pageSize) - 1
    );
    if (this.pageIndex > maxPage) this.pageIndex = maxPage;
    this.updatePagedItems();

    if (!this.filteredSource.length) {
      this.selected = undefined;
      return;
    }

    const preferred =
      (preferId &&
        this.filteredSource.find((x) => x.locationId === preferId)) ||
      (this.selected &&
        this.filteredSource.find(
          (x) => x.locationId === this.selected!.locationId
        ));

    this.selectItem(preferred || this.pageItems[0] || this.filteredSource[0]);
  }

  updatePagedItems() {
    const start = this.pageIndex * this.pageSize;
    this.pageItems = this.filteredSource.slice(start, start + this.pageSize);
  }

  goToPage(page: number) {
    const next = Math.max(0, Math.min(page, this.totalPages - 1));
    if (next === this.pageIndex) return;
    this.pageIndex = next;
    this.updatePagedItems();
  }

  prevPage() {
    this.goToPage(this.pageIndex - 1);
  }

  nextPage() {
    this.goToPage(this.pageIndex + 1);
  }

  clearSearch() {
    this.searchTerm = '';
  }

  setTypeFilter(value: '' | '0' | '1') {
    this.typeFilter = value;
    this.pageIndex = 0;
    this.applyFilter();
  }

  selectItem(item: CompanyLocationModel) {
    this.selected = item;
    this.center = {
      lat: this.toCoord(item.latitude, 13.7563),
      lng: this.toCoord(item.longitude, 100.5018),
    };
  }

  isSelected(item: CompanyLocationModel): boolean {
    return !!this.selected && this.selected.locationId === item.locationId;
  }

  isTemporary(item: CompanyLocationModel): boolean {
    return Number(item.locationType) === 1;
  }

  itemEnterDelay(index: number): number {
    return Math.min(index, 8) * 40;
  }

  private scheduleEditMapInvalidate() {
    // Modal opens via HS overlay; give the host time to become visible.
    setTimeout(() => this.editGeofenceMap?.invalidateSize(), 180);
    setTimeout(() => this.editGeofenceMap?.invalidateSize(), 450);
  }

  new() {
    this.action = 'add';
    this.selectModel = new CompanyLocationModel(undefined, this.translate);
    this.selectModel.latitude = 13.7563;
    this.selectModel.longitude = 100.5018;
    this.selectModel.radius = 0.5;
    this.selectModel.locationType = 0;
    this.selectModel.locationName = '';
    const today = new Date().toISOString().slice(0, 10);
    this.selectModel.startDate = today;
    this.selectModel.endDate = today;
    this.center = this.mapCenter;
    this.scheduleEditMapInvalidate();
  }

  view(item: CompanyLocationModel) {
    this.selectItem(item);
    this.action = 'edit';
    this.selectModel = new CompanyLocationModel(item, this.translate);
    if (this.selectModel.startDate) {
      this.selectModel.startDate = String(this.selectModel.startDate).slice(0, 10);
    }
    if (this.selectModel.endDate) {
      this.selectModel.endDate = String(this.selectModel.endDate).slice(0, 10);
    }
    this.center = this.mapCenter;
    this.scheduleEditMapInvalidate();
  }

  openEdit(item: CompanyLocationModel) {
    this.view(item);
  }

  onEditMapPosition(pos: GeofencePosition) {
    this.selectModel.latitude = pos.lat;
    this.selectModel.longitude = pos.lng;
    this.center = { lat: pos.lat, lng: pos.lng };
  }

  save() {
    const name = (this.selectModel.locationName || '').trim();
    if (!name) {
      swal('ข้อมูลไม่ครบ', 'กรุณากรอกชื่อสถานที่', 'warning');
      return;
    }
    if (
      !Number.isFinite(Number(this.selectModel.latitude)) ||
      !Number.isFinite(Number(this.selectModel.longitude))
    ) {
      swal('ข้อมูลไม่ครบ', 'กรุณาเลือกตำแหน่งบนแผนที่', 'warning');
      return;
    }
    if (
      this.selectModel.locationType === undefined ||
      this.selectModel.locationType === null
    ) {
      this.selectModel.locationType = 0;
    }
    if (!this.selectModel.radius && this.selectModel.radius !== 0) {
      this.selectModel.radius = 0.5;
    }

    swal({
      title: 'ยืนยันการบันทึก?',
      text: name,
      icon: 'warning',
      buttons: ['ยกเลิก', 'บันทึก'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.saving = true;
      const req$ =
        this.action === 'edit'
          ? this.comLocationService.update(this.companyId, this.selectModel)
          : this.comLocationService.save(this.companyId, this.selectModel);
      req$.subscribe({
        next: () => {
          this.saving = false;
          swal('สำเร็จ', 'บันทึกข้อมูลสำเร็จ', 'success');
          this.getLocation();
          this.childModal?.nativeElement.click();
        },
        error: (err) => {
          this.saving = false;
          const detail = err?.error?.detail;
          let msg = 'บันทึกสถานที่ไม่สำเร็จ';
          if (typeof detail === 'string') msg = detail;
          else if (Array.isArray(detail)) {
            msg = detail
              .map((d: unknown) =>
                typeof d === 'object' && d !== null && 'msg' in d
                  ? String((d as { msg?: string }).msg)
                  : JSON.stringify(d),
              )
              .join('\n');
          }
          swal('บันทึกไม่สำเร็จ', msg, 'error');
        },
      });
    });
  }

  delete(item: CompanyLocationModel) {
    swal({
      title: 'ลบสถานที่นี้?',
      text: item.locationName || '',
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ลบ'],
    }).then((willDelete: unknown) => {
      if (!willDelete) return;
      this.comLocationService.delete(this.companyId, item).subscribe({
        next: () => {
          swal('สำเร็จ', 'ลบแล้ว', 'success');
          this.getLocation();
        },
        error: () => swal('Error', 'ลบไม่สำเร็จ', 'error'),
      });
    });
  }

  toggleAll(event: Event) {
    const checked = !!(event.target as HTMLInputElement)?.checked;
    this.allSelected = checked;
    this.selectedItems.clear();
    this.filteredSource.forEach((item) => {
      this.selectedItems.set(item.locationId, checked);
    });
    this.someSelected = checked && this.filteredSource.length > 0;
  }

  onCheckboxChange(locationId: string, event: Event) {
    event.stopPropagation();
    const checked = !!(event.target as HTMLInputElement)?.checked;
    this.selectedItems.set(locationId, checked);
    this.allSelected =
      this.filteredSource.length > 0 &&
      this.filteredSource.every((item) => this.selectedItems.get(item.locationId));
    this.someSelected = this.filteredSource.some((item) =>
      this.selectedItems.get(item.locationId)
    );
  }

  deleteSelect() {
    const targets = this.filteredSource.filter((item) =>
      this.selectedItems.get(item.locationId)
    );
    if (!targets.length) return;

    const names = targets.map((t) => t.locationName).join('\n');
    swal({
      title: `ลบ ${targets.length} สถานที่?`,
      text: names,
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ลบ'],
    }).then((willDelete: unknown) => {
      if (!willDelete) return;
      let pending = targets.length;
      targets.forEach((item) => {
        this.comLocationService.delete(this.companyId, item).subscribe({
          next: () => {
            pending -= 1;
            if (pending <= 0) {
              swal('สำเร็จ', 'ลบแล้ว', 'success');
              this.getLocation();
            }
          },
          error: () => {
            pending -= 1;
            if (pending <= 0) this.getLocation();
          },
        });
      });
    });
  }

  changeMarker() {
    this.selectModel.latitude = this.toCoord(this.selectModel.latitude, 13.7563);
    this.selectModel.longitude = this.toCoord(
      this.selectModel.longitude,
      100.5018
    );
    this.center = this.mapCenter;
  }

  private matchesSearch(item: CompanyLocationModel, q: string): boolean {
    const haystack = [
      item.locationName || '',
      item.locationId || '',
      item.getStatus?.() || '',
      String(item.latitude ?? ''),
      String(item.longitude ?? ''),
      String(item.radius ?? ''),
    ]
      .join(' ')
      .toLowerCase();
    return haystack.includes(q);
  }

  private toCoord(value: unknown, fallback: number): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
}
