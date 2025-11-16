import { Component, ElementRef, Inject, Renderer2 } from '@angular/core';
import { NgxColorsModule } from 'ngx-colors';
import * as switcher from '../switcher/switcher';
import { DOCUMENT } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
@Component({
  selector: 'app-landing-switcher',
  templateUrl: './landing-switcher.component.html',
  styleUrl: './landing-switcher.component.scss'
})
export class LandingSwitcherComponent {
  body: HTMLBodyElement | null;
  constructor( @Inject(DOCUMENT) private document: Document,private elementRef: ElementRef,
  private renderer: Renderer2,  private el: ElementRef,){
    this.body = document.querySelector('body');
    const htmlElement =
    this.elementRef.nativeElement.ownerDocument.documentElement;
  const bodyElement = document.body;
  }
  CheckOpe = () => {
    if (localStorage.getItem('ynex-dir') == 'rtl') {
      this.RtlChecked = true;
    }
    if (localStorage.getItem('ynex-dir') == 'rtl') {
      this.darkchecked = true;
    }
  };
  // public localdata = localStorage;

  ngOnInit(): void {
 
    switcher.localStorageBackUp();
    this.CheckOpe();


  }
  themeChange(type: string, type1: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
  
    this.renderer.setAttribute(htmlElement, 'class', type);
    localStorage.setItem('ynex-theme-mode', type);
  
    this.renderer.setAttribute(htmlElement, 'data-header-styles', type1);
    localStorage.setItem('ynex-header-mode', type1);
  
    if (localStorage.getItem('ynex-header-mode') === type1) {
      this.renderer.removeAttribute(htmlElement, 'style');
    }
  }
  primary(type: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    htmlElement.style.setProperty('--primary', type);
    htmlElement.style.setProperty('--primary-rgb', type);
    localStorage.setItem('ynex-primary-mode', type);
  }
  
  color1 = '#1457e6';
    //primary theme change
    public dynamicLightPrimary(data: any): void {
      this.color1 = data.color;
  
      const dynamicPrimaryLight = document.querySelectorAll(
        'input.color-primary-light'
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
      localStorage.removeItem('ynex-primary-mode');
    }
  DirectionsChange(type: string) {
    const htmlElement =
      this.elementRef.nativeElement.ownerDocument.documentElement;
    this.renderer.setAttribute(htmlElement, 'dir', type);
    localStorage.setItem('ynex-dir', type);
  }
  public localDark = localStorage;
  public localdata = localStorage;
  public darkchecked: any;
  public RtlChecked: any;
  reset() {
    localStorage.clear();
    const htmlElement = this.elementRef.nativeElement.ownerDocument.documentElement;
    htmlElement.removeAttribute('style');
    htmlElement.setAttribute('class', 'light');
    htmlElement.setAttribute('dir', 'ltr');
    htmlElement.setAttribute('data-nav-layout', 'horizontal');
    htmlElement.setAttribute('data-page-style', 'regular');
    htmlElement.setAttribute('data-header-styles', 'light');
    htmlElement.setAttribute('data-menu-styles', 'dark');
    htmlElement.setAttribute('bg-img', 'dark');
    htmlElement.removeAttribute('data-toggled');
    htmlElement.removeAttribute('style');
    // switcher.checkOptions();
     this.toggleExpand();
  }
  expande = false;
expande1 = false;
expande2 = false;
toggleExpand(): void {
  this.expande = !this.expande;   
 if (localStorage.getItem('data-menu-styles') == 'light') {
   document
     .querySelector('html')
     ?.setAttribute('data-menu-styles', 'light');
 } else if (localStorage.getItem('data-menu-styles') == 'dark') {
   document
     .querySelector('html')
     ?.setAttribute('data-menu-styles', 'dark');
 }
}
}

