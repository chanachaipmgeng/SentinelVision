import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild, OnInit,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { FileItem, FileUploader, FileUploadModule, ParsedResponseHeaders } from 'ng2-file-upload';
import swal from 'sweetalert';
import { HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { MaterialModuleModule } from '../../../material-module/material-module.module';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import { FaceManagementComponent } from '../dialogs/face-management/face-management.component';
import { DepartmentModel } from '../../models/department.model';
import { EmployeeModel } from '../../models/employee.model';
import { PositionModel } from '../../models/position.model';
import { DepartmentService } from '../../services/department.service';
import { EmployeeImportProgress, EmployeeService } from '../../services/employee.service';
import { PositionService } from '../../services/position.service';
import { EmpFaceEnrollModalComponent } from './company-emp-enroll/emp-face-enroll-modal.component';
import { EmpDetailModalComponent } from './company-emp-form/emp-detail-modal.component';
import { EmpImportOverlayComponent } from './company-emp-import/emp-import-overlay.component';
import { EmpImportService } from './company-emp-import/emp-import.service';
import { EmpListComponent } from './company-emp-list/emp-list.component';
import {
  EmpListViewMode,
  defaultListViewForTotal,
  formatApiError,
  pageEnd as calcPageEnd,
  pageSizeForView,
  pageStart as calcPageStart,
  readStoredListView,
  saveErrorTitle,
  totalPages,
  translateApiMessage,
  validateEmployeeForm,
  writeStoredListView,
} from './company-emp.helpers';
import { clampPageIndex } from '../../../shared/utils/data-table-query';

/**
 * Company employees shell — toolbar + list/form/import/enroll children.
 * Pure filter/paging/validate helpers live in company-emp.helpers.ts.
 */
@Component({
    selector: 'app-company-emp',
    imports: [
        SharedModule,
        NgSelectModule,
        RouterModule,
        MaterialModuleModule,
        TranslateModule,
        FlatpickrModule,
        MatDatepickerModule,
        FormsModule,
        CommonModule,
        FileUploadModule,
        FaceManagementComponent,
        EmpListComponent,
        EmpDetailModalComponent,
        EmpImportOverlayComponent,
        EmpFaceEnrollModalComponent,
    ],
    providers: [FlatpickrDefaults, EmpImportService],
    templateUrl: './company-emp.component.html',
    styleUrl: './company-emp.component.css'
})
export class CompanyEmpComponent implements OnDestroy, AfterViewInit, OnInit {
  @ViewChild('detailModal') detailModal?: EmpDetailModalComponent;
  @ViewChild('faceEnrollModal') faceEnrollModal?: EmpFaceEnrollModalComponent;
  @ViewChild('importFileInput') importFileInput?: ElementRef<HTMLInputElement>;
  @ViewChild('importPhotosInput') importPhotosInput?: ElementRef<HTMLInputElement>;

  uploaderProfile: FileUploader | undefined;
  uploadErrorMsg = '';
  /** Current page rows from server (Phase E2). */
  itemsList: EmployeeModel[] = [];
  filterList: EmployeeModel[] = [];
  selectModel: EmployeeModel = new EmployeeModel();
  departmentList: DepartmentModel[] = [];
  positionList: PositionModel[] = [];
  pageIndex = 0;
  pageSize = 10;
  /** Total matching rows from server page envelope. */
  serverTotal = 0;
  listLoading = false;
  listViewMode: EmpListViewMode = 'cards';
  /** False until user picks a view or we apply a stored/default preference. */
  private listViewPreferenceLocked = false;
  selectedMemberId: string | null = null;
  selectedMemberName = '';
  companyId = '';
  _searchTerm = '';
  sortBy: string | null = 'employeeId';
  sortDir: 'asc' | 'desc' | null = 'asc';
  isEdit = false;
  isImporting = false;
  importProgress: EmployeeImportProgress | null = null;
  importStatusText = 'กรุณารอสักครู่ ระบบกำลังบันทึกข้อมูลและใบหน้า';
  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  private readonly bodyModalIds = ['modal-face', 'modal-detail', 'modal-face-management'];
  private movedModalNodes: HTMLElement[] = [];

  get searchTerm(): string {
    return this._searchTerm;
  }
  set searchTerm(val: string) {
    this.pageIndex = 0;
    this._searchTerm = val ?? '';
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.reloadEmployees(), 250);
  }

  get totalFiltered(): number {
    return this.serverTotal;
  }

  get totalPages(): number {
    return totalPages(this.totalFiltered, this.pageSize);
  }

  get pageStart(): number {
    return calcPageStart(this.totalFiltered, this.pageIndex, this.pageSize);
  }

  get pageEnd(): number {
    return calcPageEnd(this.totalFiltered, this.pageIndex, this.pageSize);
  }

  constructor(
    private employeeService: EmployeeService,
    public translate: TranslateService,
    private departmentService: DepartmentService,
    private positionService: PositionService,
    private tokenService: TokenService,
    private cdr: ChangeDetectorRef,
    private importService: EmpImportService,
  ) {
    this.uploadConfig();
    this.companyId = this.tokenService.getSelectCompany()?.companyId || '';
    const storedView = readStoredListView();
    if (storedView) {
      this.listViewMode = storedView;
      this.listViewPreferenceLocked = true;
    } else {
      this.listViewMode = 'cards';
    }
    this.pageSize = pageSizeForView(this.listViewMode);
    this.importService.state$.subscribe((s) => {
      this.isImporting = s.isImporting;
      this.importProgress = s.progress;
      this.importStatusText = s.statusText;
      this.cdr.detectChanges();
    });
  }

  ngAfterViewInit(): void {
    this.bodyModalIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el && el.parentElement !== document.body) {
        document.body.appendChild(el);
        this.movedModalNodes.push(el);
      }
    });
  }

  ngOnDestroy(): void {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.faceEnrollModal?.closeFaceEnrollModal();
    this.movedModalNodes.forEach((el) => el.remove());
    this.movedModalNodes = [];
  }

  ngOnInit(): void {
    this.reloadEmployees();
    this.getDepartment();
    this.getPosition();
  }

  setListViewMode(mode: EmpListViewMode, opts: { persist?: boolean; reload?: boolean } = {}): void {
    const persist = opts.persist !== false;
    const reload = opts.reload !== false;
    if (this.listViewMode === mode && this.pageSize === pageSizeForView(mode)) {
      if (persist) {
        this.listViewPreferenceLocked = true;
        writeStoredListView(mode);
      }
      return;
    }
    this.listViewMode = mode;
    this.pageSize = pageSizeForView(mode);
    this.pageIndex = 0;
    if (persist) {
      this.listViewPreferenceLocked = true;
      writeStoredListView(mode);
    }
    if (reload) {
      this.reloadEmployees();
    }
  }

  getDepartment(): void {
    this.departmentService.getLists(this.companyId).subscribe((result) => {
      this.departmentList = result;
    });
  }

  getPosition(): void {
    this.positionService.getLists(this.companyId).subscribe((result) => {
      this.positionList = result;
    });
  }

  /** Server-side pagination / filter / sort (Phase E2). */
  reloadEmployees(): void {
    if (!this.companyId) return;
    this.listLoading = true;
    this.employeeService
      .getPage(this.companyId, {
        pageIndex: this.pageIndex,
        pageSize: this.pageSize,
        q: this._searchTerm,
        sortBy: this.sortBy,
        sortDir: this.sortDir || 'asc',
      })
      .subscribe({
        next: (page) => {
          this.serverTotal = page.total;
          if (!this.listViewPreferenceLocked) {
            const denser = defaultListViewForTotal(page.total);
            if (denser !== this.listViewMode) {
              this.listViewMode = denser;
              this.pageSize = pageSizeForView(denser);
              this.pageIndex = 0;
              // Re-fetch once with the denser page size; lock so we don't loop.
              this.listViewPreferenceLocked = true;
              this.reloadEmployees();
              return;
            }
            this.listViewPreferenceLocked = true;
          }
          this.pageIndex = clampPageIndex(this.pageIndex, page.total, this.pageSize);
          this.itemsList = (page.items || []).filter((row): row is EmployeeModel => !!row);
          this.filterList = this.itemsList;
          this.listLoading = false;
          this.cdr.detectChanges();
        },
        error: () => {
          this.listLoading = false;
          swal('Error', 'โหลดรายชื่อพนักงานไม่สำเร็จ', 'error');
        },
      });
  }

  goToPage(index: number): void {
    if (index < 0 || index >= this.totalPages) return;
    this.pageIndex = index;
    this.reloadEmployees();
  }

  nextPage(): void {
    this.goToPage(this.pageIndex + 1);
  }

  prevPage(): void {
    this.goToPage(this.pageIndex - 1);
  }

  delete(item: EmployeeModel): void {
    swal({
      title: 'Are you sure?',
      text: "You won't be able to revert this!",
      icon: 'warning',
      dangerMode: true,
      buttons: ['Cancel', 'Yes,Delete it!'],
    }).then((willDelete: unknown) => {
      if (willDelete) {
        this.employeeService.delete(this.companyId, item).subscribe(() => {
          swal('Save Success!!', 'บันทึกข้อมูลสำเร็จ', 'success');
          this.ngOnInit();
        });
      }
    });
  }

  new(): void {
    this.isEdit = false;
    this.selectModel = new EmployeeModel();
  }

  view(item: EmployeeModel): void {
    this.isEdit = true;
    this.selectModel = item;
  }

  async openFaceEnroll(item: EmployeeModel): Promise<void> {
    this.view(item);
    await this.faceEnrollModal?.openForEmployee(item);
  }

  openFaceManagementModal(item: EmployeeModel): void {
    if (item.member?.memberId) {
      this.selectedMemberId = item.member.memberId;
      const first = item.member.firstName || '';
      const last = item.member.lastName || '';
      this.selectedMemberName =
        [first, last].filter(Boolean).join(' ').trim() ||
        item.employeeId ||
        item.member.memberId;
    }
  }

  downloadImportTemplate(): void {
    this.employeeService.downloadImportTemplate(this.companyId).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'employee-import-template.xlsx';
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => {
        void this.resolveBlobError(err).then((msg) => swal('ดาวน์โหลดไม่สำเร็จ', msg, 'error'));
      },
    });
  }

  triggerImportFile(): void {
    if (this.isImporting) return;
    this.importService.setPendingExcel(null);
    if (this.importFileInput?.nativeElement) {
      this.importFileInput.nativeElement.value = '';
      this.importFileInput.nativeElement.click();
    }
  }

  onImportFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    const err = this.importService.validateExcel(file);
    if (err) {
      swal('ไฟล์ไม่ถูกต้อง', err, 'warning');
      input.value = '';
      return;
    }
    this.importService.setPendingExcel(file);
    input.value = '';
    swal({
      title: 'นำเข้าพนักงานจาก Excel?',
      text:
        `ไฟล์: ${file.name}\n\n` +
        'ต้องการแนบ ZIP รูปใบหน้าด้วยหรือไม่?\n' +
        '(ชื่อไฟล์ใน ZIP ควรตรงคอลัมน์ ไฟล์รูปใบหน้า หรือใช้อีเมล/รหัสพนักงาน)',
      icon: 'info',
      buttons: {
        cancel: { text: 'Cancel', value: null, visible: true },
        skip: { text: 'นำเข้าโดยไม่มีรูป', value: 'skip' },
        zip: { text: 'แนบ ZIP รูป', value: 'zip' },
      },
    }).then((choice: string | null) => {
      if (!choice) {
        this.importService.setPendingExcel(null);
        return;
      }
      if (choice === 'zip') {
        if (this.importPhotosInput?.nativeElement) {
          this.importPhotosInput.nativeElement.value = '';
          this.importPhotosInput.nativeElement.click();
        }
        return;
      }
      this.runEmployeeImport(null);
    });
  }

  onImportPhotosSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const zip = input.files?.[0] || null;
    input.value = '';
    if (!this.importService.hasPendingExcel()) {
      return;
    }
    if (zip) {
      const err = this.importService.validateZip(zip);
      if (err) {
        swal('ไฟล์ไม่ถูกต้อง', err, 'warning');
        this.importService.setPendingExcel(null);
        return;
      }
    }
    this.runEmployeeImport(zip);
  }

  private runEmployeeImport(photosZip: File | null): void {
    this.importService.startImport(
      this.companyId,
      photosZip,
      (result) => {
        this.ngOnInit();
        this.showImportResult(result);
      },
      (msg) => swal('นำเข้าไม่สำเร็จ', msg, 'error'),
    );
  }

  private showImportResult(result: {
    total: number;
    success: number;
    failed: number;
    facesEnrolled?: number;
    created?: { faceEnrolled?: boolean; faceWarning?: string | null; row: number; email: string }[];
    errors?: { row: number; email: string; message: string }[];
  }): void {
    const faceWarnLines = (result.created || [])
      .filter((c) => c.faceWarning)
      .slice(0, 5)
      .map(
        (c) =>
          `• แถว ${c.row}${c.email ? ` (${c.email})` : ''}: บันทึกพนักงานแล้ว แต่ใบหน้าไม่สำเร็จ — ${c.faceWarning}`,
      );
    const errorLines = (result.errors || [])
      .slice(0, 8)
      .map((e) => `• แถว ${e.row}${e.email ? ` (${e.email})` : ''}: ${e.message}`);
    const more =
      (result.errors?.length || 0) > 8 ? `\n…และอีก ${result.errors!.length - 8} รายการ` : '';
    const faces = result.facesEnrolled ?? 0;
    const text = [
      `ทั้งหมด ${result.total} แถว`,
      `สำเร็จ ${result.success} รายการ`,
      `ลงทะเบียนใบหน้า ${faces} รายการ`,
      `ไม่สำเร็จ ${result.failed} รายการ`,
      faceWarnLines.length ? '\nคำเตือนรูปใบหน้า:\n' + faceWarnLines.join('\n') : '',
      errorLines.length ? '\nรายละเอียดข้อผิดพลาด:\n' + errorLines.join('\n') + more : '',
    ]
      .filter(Boolean)
      .join('\n');
    const hasFaceWarn = faceWarnLines.length > 0;
    const icon =
      result.failed === 0 && !hasFaceWarn ? 'success' : result.success > 0 ? 'warning' : 'error';
    const title =
      result.failed === 0 && !hasFaceWarn
        ? 'นำเข้าสำเร็จ'
        : result.success > 0
          ? 'นำเข้าบางส่วนสำเร็จ'
          : 'นำเข้าไม่สำเร็จ';
    swal({ title, text, icon });
  }

  save(): void {
    const clientError = validateEmployeeForm(this.selectModel);
    if (clientError) {
      swal('ไม่สามารถบันทึกได้', clientError, 'warning');
      return;
    }
    swal({
      title: 'Are you sure?',
      text: 'คุณต้องการบันทึกหรือไม่',
      icon: 'warning',
      dangerMode: false,
      buttons: ['Cancel', 'Confirm'],
    }).then((willSave) => {
      if (!willSave) return;
      if (!this.isEdit) {
        if (this.selectModel.companyRoleType === undefined || this.selectModel.companyRoleType === null) {
          this.selectModel.companyRoleType = 0;
        }
        this.employeeService.save(this.selectModel, this.companyId).subscribe({
          next: () => {
            swal('Save Success!!', 'บันทึกข้อมูลสำเร็จ', 'success');
            this.ngOnInit();
            this.detailModal?.clickClose();
          },
          error: (err) => this.showSaveError(err),
        });
      } else {
        this.employeeService.update(this.selectModel, this.companyId).subscribe({
          next: () => {
            swal('Save Success!!', 'บันทึกข้อมูลสำเร็จ', 'success');
            this.ngOnInit();
            this.detailModal?.clickClose();
          },
          error: (err) => this.showSaveError(err),
        });
      }
    });
  }

  private showSaveError(err: HttpErrorResponse): void {
    swal({
      title: saveErrorTitle(err.status),
      text: formatApiError(err),
      icon: 'error',
    });
  }

  private async resolveBlobError(err: HttpErrorResponse): Promise<string> {
    if (err.error instanceof Blob) {
      try {
        const text = await err.error.text();
        const json = JSON.parse(text);
        if (typeof json?.detail === 'string') {
          return translateApiMessage(json.detail);
        }
      } catch {
        /* fall through */
      }
    }
    return formatApiError(err);
  }

  uploadConfig(): void {
    this.uploaderProfile = new FileUploader({
      url: environment.baseUrl + '/api/upload-image',
      isHTML5: true,
      authToken: this.tokenService.getToken()!,
    });

    this.uploaderProfile.onAfterAddingFile = (fileItem: FileItem) => {
      fileItem.withCredentials = false;
      this.uploadErrorMsg = '';

      while (this.uploaderProfile!.queue.length > 1) {
        this.uploaderProfile!.queue[0].remove();
      }

      if (fileItem.file.size > 5000000) {
        this.uploadErrorMsg = 'maximum file size 5mb.';
        swal('Opp!!', 'ไม่สามารถอัพโหลดได้', 'info');
        fileItem.isCancel = true;
        return;
      }

      if (fileItem.file.type!.indexOf('image') === -1) {
        this.uploadErrorMsg = 'please upload image only.';
        swal('Opp!!', 'ไม่สามารถอัพโหลดได้', 'info');
        fileItem.isCancel = true;
        return;
      }

      fileItem.upload();
    };

    this.uploaderProfile.onCompleteItem = (
      item: FileItem,
      response: string,
      _status: number,
      _headers: ParsedResponseHeaders,
    ) => {
      if (item.isSuccess) {
        const res = JSON.parse(response);
        this.selectModel.member.picture = res.filename;
        swal(res.message, 'บันทึกสำเร็จ', 'success');
      } else {
        this.uploadErrorMsg = 'cannot upload file.';
        swal('Opp!!', 'ไม่สามารถอัพโหลดได้', 'info');
      }
    };
  }
}
