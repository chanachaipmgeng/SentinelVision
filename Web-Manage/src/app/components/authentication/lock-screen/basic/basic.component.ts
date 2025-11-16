import { Component } from '@angular/core';
import { SharedModule } from '../../../../shared/shared.module';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-basic',
  standalone: true,
  imports: [SharedModule,RouterModule],
  templateUrl: './basic.component.html',
  styleUrls: ['./basic.component.scss']
})
export class BasicComponent {
  showPassword = false;
  toggleClass = "off-line";
  toggleVisibility() {
    this.showPassword = !this.showPassword;
    if (this.toggleClass === "off-line") {
      this.toggleClass = "line";
    } else {
      this.toggleClass = "off-line";
    }
  }
}
