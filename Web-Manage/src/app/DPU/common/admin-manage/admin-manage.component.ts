import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FileItem, FileUploader, FileUploadModule } from 'ng2-file-upload';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { SimplePagerComponent } from '../../../shared/components/simple-pager/simple-pager.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { UserService } from '../../services/user.service';
import { UserProfileModel } from '../../models/user.model';
import { TokenService } from '../../../shared/services/token.service';
import { environment } from '../../../../environments/environment';
import swal from 'sweetalert';

@Component({
    selector: 'app-admin-manage',
    imports: [
        CommonModule,
        SharedModule,
        TranslateModule,
        NgSelectModule,
        FormsModule,
        FileUploadModule,
        PageToolbarComponent,
        PillSearchComponent,
        StatChipComponent,
        SimplePagerComponent,
        EmptyStateComponent,
    ],
    templateUrl: './admin-manage.component.html',
    styleUrls: [
        '../../../shared/styles/dpu-list-page.css',
        './admin-manage.component.css',
    ],
    encapsulation: ViewEncapsulation.None
})
export class AdminManageComponent implements OnInit {
  @ViewChild('closeModal') public childModal?: ElementRef;

  readonly pageSize = 10;
  readonly adminRole = 99;

  action: 'add' | 'edit' = 'add';
  loading = false;
  allSelected = false;
  someSelected = false;
  confirmPassword = '';
  pageIndex = 0;
  uploaderProfile?: FileUploader;

  itemsList: UserProfileModel[] = [];
  filteredSource: UserProfileModel[] = [];
  pageItems: UserProfileModel[] = [];
  selectModel: UserProfileModel = new UserProfileModel();
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
  get activeCount(): number {
    return this.itemsList.filter((x) => x.status === 1).length;
  }

  constructor(
    private userService: UserService,
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
    this.userService.getLists().subscribe({
      next: (result) => {
        this.itemsList = (result || []).filter((e) => e.role == this.adminRole);
        this.selectedItems.clear();
        this.allSelected = false;
        this.someSelected = false;
        this.applyFilter();
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        swal('Error', 'โหลดผู้ดูแลไม่สำเร็จ', 'error');
      },
    });
  }

  applyFilter() {
    const q = (this._searchTerm || '').trim().toLowerCase();
    this.filteredSource = !q
      ? [...this.itemsList]
      : this.itemsList.filter((x) =>
          [x.memberId, x.username, x.email, x.phoneNumber, x.getStatus?.(), x.getFullname?.()]
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
    this.confirmPassword = '';
    this.selectModel = new UserProfileModel();
    this.selectModel.role = this.adminRole;
  }

  view(item: UserProfileModel) {
    this.action = 'edit';
    this.confirmPassword = '';
    this.selectModel = new UserProfileModel(item);
    this.selectModel.role = this.adminRole;
  }

  save() {
    if (this.action === 'add' && this.confirmPassword !== this.selectModel.password) {
      swal('รหัสผ่านไม่ตรงกัน', '', 'warning');
      return;
    }
    this.selectModel.role = this.adminRole;
    swal({
      title: 'ยืนยันการบันทึก?',
      text: this.selectModel.username || '',
      icon: 'warning',
      buttons: ['ยกเลิก', 'บันทึก'],
    }).then((ok: unknown) => {
      if (!ok) return;
      const req$ =
        this.action === 'edit'
          ? this.userService.update(this.selectModel)
          : this.userService.save(this.selectModel);
      req$.subscribe({
        next: () => {
          swal('สำเร็จ', 'บันทึกผู้ดูแลระบบ', 'success');
          this.load();
          this.childModal?.nativeElement.click();
        },
        error: () => swal('Error', 'บันทึกไม่สำเร็จ', 'error'),
      });
    });
  }

  delete(item: UserProfileModel) {
    swal({
      title: 'ลบผู้ดูแลนี้?',
      text: item.getFullname?.() || item.username,
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ลบ'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.userService.delete(item).subscribe({
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
    this.filteredSource.forEach((item) => this.selectedItems.set(item.memberId, checked));
    this.someSelected = checked && this.filteredSource.length > 0;
  }

  onCheckboxChange(memberId: string, event: Event) {
    const checked = !!(event.target as HTMLInputElement)?.checked;
    this.selectedItems.set(memberId, checked);
    this.allSelected =
      this.filteredSource.length > 0 &&
      this.filteredSource.every((item) => this.selectedItems.get(item.memberId));
    this.someSelected = this.filteredSource.some((item) => this.selectedItems.get(item.memberId));
  }

  selectedTargets(): UserProfileModel[] {
    return this.filteredSource.filter((item) => this.selectedItems.get(item.memberId));
  }

  deleteSelect() {
    const targets = this.selectedTargets();
    if (!targets.length) return;
    swal({
      title: `ลบ ${targets.length} ผู้ดูแล?`,
      text: targets.map((t) => t.getFullname?.() || t.username).join('\n'),
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ลบ'],
    }).then((ok: unknown) => {
      if (!ok) return;
      let pending = targets.length;
      targets.forEach((user) => {
        this.userService.delete(user).subscribe({
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
      title: status === 1 ? 'เปิดใช้งานที่เลือก?' : 'ปิดใช้งานที่เลือก?',
      text: targets.map((t) => t.getFullname?.() || t.username).join('\n'),
      icon: 'warning',
      buttons: ['ยกเลิก', 'ยืนยัน'],
    }).then((ok: unknown) => {
      if (!ok) return;
      let pending = targets.length;
      targets.forEach((user) => {
        user.status = status;
        user.role = this.adminRole;
        this.userService.update(user).subscribe({
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
