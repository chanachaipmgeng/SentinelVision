import { CommonModule } from '@angular/common';
import { Component, ElementRef, ViewChild, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { SharedModule } from '../../../../shared/shared.module';
import { PageToolbarComponent } from '../../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../../shared/components/pill-search/pill-search.component';
import { StatChipComponent } from '../../../../shared/components/stat-chip/stat-chip.component';
import { SimplePagerComponent } from '../../../../shared/components/simple-pager/simple-pager.component';
import { EmptyStateComponent } from '../../../../shared/components/empty-state/empty-state.component';
import { PositionService } from '../../../services/position.service';
import { PositionModel } from '../../../models/position.model';
import { TokenService } from '../../../../shared/services/token.service';
import { downloadCsv } from '../../../company-management/sentinel-center/sentinel.helpers';
import swal from 'sweetalert';

@Component({
    selector: 'app-position',
    imports: [
        CommonModule,
        SharedModule,
        TranslateModule,
        FormsModule,
        PageToolbarComponent,
        PillSearchComponent,
        StatChipComponent,
        SimplePagerComponent,
        EmptyStateComponent,
    ],
    templateUrl: './position.component.html',
    styleUrls: [
        '../../../../shared/styles/dpu-list-page.css',
        './position.component.css',
    ],
    encapsulation: ViewEncapsulation.None
})
export class PositionComponent {
  @ViewChild('closeModal') public childModal?: ElementRef;

  readonly pageSize = 10;
  companyId = '';
  loading = false;
  allSelected = false;
  someSelected = false;
  isEdit = false;
  pageIndex = 0;

  itemsList: PositionModel[] = [];
  filteredSource: PositionModel[] = [];
  pageItems: PositionModel[] = [];
  selectModel: PositionModel = new PositionModel();
  selectedItems = new Map<string, boolean>();
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

  constructor(
    private positionService: PositionService,
    private tokenService: TokenService,
    public translate: TranslateService
  ) {
    this.companyId = this.tokenService.getSelectCompany()?.companyId || '';
    if (!this.companyId) {
      this.loading = false;
      return;
    }
    this.getPosition();
  }

  getPosition() {
    if (!this.companyId) {
      this.loading = false;
      return;
    }
    this.loading = true;
    this.positionService.getLists(this.companyId).subscribe({
      next: (result) => {
        this.itemsList = result || [];
        this.selectedItems.clear();
        this.allSelected = false;
        this.someSelected = false;
        this.applyFilter();
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        swal('Error', 'โหลดตำแหน่งไม่สำเร็จ', 'error');
      },
    });
  }

  applyFilter() {
    const q = (this._searchTerm || '').trim().toLowerCase();
    this.filteredSource = !q
      ? [...this.itemsList]
      : this.itemsList.filter(
          (x) =>
            (x.positionId || '').toLowerCase().includes(q) ||
            (x.thName || '').toLowerCase().includes(q) ||
            (x.engName || '').toLowerCase().includes(q)
        );
    const maxPage = Math.max(
      0,
      Math.ceil(this.filteredSource.length / this.pageSize) - 1
    );
    if (this.pageIndex > maxPage) this.pageIndex = maxPage;
    this.updatePagedItems();
  }

  updatePagedItems() {
    const start = this.pageIndex * this.pageSize;
    this.pageItems = this.filteredSource.slice(start, start + this.pageSize);
  }

  onPageChange(page: number) {
    this.pageIndex = page;
    this.updatePagedItems();
  }

  clearSearch() {
    this.searchTerm = '';
  }

  delete(item: PositionModel) {
    if (item.employeeCount > 0) {
      swal('ไม่สามารถลบได้', `ตำแหน่ง "${item.thName}" ยังมีพนักงานใช้งานอยู่ ${item.employeeCount} คน กรุณาย้ายพนักงานออกก่อน`, 'warning');
      return;
    }
    swal({
      title: 'ลบตำแหน่งนี้?',
      text: item.thName || '',
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ลบ'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.positionService.delete(item).subscribe({
        next: () => {
          swal('สำเร็จ', 'ลบแล้ว', 'success');
          this.getPosition();
        },
        error: (err) => {
          const msg = err?.error?.detail || 'ลบไม่สำเร็จ';
          swal('Error', msg, 'error');
        },
      });
    });
  }

  new() {
    this.isEdit = false;
    this.selectModel = new PositionModel();
  }

  view(item: PositionModel) {
    this.isEdit = true;
    this.selectModel = new PositionModel(item);
  }

  save() {
    if (!(this.selectModel.thName || '').trim() || !(this.selectModel.engName || '').trim()) {
      swal('ข้อมูลไม่ครบ', 'กรุณากรอกชื่อภาษาไทยและอังกฤษ', 'warning');
      return;
    }
    swal({
      title: 'ยืนยันการบันทึก?',
      text: this.selectModel.thName,
      icon: 'warning',
      buttons: ['ยกเลิก', 'บันทึก'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.selectModel.companyId = this.companyId;
      const req$ = this.isEdit
        ? this.positionService.update(this.selectModel)
        : this.positionService.save(this.selectModel);
      req$.subscribe({
        next: () => {
          swal('สำเร็จ', 'บันทึกข้อมูลสำเร็จ', 'success');
          this.getPosition();
          this.childModal?.nativeElement.click();
        },
        error: () => swal('Error', 'บันทึกไม่สำเร็จ', 'error'),
      });
    });
  }

  toggleAll(event: Event) {
    const checked = !!(event.target as HTMLInputElement)?.checked;
    this.allSelected = checked;
    this.selectedItems.clear();
    this.filteredSource.forEach((item) => {
      this.selectedItems.set(item.positionId, checked);
    });
    this.someSelected = checked && this.filteredSource.length > 0;
  }

  onCheckboxChange(positionId: string, event: Event) {
    const checked = !!(event.target as HTMLInputElement)?.checked;
    this.selectedItems.set(positionId, checked);
    this.allSelected =
      this.filteredSource.length > 0 &&
      this.filteredSource.every((item) => this.selectedItems.get(item.positionId));
    this.someSelected = this.filteredSource.some((item) =>
      this.selectedItems.get(item.positionId)
    );
  }

  deleteSelect() {
    const targets = this.filteredSource.filter((item) =>
      this.selectedItems.get(item.positionId)
    );
    if (!targets.length) return;
    const names = targets.map((t) => t.thName).join('\n');
    swal({
      title: `ลบ ${targets.length} ตำแหน่ง?`,
      text: names,
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ลบ'],
    }).then((ok: unknown) => {
      if (!ok) return;
      let pending = targets.length;
      targets.forEach((item) => {
        this.positionService.delete(item).subscribe({
          next: () => {
            pending -= 1;
            if (pending <= 0) {
              swal('สำเร็จ', 'ลบแล้ว', 'success');
              this.getPosition();
            }
          },
          error: () => {
            pending -= 1;
            if (pending <= 0) this.getPosition();
          },
        });
      });
    });
  }

  exportCsv(): void {
    downloadCsv(
      ['PositionID', 'NameTH', 'NameEN', 'EmployeeCount'],
      this.filteredSource.map((p) => [
        p.positionId || '',
        p.thName || '',
        p.engName || '',
        p.employeeCount ?? 0,
      ]),
      'positions',
    );
  }
}
