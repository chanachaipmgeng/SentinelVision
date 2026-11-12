import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FileItem, FileUploader, FileUploadModule } from 'ng2-file-upload';
import { firstValueFrom } from 'rxjs';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { SimplePagerComponent } from '../../../shared/components/simple-pager/simple-pager.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { UserService } from '../../services/user.service';
import { UserProfileModel } from '../../models/user.model';
import { EmployeeModel } from '../../models/employee.model';
import { TokenService } from '../../../shared/services/token.service';
import { environment } from '../../../../environments/environment';
import { EmpFaceEnrollModalComponent } from '../../company-management/company-emp/company-emp-enroll/emp-face-enroll-modal.component';
import { FaceManagementComponent } from '../../company-management/dialogs/face-management/face-management.component';
import { apiErrorMessage } from '../../../shared/utils/http-error-body';
import swal from 'sweetalert';

type ConsentPolicy = {
  version: string;
  textTh: string;
  textEn: string;
  updatedAt?: string | null;
  galleryKey?: string | null;
};

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
        EmpFaceEnrollModalComponent,
        FaceManagementComponent,
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
  @ViewChild('faceEnrollModal') faceEnrollModal?: EmpFaceEnrollModalComponent;
  @ViewChild('openFaceOverlay') openFaceOverlay?: ElementRef<HTMLButtonElement>;
  @ViewChild('openConsentOverlay') openConsentOverlay?: ElementRef<HTMLButtonElement>;
  @ViewChild('closeConsentOverlay') closeConsentOverlay?: ElementRef<HTMLButtonElement>;

  readonly pageSize = 10;
  readonly adminRole = 99;

  action: 'add' | 'edit' = 'add';
  loading = false;
  allSelected = false;
  someSelected = false;
  confirmPassword = '';
  pageIndex = 0;
  uploaderProfile?: FileUploader;
  /** Empty companyId — system-admin enroll writes a local encoding only. */
  faceEnrollCompanyId = '';
  faceEnrollSelectModel: EmployeeModel = new EmployeeModel();
  selectedMemberId = '';
  selectedMemberName = '';

  consentPolicy: ConsentPolicy | null = null;
  consentLoading = false;
  consentGranting = false;
  pendingConsentMember: UserProfileModel | null = null;

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
  get consentedCount(): number {
    return this.itemsList.filter((x) => x.hasBiometricConsent()).length;
  }
  get faceEnrolledCount(): number {
    return this.itemsList.filter((x) => x.hasFaceEnrolled()).length;
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

  consentText(): string {
    const locale = (this.translate.currentLang || 'th').toLowerCase();
    if (!this.consentPolicy) return '';
    return locale.startsWith('th')
      ? this.consentPolicy.textTh
      : this.consentPolicy.textEn || this.consentPolicy.textTh;
  }

  async openFaceEnroll(item: UserProfileModel): Promise<void> {
    if (!item?.memberId) return;
    if (item.hasBiometricConsent()) {
      await this.startFaceEnroll(item);
      return;
    }
    this.pendingConsentMember = item;
    this.consentLoading = true;
    this.consentPolicy = null;
    this.openConsentOverlay?.nativeElement?.click();
    try {
      this.consentPolicy = await firstValueFrom(this.userService.getSystemConsentPolicy());
    } catch (err) {
      this.closeConsentDialog();
      swal('โหลดนโยบายไม่สำเร็จ', apiErrorMessage(err, 'Consent policy failed'), 'error');
    } finally {
      this.consentLoading = false;
    }
  }

  closeConsentDialog(): void {
    this.pendingConsentMember = null;
    this.consentGranting = false;
    this.closeConsentOverlay?.nativeElement?.click();
  }

  async acceptConsentAndEnroll(): Promise<void> {
    const item = this.pendingConsentMember;
    if (!item?.memberId || this.consentGranting) return;
    this.consentGranting = true;
    try {
      await firstValueFrom(this.userService.grantBiometricConsent(item.memberId, 'th'));
      item.biometricConsentAt = new Date().toISOString();
      this.closeConsentDialog();
      await this.startFaceEnroll(item);
      this.load();
    } catch (err) {
      swal('ไม่สามารถบันทึกความยินยอมได้', apiErrorMessage(err, 'Consent failed'), 'error');
    } finally {
      this.consentGranting = false;
    }
  }

  private async startFaceEnroll(item: UserProfileModel): Promise<void> {
    this.faceEnrollSelectModel = new EmployeeModel({
      member: item,
      companyId: '',
    });
    this.openFaceOverlay?.nativeElement?.click();
    await this.faceEnrollModal?.openForEmployee(this.faceEnrollSelectModel);
  }

  openFaceManagementModal(item: UserProfileModel): void {
    this.selectedMemberId = item?.memberId || '';
    this.selectedMemberName = item?.getFullname?.() || item?.username || '';
  }

  onFaceManagementClosed(): void {
    this.selectedMemberId = '';
    this.load();
  }

  revokeConsent(item: UserProfileModel): void {
    if (!item?.memberId || !item.hasBiometricConsent()) return;
    swal({
      title: 'เพิกถอนความยินยอม PDPA?',
      text: 'จะลบข้อมูลใบหน้าสำหรับเข้าสู่ระบบคอนโซลของผู้ดูแลรายนี้',
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'เพิกถอน'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.userService.revokeBiometricConsent(item.memberId).subscribe({
        next: () => {
          swal('สำเร็จ', 'เพิกถอนความยินยอมและลบใบหน้าแล้ว', 'success');
          this.load();
        },
        error: (err) =>
          swal('เพิกถอนไม่สำเร็จ', apiErrorMessage(err, 'Revoke failed'), 'error'),
      });
    });
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
