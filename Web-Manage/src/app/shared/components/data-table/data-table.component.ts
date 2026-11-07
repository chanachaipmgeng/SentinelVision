import { CommonModule } from '@angular/common';
import { Component, ContentChild, EventEmitter, Input, Output, TemplateRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SimplePagerComponent } from '../simple-pager/simple-pager.component';
import { SortDir } from '../../utils/data-table-query';

export interface DataTableColumn<T = unknown> {
  key: string;
  header: string;
  sortable?: boolean;
  /** Optional cell class hook. */
  cellClass?: string | ((row: T) => string);
  /** Optional value getter when not using cellTemplate. */
  value?: (row: T) => unknown;
}

export interface DataTableSortChange {
  sortBy: string | null;
  sortDir: SortDir | null;
}

/**
 * Presentational server-driven table: parent owns HTTP; this emits page/sort/search.
 * Uses DPU list chrome (pager) — not a card grid.
 */
@Component({
  selector: 'app-data-table',
  standalone: true,
  imports: [CommonModule, FormsModule, SimplePagerComponent],
  templateUrl: './data-table.component.html',
  styleUrls: ['./data-table.component.css'],
})
export class DataTableComponent<T = unknown> {
  @Input() columns: DataTableColumn<T>[] = [];
  @Input() rows: T[] = [];
  @Input() total = 0;
  @Input() loading = false;
  @Input() pageIndex = 0;
  @Input() pageSize = 10;
  @Input() sortBy: string | null = null;
  @Input() sortDir: SortDir | null = 'asc';
  @Input() search = '';
  @Input() searchPlaceholder = 'ค้นหา…';
  @Input() emptyTitle = 'ไม่พบข้อมูล';
  @Input() emptyHint = '';
  @Input() trackByKey: keyof T | string = 'id';
  /** Show the built-in search field above the table. */
  @Input() showSearch = true;

  @Output() pageIndexChange = new EventEmitter<number>();
  @Output() sortChange = new EventEmitter<DataTableSortChange>();
  @Output() searchChange = new EventEmitter<string>();
  @Output() searchSubmit = new EventEmitter<string>();

  @ContentChild('cell', { read: TemplateRef }) cellTemplate?: TemplateRef<{
    $implicit: T;
    column: DataTableColumn<T>;
    row: T;
  }>;

  onPage(index: number): void {
    this.pageIndexChange.emit(index);
  }

  onSearchInput(value: string): void {
    this.searchChange.emit(value);
  }

  onSearchKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      this.searchSubmit.emit(this.search || '');
    }
  }

  toggleSort(col: DataTableColumn<T>): void {
    if (!col.sortable) return;
    if (this.sortBy !== col.key) {
      this.sortChange.emit({ sortBy: col.key, sortDir: 'asc' });
      return;
    }
    if (this.sortDir === 'asc') {
      this.sortChange.emit({ sortBy: col.key, sortDir: 'desc' });
      return;
    }
    this.sortChange.emit({ sortBy: null, sortDir: null });
  }

  sortIndicator(col: DataTableColumn<T>): string {
    if (!col.sortable || this.sortBy !== col.key) return '';
    return this.sortDir === 'desc' ? ' ↓' : ' ↑';
  }

  cellValue(row: T, col: DataTableColumn<T>): unknown {
    if (col.value) return col.value(row);
    return (row as Record<string, unknown>)?.[col.key];
  }

  cellClass(row: T, col: DataTableColumn<T>): string {
    if (!col.cellClass) return '';
    return typeof col.cellClass === 'function' ? col.cellClass(row) : col.cellClass;
  }

  trackRow = (index: number, row: T): unknown => {
    const key = this.trackByKey as string;
    const value = row && typeof row === 'object' ? (row as Record<string, unknown>)[key] : undefined;
    return value ?? index;
  };
}
