import { Component } from '@angular/core';
import { BasicAngularTableComponent } from '../data-tableComponents/basic-angular-table/basic-angular-table.component';
import { SortableDataComponent } from '../data-tableComponents/sortable-data/sortable-data.component';
import { AddRemoveDataComponent } from '../data-tableComponents/add-remove-data/add-remove-data.component';
import { SelectionDataTableComponent } from '../data-tableComponents/selection-data-table/selection-data-table.component';
import { SharedModule } from '../../../../../src/app/shared/shared.module';

@Component({
  selector: 'app-data-tables',
  standalone: true,
  imports: [BasicAngularTableComponent,SortableDataComponent,AddRemoveDataComponent,SelectionDataTableComponent,SharedModule],
  templateUrl: './data-tables.component.html',
  styleUrls: ['./data-tables.component.scss']
})
export class DataTablesComponent {

}
