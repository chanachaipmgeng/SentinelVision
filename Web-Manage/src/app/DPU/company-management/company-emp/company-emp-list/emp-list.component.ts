import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { EmployeeModel } from '../../../models/employee.model';
import { EmpListViewMode } from '../company-emp.helpers';

/**
 * Employee list — table or cards mode + pager.
 * Parent owns filter/paging state; this is presentational.
 *
 * Styles live in the parent `company-emp.component.css` and are also linked
 * here so encapsulated selectors match this child template (table/cards chrome).
 */
@Component({
    selector: 'app-emp-list',
    imports: [CommonModule, RouterModule, TranslateModule],
    templateUrl: './emp-list.component.html',
    styleUrl: '../company-emp.component.css'
})
export class EmpListComponent {
  @Input() listViewMode: EmpListViewMode = 'cards';
  @Input() filterList: EmployeeModel[] | null | undefined = [];
  @Input() totalFiltered = 0;
  @Input() searchTerm = '';
  @Input() pageIndex = 0;
  @Input() pageSize = 10;
  @Input() pageStart = 0;
  @Input() pageEnd = 0;

  @Output() viewItem = new EventEmitter<EmployeeModel>();
  @Output() deleteItem = new EventEmitter<EmployeeModel>();
  @Output() enrollFace = new EventEmitter<EmployeeModel>();
  @Output() manageFace = new EventEmitter<EmployeeModel>();
  @Output() goToPage = new EventEmitter<number>();
  @Output() nextPage = new EventEmitter<void>();
  @Output() prevPage = new EventEmitter<void>();

  get safeFilterList(): EmployeeModel[] {
    return (this.filterList || []).filter((row): row is EmployeeModel => !!row);
  }

  trackEmp(item: EmployeeModel): string {
    return (
      item?.company_employeeId ||
      item?.employeeId ||
      item?.member?.memberId ||
      item?.member?.email ||
      'emp-row'
    );
  }

  pictureOf(item: EmployeeModel): string {
    const member = item?.member;
    if (member && typeof member.getPicture === 'function') {
      return member.getPicture() || './assets/images/faces/1.jpg';
    }
    return './assets/images/faces/1.jpg';
  }
}
