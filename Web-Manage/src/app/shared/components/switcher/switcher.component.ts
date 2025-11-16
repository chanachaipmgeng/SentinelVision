import { Component, ElementRef, Renderer2 } from '@angular/core';
import { NavService } from '../../services/nav.service';
import * as switcher from './switcher';
@Component({
  selector: 'app-switcher',
  templateUrl: './switcher.component.html',
  styleUrls: ['./switcher.component.scss']
})
export class SwitcherComponent {
  constructor(
    private renderer: Renderer2,
    private elementRef: ElementRef,
    private navServices: NavService
  ) {

  }
  body = document.querySelector('body');
  public localdata = localStorage;

  themeChange(type: string, type1: string,type2:string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'class', type);
    localStorage.setItem('ynex-theme-mode', type);

    this.renderer.setAttribute(htmlElement, 'data-header-styles', type1);
    localStorage.setItem('ynex-header-mode', type1);
    this.renderer.setAttribute(htmlElement, 'data-menu-styles', type2);
    localStorage.setItem('ynex-menu-mode', type2);
    if (localStorage.getItem('ynex-header-mode') == 'light') {
      this.elementRef.nativeElement.ownerDocument.documentElement?.removeAttribute('style');
      // localStorage.removeItem('ynexlight-background-light');
      // this.body = document.querySelector('body');
      // this.body?.classList.remove('dark');
    }
    if (localStorage.getItem('ynex-theme-mode') == 'light') {
      this.elementRef.nativeElement.ownerDocument.documentElement?.removeAttribute('style');
      localStorage.removeItem('ynexlight-background-light');
      localStorage.removeItem('ynexlight-background-body');
      localStorage.removeItem('ynexlight-background-dark');
      localStorage.removeItem('ynex-background-mode-dark');
      localStorage.removeItem('ynex-background-mode-body');
      localStorage.removeItem('ynex-background-mode-light');
      localStorage.removeItem('ynex-background-mode-input');



      // this.body = document.querySelector('body');
      // this.body?.classList.remove('dark');
    }
  }
  
  DirectionsChange(type: string) {
    // this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('dir', type);
    // localStorage.setItem('ynex-dir', type);
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'dir', type);
    localStorage.setItem('ynex-dir', type);
  }
  NavigationChange(type: string) {
    const htmlElement = this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'data-nav-layout', type);
    if(type == 'vertical'){
      this.renderer.setAttribute(htmlElement, 'data-vertical-style', 'overlay');
      this.renderer.removeAttribute(htmlElement, 'data-nav-style');

    }
    if(type == 'horizontal'){
      this.renderer.setAttribute(htmlElement, 'data-nav-style', 'menu-click');
      this.renderer.removeAttribute(htmlElement, 'data-vertical-style');
      localStorage.setItem('ynex-menu-style','menu-click');
      setTimeout(() => {
        const mainContentElement = document.querySelector(".main-content") as HTMLElement | null;
        if (mainContentElement) {
            mainContentElement.click();
        }
    }, 100);
   
  

    }else{
      this.renderer.setAttribute(htmlElement, 'data-menu-styles', 'dark');
      localStorage.removeItem('ynex-menu-style');

    }
    localStorage.setItem('ynex-nav-mode', type);
  }
  Menustyles(type: string, type1: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    localStorage.setItem('ynex-menu-style', type);
    this.renderer.setAttribute(htmlElement, 'data-toggled', type1);
    localStorage.setItem('ynex-menu-style', type1);
    this.renderer.setAttribute(htmlElement, 'data-toggled', type1);
    localStorage.setItem('ynex-menu-style', type1);
  }
  menuItems!: any;
  Menus(type: string, type1: string) {
    this.navServices.items.subscribe((items) => {
      this.menuItems = items;
    });
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'data-nav-style', type1);
    localStorage.setItem('ynex-menu-style', type1);
    localStorage.setItem('ynex-menu-style-toggled', type);
    this.renderer.setAttribute(htmlElement, 'data-toggled', type);
    this.renderer.removeAttribute(htmlElement, 'data-vertical-style');
    localStorage.removeItem('ynex-sidemenu-styles');
    localStorage.removeItem('ynex-sidemenu-styles-toggled');

  }
  
  SideMenus(type: string, type1: string) {
    this.navServices.items.subscribe((items) => {
      this.menuItems = items;
    });
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'data-vertical-style', type1);
  
     
     if(localStorage.getItem('ynex-sidemenu-styles') == 'closed'){
       this.renderer.setAttribute(htmlElement, 'data-toggled', type);
     }
     else if (localStorage.getItem('ynex-sidemenu-styles') == 'closed'){
     this.renderer.removeAttribute(htmlElement, 'data-toggled');
     }
     
    localStorage.setItem('ynex-sidemenu-styles', type1);
    localStorage.setItem('ynex-sidemenu-styles-toggled', type);
    this.renderer.setAttribute(htmlElement, 'data-toggled', type);
    this.renderer.removeAttribute(htmlElement, 'data-nav-style');
    if (type1 === 'icon-text') {
      this.renderer.setAttribute(htmlElement, 'icon-text', 'open');
    } else {
      // If not 'icon-text', remove the icon-text attribute
      this.renderer.removeAttribute(htmlElement, 'icon-text');
    }

  }
  PageChange(type: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'data-page-style', type);
    localStorage.setItem('ynex-page-mode', type);
  }

  WidthChange(type: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'data-width', type);
    localStorage.setItem('ynex-width-mode', type);
  }
  MenuChange(type: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'data-menu-position', type);
    localStorage.setItem('ynex-menu-position', type);
  }
  menuTheme(type: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'data-menu-styles', type);
    localStorage.setItem('ynex-menu-mode', type);
  }
  HeaderChange(type: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'data-header-position', type);
    localStorage.setItem('ynex-header-position', type);
  }
  Loader(type: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'loader', type);
    localStorage.setItem('ynex-loader', type);
  }
  headerTheme(type: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'data-header-styles', type);
    localStorage.setItem('ynex-header-mode', type);
  }
  closeMenu(type1: any) {
    if (type1 == 'icon-hover' || type1 == 'menu-hover') {
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

  primary(type: string) {
    this.elementRef.nativeElement.ownerDocument.documentElement?.style.setProperty('--primary', type);
    this.elementRef.nativeElement.ownerDocument.documentElement?.style.setProperty('--primary-rgb', type);
    localStorage.setItem('ynex-primary-mode', type);
    // localStorage.removeItem('ynexlight-primary-color');
  }
  background(lightBg:string,inputBorder:string,bodyBg: string, darkBg: string, type: string, type1: string) {
    this.elementRef.nativeElement.ownerDocument.documentElement?.style.setProperty('--light', lightBg);
    this.elementRef.nativeElement.ownerDocument.documentElement?.style.setProperty('--input-border', inputBorder);
    this.elementRef.nativeElement.ownerDocument.documentElement?.style.setProperty('--body-bg', bodyBg);
    this.elementRef.nativeElement.ownerDocument.documentElement?.style.setProperty('--dark-bg', darkBg);
    localStorage.setItem('ynex-background-mode-body', bodyBg);
    localStorage.setItem('ynex-background-mode-dark', darkBg);
    localStorage.setItem('ynex-background-mode-light', lightBg);
    localStorage.setItem('ynex-background-mode-input', inputBorder);

    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('class', type);
    localStorage.setItem('ynex-theme-mode', type);

    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('data-header-styles', type1);
    localStorage.setItem('ynex-header-mode', type1);
    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('data-menu-styles', type1);
    localStorage.setItem('ynex-menu-mode', type1);

    localStorage.removeItem("ynexlight-background-dark");
    localStorage.removeItem("ynexlight-background-body");
    localStorage.removeItem("ynexlight-background-light")

  }

  //primary theme change
  public dynamicLightPrimary(data: any): void {
    this.color1 = data.color;

    const dynamicPrimaryLight = document.querySelectorAll(
      'button.pcr-button'
    );

    switcher.dynamicLightPrimaryColor(dynamicPrimaryLight, this.color1);

    localStorage.setItem('ynexlight-primary-color', switcher.hexToRgba(this.color1) || '');
    localStorage.setItem('ynexlight-primary-color1', switcher.hexToRgba(this.color1) || '');
    localStorage.setItem('ynexlight-mode', 'true');
    this.body?.classList.remove('transparent-mode');

    // Adding
    this.body?.classList.add('light-mode');

    // Removing
    this.body?.classList.remove('dark');
    this.body?.classList.remove('bg-img1');

    // removing data from session storage

    // switcher.checkOptions();
    // localStorage.removeItem('ynex-primary-mode');
  }

  //background theme change
  public color4 = '#6c5ffc';
  public dynamicTranparentBgPrimary(data: any,): void {
    const darkChecked = document.getElementById(
      'switcher-dark-theme'
    ) as HTMLInputElement;
    if (darkChecked) {
      darkChecked.checked = true;
    }
    // switcher.checkOptions();
    this.color4 = data.color;
    const dynamicPrimaryBgTrasnsparent = document.querySelectorAll(
      'button.pcr-button'
    );

    switcher.dynamicBgTrasnsparentPrimaryColor(
      dynamicPrimaryBgTrasnsparent,
      this.color4
    );
    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('class','dark');

    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('data-header-styles', 'dark');
    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('data-menu-styles', 'dark');
    // Adding
    localStorage.setItem('ynexlight-background-body', switcher.hexToRgba(this.color4) || '');
    localStorage.setItem('ynexlight-background-dark', switcher.hexToRgba2(this.color4) || '');
    localStorage.setItem('ynexlight-background-light', switcher.hexToRgba3(this.color4) || '');
    localStorage.setItem('ynex-header-mode','dark');
    localStorage.setItem('ynex-theme-mode','dark');

    localStorage.removeItem('ynexDark');
    localStorage.removeItem('ynexLight');

    this.elementRef.nativeElement.ownerDocument.documentElement?.classList.add('dark');
    document
      .querySelector('.app-header')
      ?.classList.add(
        'hor-header',
        'fixed-header',
        'visible-title',
        'stickyClass'
      );

  }

  color1 = '#1457e6';
  color = '#1ae715';

  ImageTheme(type: string) {
    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('bg-img', type);
    localStorage.setItem('ynex-image', type);
  }
  reset() {
    localStorage.clear();
    const html: any = this.elementRef.nativeElement.ownerDocument.documentElement;
    const body: any = document.querySelector('body');
    html.style = '';
    html.setAttribute('class', 'light');
    html.setAttribute('data-vertical-style', 'overlay');
    html.setAttribute('dir', 'ltr');
    html.setAttribute('data-nav-layout', 'vertical');
    html.removeAttribute('data-page-style', 'regular');
    html.removeAttribute('data-width', 'full-width');
    html.removeAttribute('data-menu-position', 'fixed');
    html.removeAttribute('data-header-position', 'fixed');
    html.setAttribute('data-header-styles', 'light');
    html.setAttribute('data-menu-styles', 'dark');
    html.removeAttribute('bg-img', 'dark');
    html.removeAttribute('data-toggled', 'overlay');
    body.removeAttribute('class');
    html.removeAttribute("data-nav-style")

    const menuclickclosed = document.getElementById(
      'switcher-menu-click'
    ) as HTMLInputElement;
    menuclickclosed.checked = false;
    const menuhoverclosed = document.getElementById(
      'switcher-menu-hover'
    ) as HTMLInputElement;
    menuhoverclosed.checked = false;
    const iconclickclosed = document.getElementById(
      'switcher-icon-click'
    ) as HTMLInputElement;
    iconclickclosed.checked = false;
    const iconhoverclosed = document.getElementById(
      'switcher-icon-hover'
    ) as HTMLInputElement;
    iconhoverclosed.checked = false;
    const defaultclickchecked = document.getElementById(
      'switcher-default-menu'
    ) as HTMLInputElement;
    if (defaultclickchecked) {
      defaultclickchecked.checked = true;
    }
    const Light = document.getElementById(
      'switcher-light-theme'
    ) as HTMLInputElement;
    if (Light) {
      Light.checked = true;
    }
    const menuscrollable = document.getElementById(
      'switcher-menu-fixed'
    ) as HTMLInputElement;
    if (menuscrollable) {
      menuscrollable.checked = true;
    }
    const headerscrollable = document.getElementById(
      'switcher-header-fixed'
    ) as HTMLInputElement;
    if (headerscrollable) {
      headerscrollable.checked = true;
    }
    // switcher.checkOptions();
  }
  ngOnInit(): void {
    switcher.localStorageBackUp();
    this.closeMenu(localStorage.getItem('ynex-menu-style'));
  }
}
