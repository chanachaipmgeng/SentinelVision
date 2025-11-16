import { Directive, ElementRef, HostListener, Renderer2 } from '@angular/core';

@Directive({
  selector: '[appAppshowcode]',
  // standalone: true
})
export class AppshowcodeDirective {
  private isCodeVisible = false; // Track the state of code visibility
  // isCodeVisible!: boolean;



  constructor(private el: ElementRef, private renderer: Renderer2) {}
  
  @HostListener('click') onClick() {
    const boxElement = this.el.nativeElement.closest('.box');
    // console.log('boxElement:', boxElement);
    if (boxElement) {
      const boxBody = boxElement.querySelector('.box-body');
      const boxFooter = boxElement.querySelector('.box-footer');
      // console.log('boxBody:', boxBody);
      // console.log('boxFooter:', boxFooter);
      if (boxBody && boxFooter) {
          boxBody.classList.toggle('hidden');
          boxFooter.classList.toggle('hidden');
          const codeContent = boxBody?.innerHTML.replace(/<\/\w+>/g, '$&\n\n').replace(/^\s+/gim, '');
          boxFooter.innerText = codeContent;
        this.isCodeVisible = !this.isCodeVisible; // Toggle the state
      }
    }
}

  }