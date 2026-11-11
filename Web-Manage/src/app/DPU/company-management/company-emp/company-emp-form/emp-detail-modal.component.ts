import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { FileUploadModule } from 'ng2-file-upload';
import { FileUploader } from 'ng2-file-upload';
import { SharedModule } from '../../../../shared/shared.module';
import { DepartmentModel } from '../../../models/department.model';
import { EmployeeModel } from '../../../models/employee.model';
import { PositionModel } from '../../../models/position.model';

@Component({
    selector: 'app-emp-detail-modal',
    imports: [CommonModule, FormsModule, SharedModule, NgSelectModule, FlatpickrModule, FileUploadModule],
    providers: [FlatpickrDefaults],
    templateUrl: './emp-detail-modal.component.html'
})
export class EmpDetailModalComponent {
  @ViewChild('closeModal') public childModal?: ElementRef;

  @Input() selectModel: EmployeeModel = new EmployeeModel();
  @Input() itemsList: EmployeeModel[] = [];
  @Input() departmentList: DepartmentModel[] = [];
  @Input() positionList: PositionModel[] = [];
  @Input() uploaderProfile: FileUploader | undefined;

  @Output() save = new EventEmitter<void>();

  compareDepartment = (a: DepartmentModel | null, b: DepartmentModel | null): boolean =>
    !!a?.departmentId && !!b?.departmentId && a.departmentId === b.departmentId;

  comparePosition = (a: PositionModel | null, b: PositionModel | null): boolean =>
    !!a?.positionId && !!b?.positionId && a.positionId === b.positionId;

  bossOptions(): EmployeeModel[] {
    return (this.itemsList || []).filter((row) => !!row?.member?.memberId);
  }

  clickClose(): void {
    this.childModal?.nativeElement?.click();
  }
}
