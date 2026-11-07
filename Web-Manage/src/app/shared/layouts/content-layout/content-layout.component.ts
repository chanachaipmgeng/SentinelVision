import { ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, OnDestroy, Renderer2 } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Subscription, filter } from 'rxjs';
import { Menu, NavService } from '../../services/nav.service';
import { routeAnimations } from '../../services/animations/route.animations';
import { UserService } from '../../../DPU/services/user.service';
import { TokenService } from '../../services/token.service';

const KIOSK_MODE_CLASS = 'dpu-kiosk-mode';

@Component({
  selector: 'app-content-layout',
  templateUrl: './content-layout.component.html',
  styleUrl: './content-layout.component.scss',
  animations: [routeAnimations],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContentLayoutComponent implements OnDestroy {
  public menuItems!: Menu[];
  private routerSub?: Subscription;

  constructor(
    public navServices: NavService,
    private elementRef: ElementRef,
    private renderer: Renderer2,
    private ref: ChangeDetectorRef,
    private userService: UserService,
    private tokenService: TokenService,
    private router: Router
  ) {
    this.navServices.items.subscribe((menuItems: any) => {
      this.menuItems = menuItems;
    });
    setInterval(() => {
      // require view to be updated
      this.ref.markForCheck();
    }, 100);

    this.syncKioskMode(this.router.url);
    this.routerSub = this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((e) => this.syncKioskMode(e.urlAfterRedirects || e.url));
  }

  ngOnDestroy(): void {
    this.routerSub?.unsubscribe();
    this.setKioskMode(false);
  }

  private syncKioskMode(url: string): void {
    const path = (url || '').split('?')[0];
    // Legacy attendance kiosk + modular `/company/scan/:stationMode` (not scan-hub).
    this.setKioskMode(
      path.includes('/company/timestamp-face') || path.includes('/company/scan/'),
    );
  }

  private setKioskMode(on: boolean): void {
    const html = this.elementRef.nativeElement.ownerDocument.documentElement as HTMLElement;
    if (!html) return;
    if (on) {
      this.renderer.addClass(html, KIOSK_MODE_CLASS);
    } else {
      this.renderer.removeClass(html, KIOSK_MODE_CLASS);
    }
  }
  clearToggle() {
    const html = this.elementRef.nativeElement.ownerDocument.documentElement;
    html?.setAttribute('data-toggled', 'close');
    document.querySelector('#responsive-overlay')?.classList.remove('active');
  }
  togglesidemenuBody() {
    if (localStorage.getItem('ynex-sidemenu-styles') == 'icontext') {
      document.documentElement.removeAttribute('icon-text');
    }
    if (document.documentElement.getAttribute('data-nav-layout') == 'horizontal' && window.innerWidth > 992) {
      this.closeMenu();
    }
    const html = this.elementRef.nativeElement.ownerDocument.documentElement;
    if (window.innerWidth <= 992) {
      html?.setAttribute(
        'data-toggled',
        html?.getAttribute('data-toggled') == 'close' ? 'close' : 'close'
      );
    }
  }
  closeMenu() {
    this.menuItems?.forEach((a: any) => {
      if (this.menuItems) {
        a.active = false;
      }
      a?.children?.forEach((b: any) => {
        if (a.children) {
          b.active = false;
        }
      });
    });
  }
}
