import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { SharedModule } from '../../../shared/shared.module';
import { LocationMapComponent } from '../../../shared/components/location-map/location-map.component';
import { TimestampService } from '../../services/timestamp.service';
import { TokenService } from '../../../shared/services/token.service';
import { TimestampModel } from '../../models/timestamp.model';
import { EmployeeModel } from '../../models/employee.model';
import { EmployeeService } from '../../services/employee.service';
import swal from 'sweetalert';

@Component({
  selector: 'app-timestamp-log',
  templateUrl: './timestamp-log.component.html',
  standalone: true,
  imports: [
    CommonModule,
    SharedModule,
    TranslateModule,
    NgSelectModule,
    FormsModule,
    LocationMapComponent,
    RouterModule,
    FlatpickrModule,
  ],
  styleUrls: ['./timestamp-log.component.css'],
  providers: [FlatpickrDefaults],
  encapsulation: ViewEncapsulation.None,
})
export class TimestampLogComponent implements OnInit {
  readonly pageSize = 10;

  companyId = '';
  loading = false;
  actionBusy = false;
  exporting = false;

  dateRange: { from: Date; to: Date } = {
    from: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    to: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0),
  };

  itemsList: TimestampModel[] = [];
  filteredSource: TimestampModel[] = [];
  pageItems: TimestampModel[] = [];
  selectModel?: TimestampModel;
  empList: EmployeeModel[] = [];

  empSelect = '';
  statusSelect = '';
  pageIndex = 0;
  private _searchTerm = '';

  get searchTerm(): string {
    return this._searchTerm;
  }

  set searchTerm(val: string) {
    this._searchTerm = val;
    this.pageIndex = 0;
    this.applyFilter();
  }

  get totalFiltered(): number {
    return this.filteredSource.length;
  }

  get totalAll(): number {
    return this.itemsList.length;
  }

  get completeCount(): number {
    return this.itemsList.filter(
      (x) => x.timestampType === 1 || x.timestampType === 2
    ).length;
  }

  get checkOutCount(): number {
    return this.itemsList.filter((x) => x.timestampType === 2).length;
  }

  get lateCount(): number {
    return this.itemsList.filter((x) => x.isLate).length;
  }

  get absentCount(): number {
    return this.itemsList.filter((x) => x.timestampType === 3).length;
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

  get mapLat(): number {
    return this.toCoord(this.selectModel?.latitude, 13.7563);
  }

  get mapLng(): number {
    return this.toCoord(this.selectModel?.longitude, 100.5018);
  }

  get mapsLink(): string {
    return `https://www.google.com/maps?q=${this.mapLat},${this.mapLng}`;
  }

  constructor(
    private timeService: TimestampService,
    public translate: TranslateService,
    private tokenService: TokenService,
    private employeeService: EmployeeService,
    private route: ActivatedRoute
  ) {
    this.empSelect =
      this.route.snapshot.paramMap.get('company_employeeId') || '';
    this.companyId = this.tokenService.getSelectCompany().companyId;
  }

  ngOnInit(): void {
    this.getEmp();
    this.getTimestamp();
  }

  getTimestamp() {
    if (!this.companyId) return;
    this.loading = true;
    const keepId = this.selectModel?.timestampId;
    const { from, to } = this.resolveDateRange();

    this.timeService
      .getListsSearch(
        this.companyId,
        this.empSelect || '',
        from.toISOString(),
        to.toISOString(),
        this.statusSelect || undefined
      )
      .subscribe({
        next: (result) => {
          this.itemsList = result.sort((a, b) =>
            (b.timestamp || '').localeCompare(a.timestamp || '')
          );
          this.pageIndex = 0;
          this.applyFilter(keepId);
          this.loading = false;
        },
        error: () => {
          this.loading = false;
          swal('Error', 'โหลดข้อมูลการลงเวลาไม่สำเร็จ', 'error');
        },
      });
  }

  exportReport(format: 'xlsx' | 'csv' = 'xlsx', mode: 'raw' | 'payroll' = 'raw') {
    if (!this.companyId || this.exporting) return;
    this.exporting = true;
    const { from, to } = this.resolveDateRange();

    this.timeService
      .exportReport(
        this.companyId,
        format,
        this.empSelect || undefined,
        from.toISOString(),
        to.toISOString(),
        this.statusSelect || undefined,
        undefined,
        mode
      )
      .subscribe({
        next: (blob) => {
          this.exporting = false;
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          const dateStr = new Date().toISOString().slice(0, 10);
          const prefix = mode === 'payroll' ? 'payroll_attendance' : 'attendance_report';
          a.download = `${prefix}_${dateStr}.${format}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
        },
        error: () => {
          this.exporting = false;
          swal('Error', 'ส่งออกรายงานไม่สำเร็จ', 'error');
        },
      });
  }

  getEmp() {
    this.employeeService.getLists(this.companyId).subscribe({
      next: (result) => {
        this.empList = result;
      },
    });
  }

  applyFilter(preferId?: string) {
    const q = (this._searchTerm || '').trim().toLowerCase();
    this.filteredSource = !q
      ? [...this.itemsList]
      : this.itemsList.filter((x) => this.matchesSearch(x, q));

    const maxPage = Math.max(0, Math.ceil(this.filteredSource.length / this.pageSize) - 1);
    if (this.pageIndex > maxPage) this.pageIndex = maxPage;
    this.updatePagedItems();

    if (!this.filteredSource.length) {
      this.selectModel = undefined;
      return;
    }

    const preferred =
      (preferId &&
        this.filteredSource.find((x) => x.timestampId === preferId)) ||
      (this.selectModel &&
        this.filteredSource.find(
          (x) => x.timestampId === this.selectModel!.timestampId
        ));

    this.view(preferred || this.pageItems[0] || this.filteredSource[0]);
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

  resetFilters() {
    this.empSelect = '';
    this.statusSelect = '';
    this._searchTerm = '';
    this.dateRange = {
      from: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
      to: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0),
    };
    this.getTimestamp();
  }

  view(item: TimestampModel) {
    this.selectModel = item;
  }

  isSelected(item: TimestampModel): boolean {
    return !!this.selectModel && this.selectModel.timestampId === item.timestampId;
  }

  statusTone(item: TimestampModel): 'warning' | 'success' | 'danger' | 'muted' {
    if (item.timestampType === 0 || item.isLate) return 'warning';
    if (item.timestampType === 1 || item.timestampType === 2) return 'success';
    if (item.timestampType === 3) return 'danger';
    return 'muted';
  }

  itemEnterDelay(index: number): number {
    return Math.min(index, 8) * 40;
  }

  approveTime(item: TimestampModel) {
    if (this.actionBusy) return;
    swal({
      title: 'อนุมัติการลงเวลานี้?',
      text: item.employee?.getFullname?.() || '',
      icon: 'warning',
      buttons: ['ยกเลิก', 'อนุมัติ'],
    }).then((ok: any) => {
      if (!ok) return;
      this.actionBusy = true;
      item.timestampType = 1;
      this.timeService.update(this.companyId, item).subscribe({
        next: () => {
          this.actionBusy = false;
          swal('สำเร็จ', 'อนุมัติแล้ว', 'success');
          this.getTimestamp();
        },
        error: () => {
          this.actionBusy = false;
          swal('Error', 'อนุมัติไม่สำเร็จ', 'error');
        },
      });
    });
  }

  disapproveTime(item: TimestampModel) {
    if (this.actionBusy) return;
    swal({
      title: 'ไม่อนุมัติการลงเวลานี้?',
      text: item.employee?.getFullname?.() || '',
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ไม่อนุมัติ'],
    }).then((ok: any) => {
      if (!ok) return;
      this.actionBusy = true;
      item.timestampType = 3;
      this.timeService.update(this.companyId, item).subscribe({
        next: () => {
          this.actionBusy = false;
          swal('สำเร็จ', 'บันทึกเป็น Absent แล้ว', 'success');
          this.getTimestamp();
        },
        error: () => {
          this.actionBusy = false;
          swal('Error', 'บันทึกไม่สำเร็จ', 'error');
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
      item.getStatus?.() || '',
      item.timestampId || '',
      String(item.latitude ?? ''),
      String(item.longitude ?? ''),
    ]
      .join(' ')
      .toLowerCase();
    return haystack.includes(q);
  }

  private resolveDateRange(): { from: Date; to: Date } {
    const raw: any = this.dateRange;
    if (Array.isArray(raw) && raw.length >= 2) {
      return { from: new Date(raw[0]), to: new Date(raw[1]) };
    }
    if (raw?.from && raw?.to) {
      return { from: new Date(raw.from), to: new Date(raw.to) };
    }
    const now = new Date();
    return {
      from: new Date(now.getFullYear(), now.getMonth(), 1),
      to: new Date(now.getFullYear(), now.getMonth() + 1, 0),
    };
  }

  private toCoord(value: unknown, fallback: number): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
}
