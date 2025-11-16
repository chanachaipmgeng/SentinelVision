import { ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, Renderer2 } from '@angular/core';
import { Menu, NavService } from '../../services/nav.service';
import { routeAnimations } from '../../services/animations/route.animations';
import { UserService } from '../../../DPU/services/user.service';
import { TokenService } from '../../services/token.service';
@Component({
  selector: 'app-content-layout',
  templateUrl: './content-layout.component.html',
  styleUrl: './content-layout.component.scss',
  animations: [routeAnimations],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContentLayoutComponent {
  public menuItems!: Menu[];

  constructor(
    public navServices: NavService,
    private elementRef: ElementRef,
    private renderer: Renderer2,
    private ref: ChangeDetectorRef,
    private userService : UserService,
    private tokenService : TokenService
  ) {
    this.navServices.items.subscribe((menuItems: any) => {
      this.menuItems = menuItems;
    });
    setInterval(() => {
      // require view to be updated
      this.ref.markForCheck();
    }, 100);
  }
  clearToggle() {
    let html = this.elementRef.nativeElement.ownerDocument.documentElement;
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
    let html = this.elementRef.nativeElement.ownerDocument.documentElement;
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
