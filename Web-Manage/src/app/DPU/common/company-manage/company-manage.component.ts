import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FileItem, FileUploader, FileUploadModule } from 'ng2-file-upload';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { SimplePagerComponent } from '../../../shared/components/simple-pager/simple-pager.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { CompanyService } from '../../services/company.service';
import { CompanyModel } from '../../models/company.model';
import { TokenService } from '../../../shared/services/token.service';
import { environment } from '../../../../environments/environment';
import swal from 'sweetalert';

@Component({
  selector: 'app-company-manage',
  standalone: true,
  imports: [
    CommonModule,
    SharedModule,
    TranslateModule,
    NgSelectModule,
    FormsModule,
    FileUploadModule,
    RouterModule,
    PageToolbarComponent,
    PillSearchComponent,
    StatChipComponent,
    SimplePagerComponent,
    EmptyStateComponent,
  ],
  templateUrl: './company-manage.component.html',
  styleUrls: [
    '../../../shared/styles/dpu-list-page.css',
    './company-manage.component.css',
  ],
  encapsulation: ViewEncapsulation.None,
})
export class CompanyManageComponent implements OnInit {
  @ViewChild('closeModal') public childModal?: ElementRef;

  readonly pageSize = 10;
  action: 'add' | 'edit' = 'add';
  loading = false;
  allSelected = false;
  someSelected = false;
  pageIndex = 0;
  uploaderProfile?: FileUploader;

  itemsList: CompanyModel[] = [];
  filteredSource: CompanyModel[] = [];
  pageItems: CompanyModel[] = [];
  selectModel: CompanyModel = new CompanyModel();
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
  get publicCount(): number {
    return this.itemsList.filter((x) => x.status === 1).length;
  }

  constructor(
    private comService: CompanyService,
    public translate: TranslateService,
    private tokenService: TokenService
  ) {
    this.uploadConfig();
  }

  ngOnInit(): void {
    this.load();
  }

