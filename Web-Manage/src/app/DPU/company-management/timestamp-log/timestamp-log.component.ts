import { Component, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
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
import { clampPageIndex } from '../../../shared/utils/data-table-query';
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
export class TimestampLogComponent implements OnInit, OnDestroy {
  readonly pageSize = 10;

  companyId = '';
  loading = false;
  actionBusy = false;
  exporting = false;

  dateRange: { from: Date; to: Date } = {
    from: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    to: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0),
  };

  /** Current page from server. */
  itemsList: TimestampModel[] = [];
  pageItems: TimestampModel[] = [];
  selectModel?: TimestampModel;
  empList: EmployeeModel[] = [];
  serverTotal = 0;
  sortBy: string | null = 'timestamp';
  sortDir: 'asc' | 'desc' | null = 'desc';

  empSelect = '';
  statusSelect = '';
  pageIndex = 0;
  private _searchTerm = '';
  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  get searchTerm(): string {
    return this._searchTerm;
  }

  set searchTerm(val: string) {
    this._searchTerm = val;
    this.pageIndex = 0;
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.getTimestamp(), 250);
  }

  get totalFiltered(): number {
    return this.serverTotal;
  }

  get totalAll(): number {
    return this.serverTotal;
  }

  get completeCount(): number {
    return this.pageItems.filter(
      (x) => x.timestampType === 1 || x.timestampType === 2
    ).length;
  }

  get checkOutCount(): number {
    return this.pageItems.filter((x) => x.timestampType === 2).length;
  }

  get lateCount(): number {
    return this.pageItems.filter((x) => x.isLate).length;
  }

  get absentCount(): number {
    return this.pageItems.filter((x) => x.timestampType === 3).length;
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

  ngOnDestroy(): void {
    if (this.searchTimer) clearTimeout(this.searchTimer);
  }

  getTimestamp(preferId?: string) {
    if (!this.companyId) return;
    this.loading = true;
    const keepId = preferId || this.selectModel?.timestampId;
    const { from, to } = this.resolveDateRange();

    this.timeService
      .searchPage(this.companyId, {
        pageIndex: this.pageIndex,
        pageSize: this.pageSize,
        q: this._searchTerm,
        sortBy: this.sortBy,
        sortDir: this.sortDir || 'desc',
        company_employeeId: this.empSelect || undefined,
        startDate: from.toISOString(),
        endDate: to.toISOString(),
        timestampType: this.statusSelect || undefined,
      })
      .subscribe({
        next: (page) => {
          this.serverTotal = page.total;
          this.pageIndex = clampPageIndex(this.pageIndex, page.total, this.pageSize);
          this.itemsList = page.items || [];
          this.pageItems = this.itemsList;
          this.loading = false;
          if (!this.pageItems.length) {
            this.selectModel = undefined;
            return;
          }
          const preferred =
            (keepId && this.pageItems.find((x) => x.timestampId === keepId)) ||
            this.pageItems[0];
          this.view(preferred);
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

  goToPage(page: number) {
    const next = Math.max(0, Math.min(page, this.totalPages - 1));
    if (next === this.pageIndex) return;
    this.pageIndex = next;
    this.getTimestamp();
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
    this.pageIndex = 0;
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
