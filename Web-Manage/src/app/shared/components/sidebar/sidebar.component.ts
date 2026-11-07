import { Component, ViewChild, ElementRef, Renderer2, HostListener, ChangeDetectionStrategy } from '@angular/core';
import { Menu, NavService } from '../../services/nav.service';
import { Subscription, fromEvent } from 'rxjs';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { NavigationEnd, Router } from '@angular/router';
import { checkHoriMenu, switcherArrowFn } from './sidebar';
import { TokenService } from '../../services/token.service';
import { CompanyModel } from '../../../DPU/models/company.model';
import { CompanyModuleConfigService } from '../../../DPU/services/company-module-config.service';
@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})

export class SidebarComponent {
  localStorage: any;
  // Addding sticky-pin
  scrolled = false;
  screenWidth: number;
  eventTriggered: boolean = false;
  public localdata = localStorage;
  // options = { autoHide: false, scrollbarMinSize: 100 };
  @HostListener('window:scroll', [])
  onWindowScroll() {

    const navScrollElement =
      this.elementRef.nativeElement.querySelector('.nav-scroll');
    this.scrolled = window.scrollY > 10;

    const sections = document.querySelectorAll('.side-menu__item');
    const scrollPos =
      window.scrollY ||
      this.elementRef.nativeElement.ownerDocument.documentElement.scrollTop ||
      document.body.scrollTop;

    sections.forEach((ele, i) => {
      const currLink = sections[i];
      const val: any = currLink.getAttribute('value');
      const refElement: any = document.querySelector('#' + val);

      // Add a null check here before accessing properties of refElement
      if (refElement !== null) {
        const scrollTopMinus = scrollPos + 73;
        if (
          refElement.offsetTop <= scrollTopMinus &&
          refElement.offsetTop + refElement.offsetHeight > scrollTopMinus
        ) {
          if (navScrollElement) {
            this.renderer.removeClass(navScrollElement, 'active');
          }
          currLink.classList.add('active');
        } else {
          currLink.classList.remove('active');
        }
      }
    });
  }
  //////

  public windowSubscribe$!: Subscription;
  options = { autoHide: false, scrollbarMinSize: 100 };
  icon!: SafeHtml;

  public menuItems!: Menu[];
  public menuitemsSubscribe$!: Subscription;
  companyModel: CompanyModel = new CompanyModel()
  isCommonRoute: boolean = false;
  isInstallerRoute: boolean = false;
  previousUrl: string = '';
  currentUrl: string = '';
  constructor(
    private navServices: NavService,
    private sanitizer: DomSanitizer,
    public router: Router,
    public renderer: Renderer2,
    private elementRef: ElementRef,
    public tokenService: TokenService,
    private moduleConfigService: CompanyModuleConfigService
  ) {
    // this.companyModel = new CompanyModel(this.tokenService.getSelectCompany())
    this.screenWidth = window.innerWidth;
  }

  ngOnInit() {

    const bodyElement: any = document.querySelector('.main-content');

    bodyElement.onclick = () => {
      if (
        localStorage.getItem('ynex-menu-style') == 'icon-click' ||
        localStorage.getItem('ynex-menu-style') == 'menu-click' ||
        localStorage.getItem('ynex-menu-style') == 'icon-hover' ||
        localStorage.getItem('valexlayout') == 'horizontal'
      ) {
        document
          .querySelectorAll('.main-menu .slide-menu.child1')
          .forEach((ele: any) => {
            ele.style.display = 'none';
          });
      }
    };
    this.menuResizeFn();
    this.currentUrl = this.router.url
    this.isCommonRoute = this.currentUrl.includes('/admin');
    this.isInstallerRoute = this.currentUrl.includes('/company');
    this.menuitemsSubscribe$ = this.navServices.items.subscribe((items) => {
      this.changeMenu()
    });
    this.ParentActive();
    this.checkUrlChanges();

    const WindowResize = fromEvent(window, 'resize');
    // subscribing the Observable
    if (WindowResize) {
      this.windowSubscribe$ = WindowResize.subscribe(() => {
        // to check and adjst the menu on screen size change

        checkHoriMenu();
      });
    }
    switcherArrowFn();
    checkHoriMenu();
    if (document.documentElement.getAttribute('data-nav-layout') == 'horizontal' && window.innerWidth > 992) {
      this.closeNavActive()

    }
  }