  load() {
    this.loading = true;
    this.comService.getLists().subscribe({
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
        swal('Error', 'โหลดบริษัทไม่สำเร็จ', 'error');
      },
    });
  }

  applyFilter() {
    const q = (this._searchTerm || '').trim().toLowerCase();
    this.filteredSource = !q
      ? [...this.itemsList]
      : this.itemsList.filter((x) =>
          [
            x.companyId,
            x.companyName,
            x.companyCode,
            x.companyInfo,
            x.address,
            x.ownerName,
            x.getStatus?.(),
          ]
            .join(' ')
            .toLowerCase()
            .includes(q)
        );
    const maxPage = Math.max(0, Math.ceil(this.filteredSource.length / this.pageSize) - 1);
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

  uploadConfig() {
    this.uploaderProfile = new FileUploader({
      url: environment.baseUrl + '/api/upload-image',
      isHTML5: true,
      authToken: this.tokenService.getToken()!,
    });
    this.uploaderProfile.onAfterAddingFile = (fileItem: FileItem) => {
      fileItem.withCredentials = false;
      while (this.uploaderProfile!.queue.length > 1) this.uploaderProfile!.queue[0].remove();
      if (fileItem.file.size > 5000000) {
        swal('ไฟล์ใหญ่เกินไป', 'ขนาดสูงสุด 5MB', 'info');
        fileItem.isCancel = true;
        return;
      }
      if (fileItem.file.type!.indexOf('image') === -1) {
        swal('ไฟล์ไม่ถูกต้อง', 'อัปโหลดรูปภาพเท่านั้น', 'info');
        fileItem.isCancel = true;
        return;
      }
      fileItem.upload();
    };
    this.uploaderProfile.onCompleteItem = (item: FileItem, response: string) => {
      if (item.isSuccess) {
        const res = JSON.parse(response);
        this.selectModel.picture = res.filename;
        swal('สำเร็จ', res.message || 'อัปโหลดแล้ว', 'success');
      } else {
        swal('อัปโหลดไม่สำเร็จ', '', 'error');
      }
    };
  }

  new() {
    this.action = 'add';
    this.selectModel = new CompanyModel();
    this.selectModel.status = 1;
    this.selectModel.address = '';
    this.selectModel.latitude = 0;
    this.selectModel.longitude = 0;
    this.selectModel.picture = '';
  }

  view(item: CompanyModel) {
    this.action = 'edit';
    this.selectModel = new CompanyModel(item);
  }

  save() {
    if (!(this.selectModel.companyName || '').trim()) {
      swal('ข้อมูลไม่ครบ', 'กรุณากรอกชื่อบริษัท', 'warning');
      return;
    }
    swal({
      title: 'ยืนยันการบันทึก?',
      text: this.selectModel.companyName,
      icon: 'warning',
      buttons: ['ยกเลิก', 'บันทึก'],
    }).then((ok: any) => {
      if (!ok) return;
      const req$ =
        this.action === 'edit'
          ? this.comService.update(this.selectModel)
          : this.comService.save(this.selectModel);
      req$.subscribe({
        next: () => {
          swal('สำเร็จ', 'บันทึกข้อมูลบริษัท', 'success');
          this.load();
          this.childModal?.nativeElement.click();
        },
        error: () => swal('Error', 'บันทึกไม่สำเร็จ', 'error'),
      });
    });
  }

  delete(item: CompanyModel) {
    swal({
      title: 'ลบบริษัทนี้?',
      text: item.companyName || '',
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ลบ'],
    }).then((ok: any) => {
      if (!ok) return;
      this.comService.delete(item).subscribe({
        next: () => {
          swal('สำเร็จ', 'ลบแล้ว', 'success');
          this.load();
        },
        error: () => swal('Error', 'ลบไม่สำเร็จ', 'error'),
      });
    });
  }

  toggleAll(event: Event) {
    const checked = !!(event.target as HTMLInputElement)?.checked;
    this.allSelected = checked;
    this.selectedItems.clear();
    this.filteredSource.forEach((item) => this.selectedItems.set(item.companyId, checked));
    this.someSelected = checked && this.filteredSource.length > 0;
  }

  onCheckboxChange(companyId: string, event: Event) {
    const checked = !!(event.target as HTMLInputElement)?.checked;
    this.selectedItems.set(companyId, checked);
    this.allSelected =
      this.filteredSource.length > 0 &&
      this.filteredSource.every((item) => this.selectedItems.get(item.companyId));
    this.someSelected = this.filteredSource.some((item) => this.selectedItems.get(item.companyId));
  }

  selectedTargets(): CompanyModel[] {
    return this.filteredSource.filter((item) => this.selectedItems.get(item.companyId));
  }

  deleteSelect() {
    const targets = this.selectedTargets();
    if (!targets.length) return;
    swal({
      title: `ลบ ${targets.length} บริษัท?`,
      text: targets.map((t) => t.companyName).join('\n'),
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ลบ'],
    }).then((ok: any) => {
      if (!ok) return;
      let pending = targets.length;
      targets.forEach((item) => {
        this.comService.delete(item).subscribe({
          next: () => {
            pending -= 1;
            if (pending <= 0) {
              swal('สำเร็จ', 'ลบแล้ว', 'success');
              this.load();
            }
          },
          error: () => {
            pending -= 1;
            if (pending <= 0) this.load();
          },
        });
      });
    });
  }

  adjustSelect(status: number) {
    const targets = this.selectedTargets();
    if (!targets.length) return;
    swal({
      title: status === 1 ? 'ตั้งเป็น Public?' : 'ตั้งเป็น Pending?',
      text: targets.map((t) => t.companyName).join('\n'),
      icon: 'warning',
      buttons: ['ยกเลิก', 'ยืนยัน'],
    }).then((ok: any) => {
      if (!ok) return;
      let pending = targets.length;
      targets.forEach((item) => {
        item.status = status;
        this.comService.update(item).subscribe({
          next: () => {
            pending -= 1;
            if (pending <= 0) {
              swal('สำเร็จ', 'อัปเดตแล้ว', 'success');
              this.load();
            }
          },
          error: () => {
            pending -= 1;
            if (pending <= 0) this.load();
          },
        });
      });
    });
  }
}
