import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, ChildrenOutletContexts } from '@angular/router';
import {
  trigger,
  state,
  style,
  animate,
  transition,
  // ...
} from '@angular/animations';
import { fromEvent } from 'rxjs';
import { routeAnimations } from './shared/animations/route-animations';
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  animations: [routeAnimations]
})
export class AppComponent {
  title = 'SentinelVision';
  public isSpinner = true;

  constructor(private contexts: ChildrenOutletContexts) {}

  getRouteAnimationData() {
    return this.contexts.getContext('primary')?.route?.snapshot?.data?.['animation'];
  }

  ngOnInit() {
    this.applyDpuThemeDefaults();
  }

  /** Lock product palette to teal via DOM attrs/CSS vars only (no ynex-* localStorage writes). */
  private applyDpuThemeDefaults(): void {
    const html = document.documentElement;
    const primary = '15, 118, 110';
    const primarySpace = '15 118 110';
    html.style.setProperty('--primary-rgb', primary);
    html.style.setProperty('--primary', primarySpace);
    html.setAttribute('data-menu-styles', 'dark');
    html.setAttribute('data-header-styles', 'light');
    html.setAttribute('data-theme-mode', 'light');
    localStorage.removeItem('ynexlight-primary-color');
    localStorage.removeItem('ynexlight-primary-color1');
  }
}
