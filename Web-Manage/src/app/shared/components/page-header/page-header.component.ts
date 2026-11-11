import { Component, Input } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';

@Component({
    selector: 'app-page-header',
    imports: [TranslateModule],
    templateUrl: './page-header.component.html',
    styleUrls: ['./page-header.component.scss'],
})
export class PageHeaderComponent {
  @Input() title!: string;
  @Input() title1!:string;
  @Input() activeTitle!:string;
}
