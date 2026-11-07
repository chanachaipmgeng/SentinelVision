import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterModule } from '@angular/router';
import { EmployeeModel } from '../../../models/employee.model';
import { EmpListViewMode } from '../company-emp.helpers';

/**
 * Employee list — table or cards mode + pager.
 * Parent owns filter/paging state; this is presentational.
 */
@Component({
  selector: 'app-emp-list',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './emp-list.component.html',
})
export class EmpListComponent {
  @Input() listViewMode: EmpListViewMode = 'cards';
  @Input() filterList: EmployeeModel[] = [];
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
}
