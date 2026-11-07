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
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule, NgSelectModule, FlatpickrModule, FileUploadModule],
  providers: [FlatpickrDefaults],
  templateUrl: './emp-detail-modal.component.html',
})
export class EmpDetailModalComponent {
  @ViewChild('closeModal') public childModal?: ElementRef;

  @Input() selectModel: EmployeeModel = new EmployeeModel();
  @Input() itemsList: EmployeeModel[] = [];
  @Input() departmentList: DepartmentModel[] = [];
  @Input() positionList: PositionModel[] = [];
  @Input() uploaderProfile: FileUploader | undefined;

  @Output() save = new EventEmitter<void>();

  clickClose(): void {
    this.childModal?.nativeElement?.click();
  }
}
