import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import {
  EmployeeImportProgress,
  EmployeeService,
} from '../../../services/employee.service';
import { formatApiError, isExcelImportFile, isZipFile } from '../company-emp.helpers';

export interface EmpImportState {
  isImporting: boolean;
  progress: EmployeeImportProgress | null;
  statusText: string;
}

@Injectable()
export class EmpImportService {
  private readonly stateSubject = new BehaviorSubject<EmpImportState>({
    isImporting: false,
    progress: null,
    statusText: 'กรุณารอสักครู่ ระบบกำลังบันทึกข้อมูลและใบหน้า',
  });

  readonly state$: Observable<EmpImportState> = this.stateSubject.asObservable();

  private pendingImportExcel: File | null = null;

  constructor(private employeeService: EmployeeService) {}

  get snapshot(): EmpImportState {
    return this.stateSubject.value;
  }

  get isImporting(): boolean {
    return this.stateSubject.value.isImporting;
  }

  hasPendingExcel(): boolean {
    return !!this.pendingImportExcel;
  }

  setPendingExcel(file: File | null): void {
    this.pendingImportExcel = file;
  }

  validateExcel(file: File): string | null {
    if (!isExcelImportFile(file.name)) {
      return 'กรุณาเลือกไฟล์ Excel (.xlsx)';
    }
    return null;
  }

  validateZip(file: File): string | null {
    if (!isZipFile(file.name)) {
      return 'กรุณาเลือกไฟล์ ZIP ของรูปใบหน้า';
    }
    return null;
  }

  startImport(
    companyId: string,
    photosZip: File | null,
    onDone: (result: {
      total: number;
      success: number;
      failed: number;
      facesEnrolled?: number;
      created?: { faceEnrolled?: boolean; faceWarning?: string | null; row: number; email: string }[];
      errors?: { row: number; email: string; message: string }[];
    }) => void,
    onError: (msg: string) => void,
  ): void {
    const file = this.pendingImportExcel;
    this.pendingImportExcel = null;
    if (!file) return;

    this.patch({
      isImporting: true,
      progress: null,
      statusText: 'กำลังอัปโหลดไฟล์...',
    });

    this.employeeService.startImportJob(companyId, file, photosZip).subscribe({
      next: (job) => {
        this.patch({
          statusText: 'รอคิวประมวลผล (worker)...',
          progress: job.progress || null,
        });
        this.pollImportJob(companyId, job.jobId, onDone, onError);
      },
      error: (err) => {
        this.patch({ isImporting: false });
        onError(formatApiError(err));
      },
    });
  }

  private pollImportJob(
    companyId: string,
    jobId: string,
    onDone: (result: {
      total: number;
      success: number;
      failed: number;
      facesEnrolled?: number;
      created?: { faceEnrolled?: boolean; faceWarning?: string | null; row: number; email: string }[];
      errors?: { row: number; email: string; message: string }[];
    }) => void,
    onError: (msg: string) => void,
  ): void {
    this.employeeService.importJob(companyId, jobId).subscribe({
      next: (job) => {
        if (job.status === 'done') {
          this.patch({ isImporting: false });
          onDone(job.result || { total: 0, success: 0, failed: 0 });
          return;
        }
        if (job.status === 'failed') {
          this.patch({ isImporting: false });
          onError(job.error || 'import failed');
          return;
        }
        this.patch({
          progress: job.progress || null,
          statusText:
            job.status === 'running'
              ? 'ระบบกำลังบันทึกข้อมูลและใบหน้า'
              : 'รอคิวประมวลผล (worker)...',
        });
        setTimeout(() => this.pollImportJob(companyId, jobId, onDone, onError), 2000);
      },
      error: (err) => {
        this.patch({ isImporting: false });
        onError(formatApiError(err));
      },
    });
  }

  private patch(partial: Partial<EmpImportState>): void {
    this.stateSubject.next({ ...this.stateSubject.value, ...partial });
  }
}
