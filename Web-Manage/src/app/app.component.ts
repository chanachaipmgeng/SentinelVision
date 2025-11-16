import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import {
  trigger,
  state,
  style,
  animate,
  transition,
  // ...
} from '@angular/animations';
import { fromEvent } from 'rxjs';
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  animations:[]
})
export class AppComponent {
  title = 'ynex';
  public isSpinner = true;

  ngOnInit() {
    // this.isSpinner = false
    // fromEvent(window, 'load').subscribe(() => {document.querySelector('#loader')?.classList.remove('');});
  }
}
