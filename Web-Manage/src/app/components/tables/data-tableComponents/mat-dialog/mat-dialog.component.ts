import { Component } from '@angular/core';
import { MaterialModuleModule } from '../../../../material-module/material-module.module';

@Component({
  selector: 'app-mat-dialog',
  standalone: true,
  imports: [MaterialModuleModule],
  templateUrl: './mat-dialog.component.html',
  styleUrl: './mat-dialog.component.scss'
})
export class MatDialogComponent {

}
