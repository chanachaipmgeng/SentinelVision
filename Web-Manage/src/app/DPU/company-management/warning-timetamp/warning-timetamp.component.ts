import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { LocationMapComponent } from '../../../shared/components/location-map/location-map.component';
import { TimestampService } from '../../services/timestamp.service';
import { TokenService } from '../../../shared/services/token.service';
import { TimestampModel } from '../../models/timestamp.model';
import swal from 'sweetalert';

@Component({
  selector: 'app-warning-timetamp',
  templateUrl: './warning-timetamp.component.html',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule, LocationMapComponent],
  styleUrls: ['./warning-timetamp.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class WarningTimetampComponent implements OnInit {
  companyId = '';
  items: TimestampModel[] = [];
  filteredItems: TimestampModel[] = [];
  selected?: TimestampModel;
  loading = false;
  actionBusy = false;
  private _searchTerm = '';

  get searchTerm(): string {
    return this._searchTerm;
  }

  set searchTerm(val: string) {
    this._searchTerm = val;
    this.applyFilter();
  }

  get pendingCount(): number {
    return this.items.length;
  }

  get shownCount(): number {
    return this.filteredItems.length;
  }

  get mapLat(): number {
    return this.toCoord(this.selected?.latitude, 13.7563);
  }

  get mapLng(): number {
    return this.toCoord(this.selected?.longitude, 100.5018);
  }

  get mapsLink(): string {
    return `https://www.google.com/maps?q=${this.mapLat},${this.mapLng}`;
  }

  constructor(
    private timestampService: TimestampService,
    private tokenService: TokenService
  ) {
    this.companyId = this.tokenService.getSelectCompany()?.companyId || '';
  }

  ngOnInit() {
    this.loadPending();
  }

  loadPending() {
    if (!this.companyId) return;
    this.loading = true;
    const keepId = this.selected?.timestampId;
    this.timestampService
      .getListsSearch(this.companyId, '', '', '', undefined, 'PENDING')
      .subscribe({
        next: (result) => {
          this.items = result.sort((a, b) =>
            (b.timestamp || '').localeCompare(a.timestamp || '')
          );
          this.applyFilter(keepId);
          this.loading = false;
        },
        error: () => {
          this.loading = false;
          swal('Error', 'โหลดคิวอนุมัติไม่สำเร็จ', 'error');
        },
      });
  }

  applyFilter(preferId?: string) {
    const q = (this._searchTerm || '').trim().toLowerCase();
    this.filteredItems = !q
      ? [...this.items]
      : this.items.filter((x) => this.matchesSearch(x, q));

    if (!this.filteredItems.length) {
      this.selected = undefined;
      return;
    }

    const preferred =
      (preferId && this.filteredItems.find((x) => x.timestampId === preferId)) ||
      (this.selected &&
        this.filteredItems.find((x) => x.timestampId === this.selected!.timestampId));

    this.selectItem(preferred || this.filteredItems[0]);
  }

  selectItem(item: TimestampModel) {
    this.selected = item;
  }

  isSelected(item: TimestampModel): boolean {
    return !!this.selected && this.selected.timestampId === item.timestampId;
  }

  clearSearch() {
    this.searchTerm = '';
  }

  itemEnterDelay(index: number): number {
    return Math.min(index, 8) * 40;
  }

  approve(item: TimestampModel) {
    if (this.actionBusy) return;
    swal({
      title: 'อนุมัติการลงเวลานี้?',
      text: item.employee?.getFullname?.() || '',
      icon: 'warning',
      buttons: ['ยกเลิก', 'อนุมัติ'],
    }).then((ok: any) => {
      if (!ok) return;
      this.actionBusy = true;
      this.timestampService
        .approve(this.companyId, item.timestampId, {
          approve: true,
          approvedBy: this.tokenService.getUserData()?.memberId,
        })
        .subscribe({
          next: () => {
            this.actionBusy = false;
            swal('สำเร็จ', 'อนุมัติแล้ว', 'success');
            this.loadPending();
          },
          error: () => {
            this.actionBusy = false;
            swal('Error', 'อนุมัติไม่สำเร็จ', 'error');
          },
        });
    });
  }

  reject(item: TimestampModel) {
    if (this.actionBusy) return;
    swal({
      title: 'ปฏิเสธการลงเวลา',
      text: 'กรอกเหตุผลที่ปฏิเสธ',
      content: {
        element: 'input',
        attributes: { placeholder: 'เหตุผล' },
      } as any,
      buttons: ['ยกเลิก', 'ปฏิเสธ'],
    }).then((reason: any) => {
      if (reason === null || reason === false) return;
      const rejectReason = String(reason || '').trim();
      if (!rejectReason) {
        swal('ต้องระบุเหตุผล', '', 'info');
        return;
      }
      this.actionBusy = true;
      this.timestampService
        .approve(this.companyId, item.timestampId, {
          approve: false,
          rejectReason,
          approvedBy: this.tokenService.getUserData()?.memberId,
        })
        .subscribe({
          next: () => {
            this.actionBusy = false;
            swal('สำเร็จ', 'ปฏิเสธแล้ว', 'success');
            this.loadPending();
          },
          error: () => {
            this.actionBusy = false;
            swal('Error', 'ปฏิเสธไม่สำเร็จ', 'error');
          },
        });
    });
  }

  private matchesSearch(item: TimestampModel, q: string): boolean {
    const emp = item.employee;
    const haystack = [
      emp?.getFullname?.() || '',
      emp?.employeeId || '',
      emp?.member?.firstName || '',
      emp?.member?.lastName || '',
      emp?.department?.getName?.() || '',
      emp?.position?.getName?.() || '',
      item.getLocation?.() || '',
      item.locationName || '',
      item.note || '',
      item.timestampId || '',
      String(item.latitude ?? ''),
      String(item.longitude ?? ''),
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