  checkInitialUrl(): void {
    this.isCommonRoute = this.currentUrl.includes('/admin');
    this.isInstallerRoute = this.currentUrl.includes('/company');
    this.checkUrlChanges()
    // Log to console for verification
    console.log('Initial URL:', this.currentUrl);
    console.log('Is Common Route:', this.isCommonRoute);
    console.log('Is Installer Route:', this.isInstallerRoute);
  }

  checkUrlChanges(): void {

    this.router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.ParentActive();
      }
    });
    this.router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.previousUrl = this.currentUrl; // Save the previous URL
        this.currentUrl = event.url; // Update to the new URL

        // Check if there's a change between /installer and /admin
        if (
          (this.previousUrl.includes('/company') && this.currentUrl.includes('/admin')) ||
          (this.previousUrl.includes('/admin') && this.currentUrl.includes('/company'))
        ) {
          console.log('URL changed between /installer and /admin.');
          // Implement any logic needed when changing between /installer and /admin
        }

        // Update the boolean values
        this.isCommonRoute = this.currentUrl.includes('/admin');
        this.isInstallerRoute = this.currentUrl.includes('/company');

        // Log to console for verification
        console.log('Current URL:', this.currentUrl);
        console.log('Previous URL:', this.previousUrl);
        this.changeMenu()
      }
    });
  }

  changeMenu() {
    if (this.isInstallerRoute) {
      const raw = this.navServices.getCompanyMenu();
      const companyId = this.tokenService.getSelectCompany()?.companyId;
      if (!companyId) {
        this.menuItems = raw;
        this.ParentActive();
        return;
      }
      this.moduleConfigService.getModuleConfig(companyId).subscribe({
        next: (cfg) => {
          this.menuItems = this.navServices.filterCompanyMenuByModules(
            raw,
            cfg.enabledModules
          );
          this.ParentActive();
        },
        error: () => {
          this.menuItems = raw;
          this.ParentActive();
        },
      });
    } else {
      this.menuItems = this.navServices.getCommonMenu();
      this.ParentActive();
    }
  }


  //Active Nav State
  setNavActive(item: any) {
    this.menuItems?.filter((menuItem) => {
      if (menuItem !== item) {
        menuItem.active = false;
        this.navServices.collapseSidebar = false;
      }
      if (menuItem.children && menuItem.children.includes(item)) {
        menuItem.active = true;
        menuItem.selected = true;
      }
      if (menuItem.children) {
        menuItem.children?.filter((submenuItems) => {
          if (submenuItems.children && submenuItems.children.includes(item)) {
            menuItem.active = true;
            submenuItems.active = true;
            menuItem.selected = true;
            submenuItems.selected = true;
          }
          if (submenuItems.children) {
            submenuItems.children?.forEach((subsubmenuItems) => {
              if (
                subsubmenuItems.children &&
                subsubmenuItems.children.includes(item)
              ) {
                menuItem.active = true;
                submenuItems.active = true;
                subsubmenuItems.active = true;
                menuItem.selected = true;
                submenuItems.selected = true;
                subsubmenuItems.selected = true;
              }
            });
          }
        });
      }
    });
  }

  // Toggle menu
  toggleNavActive(item: any) {
    if (localStorage.getItem('ynex-sidemenu-styles') == 'icontext') {
      document.querySelector('html')?.setAttribute('icon-text', 'open')
    } else {
      document.querySelector('html')?.removeAttribute('icon-text')
    }
    if (localStorage.getItem('ynex-sidemenu-styles') == 'doublemenu') {
      if (item.active) return;
    }


    if (!item.active) {
      this.menuItems?.forEach((a: any) => {
        if (this.menuItems.includes(item)) {
          a.active = false;
        }
        a?.children?.forEach((b: any) => {
          if (a.children.includes(item)) {
            b.active = false;
          } else {
            b.active = false;
          }
          b?.children?.forEach((c: any) => {
            if (b.children.includes(item)) {
              c.active = false;
            }
          });
        });
      });
    }
    item.active = !item.active;
  }
  // Close Nav menu
  closeNavActive() {
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

  ParentActive() {
    if (!this.menuItems?.length) {
      return;
    }

    this.menuItems.map((element: any) => {
      if (element.children) {
        element.active = false;
        element.selected = false;
        element.children.map((ele: any) => {

          if (ele.path == this.currentUrl) {
            element.active = true;
            element.selected = true;
          }
          if (ele.children) {
            ele.active = false;
            ele.children.map((child1: any) => {
              if (child1.path == this.currentUrl) {
                element.active = true;
                element.selected = true;
                ele.active = true;
                ele.selected = true;
              }
            });
          }
        });
      }
    });
  }

  @ViewChild('iconContainer', { static: true }) iconContainer!: ElementRef;
  getSanitizedSVG(svgContent: string, menu: any): SafeHtml {
    const svg = this.renderer.createElement(
      'svg',
      'http://www.w3.org/2000/svg'
    );
    svg.innerHTML = svgContent;
    svg.classList.add('side-menu__icon');
    this.renderer.listen(svg, 'click', () => {
      this.toggleNavActive(menu);
    });
    // return svg;
    return this.sanitizer.bypassSecurityTrustHtml(svgContent);
  }
  ngOnDestroy() {
    this.menuitemsSubscribe$.unsubscribe();
    this.windowSubscribe$.unsubscribe();
    this.elementRef.nativeElement.ownerDocument.documentElement,
      'data-nav-layout',
      'vertical';
    const WindowResize = fromEvent(window, 'resize');
    // subscribing the Observable
    if (WindowResize) {
      this.windowSubscribe$ = WindowResize.subscribe(() => {
        // to check and adjst the menu on screen size change
        checkHoriMenu();
      });
    }
  }
  menuOpen() {
    const mainContent = document.querySelector('.main-content') as HTMLElement;

    if (localStorage['Ynexverticalstyles'] === 'icontext' && localStorage['iconText'] !== 'open') {
      // Assuming you have a service or method to update the theme
      this.updateTheme({ ...this.getCurrentTheme(), iconText: 'open' });

      mainContent?.addEventListener('click', (_event) => {
        // Assuming you have a service or method to update the theme
        this.updateTheme({ ...this.getCurrentTheme(), iconText: '' });
      });
    }

    if (localStorage['Ynexverticalstyles'] === 'doublemenu' && this.getCurrentTheme().dataToggled !== 'double-menu-open') {
      // Assuming you have a service or method to update the theme
      this.updateTheme({ ...this.getCurrentTheme(), dataToggled: 'double-menu-open' });
    }
  }

  // Replace this method with your actual method or service call to update the theme
  updateTheme(updatedTheme: any) {
    // Implement the logic to update the theme in your application
    // This might involve a service or a method that dispatches an action to update the theme state
    console.log('Update Theme:', updatedTheme);
  }

  // Replace this method with your actual method or service call to get the current theme
  getCurrentTheme(): any {
    // Implement the logic to get the current theme from your application state or service
    // Return the current theme object
    return {};
  }
  @HostListener('window:resize', ['$event'])
  onResize(event: any): void {
    this.menuResizeFn();

    this.screenWidth = window.innerWidth;

    // Check if the event hasn't been triggered and the screen width is less than or equal to your breakpoint
    if (!this.eventTriggered && this.screenWidth <= 992) {
      document.documentElement?.setAttribute('data-toggled', 'close')


      // Trigger your event or perform any action here
      this.eventTriggered = true; // Set the flag to true to prevent further triggering
    } else if (this.screenWidth > 992) {
      // Reset the flag when the screen width goes beyond the breakpoint
      this.eventTriggered = false;
    }
  }
  WindowPreSize: number[] = [window.innerWidth];
  menuResizeFn(): void {
    this.WindowPreSize.push(window.innerWidth);

    if (this.WindowPreSize.length > 2) {
      this.WindowPreSize.shift();
    }

    if (this.WindowPreSize.length > 1) {
      const html = document.documentElement;

      if (this.WindowPreSize[this.WindowPreSize.length - 1] < 992 && this.WindowPreSize[this.WindowPreSize.length - 2] >= 992) {
        // less than 992
        html.setAttribute('data-toggled', 'close');
      }

      if (this.WindowPreSize[this.WindowPreSize.length - 1] >= 992 && this.WindowPreSize[this.WindowPreSize.length - 2] < 992) {
        // greater than 992
        html.removeAttribute('data-toggled');
        document.querySelector('#responsive-overlay')?.classList.remove('active');
      }
    }
  }
}
