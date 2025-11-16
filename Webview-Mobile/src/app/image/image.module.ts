import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LoadingSpinnerComponent } from './loading-spinner/loading-spinner.component';
import { ShowLoadingDirective } from './show-loading.directive';



@NgModule({
  declarations: [
    ShowLoadingDirective,
    LoadingSpinnerComponent
  ],
  imports: [
    CommonModule
  ],
  exports: [
    ShowLoadingDirective,
    LoadingSpinnerComponent
  ]
})
export class ImageModule { }
