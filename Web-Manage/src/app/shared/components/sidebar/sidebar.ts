import { fromEvent } from 'rxjs';

export function switcherArrowFn() {
  const slideLeft= document.querySelector<HTMLElement>('.slide-left');
  const slideRight= document.querySelector<HTMLElement>('.slide-right');

  checkHoriMenu();

  if (slideLeft && slideRight) {
    fromEvent(slideLeft, 'click').subscribe(() => {
      const menuNav= document.querySelector<HTMLElement>('.main-menu');
      const Html= document.querySelector<HTMLElement>('html');
      const mainContainer1= document.querySelector<HTMLElement>('.main-sidebar');
      if (!menuNav || !Html || !mainContainer1) return;
      const marginLeftValue = Math.ceil(
        Number(window.getComputedStyle(menuNav).marginLeft.split('px')[0])
      );
      const marginRightValue = Math.ceil(
        Number(window.getComputedStyle(menuNav).marginRight.split('px')[0])
      );
      const mainContainer1Width = mainContainer1.offsetWidth;
      if (menuNav.scrollWidth > mainContainer1.offsetWidth) {
        if (!(Html.getAttribute('dir') === 'rtl')) {
          if (
            marginLeftValue < 0 &&
            !(Math.abs(marginLeftValue) < mainContainer1Width)
          ) {
            menuNav.style.marginRight = '0px';
            menuNav.style.marginLeft =
              Number(menuNav.style.marginLeft.split('px')[0]) +
              Math.abs(mainContainer1Width) +
              'px';
            slideRight.classList.remove('hidden');
          } else if (marginLeftValue >= 0) {
            menuNav.style.marginLeft = '0px';
            slideLeft.classList.add('hidden');
            slideRight.classList.remove('hidden');
          } else {
            menuNav.style.marginLeft = '0px';
            slideLeft.classList.add('hidden');
            slideRight.classList.remove('hidden');
          }
        } else {
          if (
            marginRightValue < 0 &&
            !(Math.abs(marginRightValue) < mainContainer1Width)
          ) {
            menuNav.style.marginLeft = '0px';
            menuNav.style.marginRight =
              Number(menuNav.style.marginRight.split('px')[0]) +
              Math.abs(mainContainer1Width) +
              'px';
            slideRight.classList.remove('hidden');
          } else if (marginRightValue >= 0) {
            menuNav.style.marginRight = '0px';
            slideLeft.classList.add('hidden');
            slideRight.classList.remove('hidden');
          } else {
            menuNav.style.marginRight = '0px';
            slideLeft.classList.add('hidden');
            slideRight.classList.remove('hidden');
          }
        }
      } else {
        menuNav.style.marginLeft = '0px';
        menuNav.style.marginRight = '0px';
      }
      const element = document.querySelector('.main-menu > .slide.open');
      const element1= document.querySelector<HTMLElement>(
        '.main-menu > .slide.open >ul'
      );
      if (element) {
        element.classList.remove('active');
      }
      if (element1) {
        element1.style.display = 'none';
      }
    });
  }

  if (slideRight && slideLeft) {
    fromEvent(slideRight, 'click').subscribe(() => {
      const menuNav= document.querySelector<HTMLElement>('.main-menu');
      const Html= document.querySelector<HTMLElement>('html');
      const mainContainer1= document.querySelector<HTMLElement>('.main-sidebar');
      if (!menuNav || !Html || !mainContainer1) return;
      const marginLeftValue = Math.ceil(
        Number(window.getComputedStyle(menuNav).marginLeft.split('px')[0])
      );
      const marginRightValue = Math.ceil(
        Number(window.getComputedStyle(menuNav).marginRight.split('px')[0])
      );
      const check = menuNav.scrollWidth - mainContainer1.offsetWidth;
      let mainContainer1Width = mainContainer1.offsetWidth;
      if (menuNav.scrollWidth > mainContainer1.offsetWidth) {
        if (!(Html.getAttribute('dir') === 'rtl')) {
          if (Math.abs(check) > Math.abs(marginLeftValue)) {
            menuNav.style.marginRight = '0px';
            if (
              !(
                Math.abs(check) >
                Math.abs(marginLeftValue) + mainContainer1Width
              )
            ) {
              mainContainer1Width = Math.abs(check) - Math.abs(marginLeftValue);
              slideRight.classList.add('hidden');
            }
            menuNav.style.marginLeft =
              Number(menuNav.style.marginLeft.split('px')[0]) -
              Math.abs(mainContainer1Width) +
              'px';
            slideLeft.classList.remove('hidden');
          }
        } else {
          if (Math.abs(check) > Math.abs(marginRightValue)) {
            menuNav.style.marginLeft = '0px';
            if (
              !(
                Math.abs(check) >
                Math.abs(marginRightValue) + mainContainer1Width
              )
            ) {
              mainContainer1Width =
                Math.abs(check) - Math.abs(marginRightValue);
              slideRight.classList.add('hidden');
            }
            menuNav.style.marginRight =
              Number(menuNav.style.marginRight.split('px')[0]) -
              Math.abs(mainContainer1Width) +
              'px';
            slideLeft.classList.remove('hidden');
          }
        }
      }
      const element = document.querySelector('.main-menu > .slide.open');
      const element1= document.querySelector<HTMLElement>(
        '.main-menu > .slide.open >ul'
      );
      if (element) {
        element.classList.remove('active');
      }
      if (element1) {
        element1.style.display = 'none';
      }
    });
  }
}
export function checkHoriMenu() {
  if (document.querySelector('.slide-left')) {
    const menuNav= document.querySelector<HTMLElement>('.main-menu');
    const mainContainer1= document.querySelector<HTMLElement>('.main-sidebar');
    const slideLeft= document.querySelector<HTMLElement>('.slide-left');
    const slideRight= document.querySelector<HTMLElement>('.slide-right');
    const Html= document.querySelector<HTMLElement>('html');
    if (!menuNav || !mainContainer1 || !slideLeft || !slideRight || !Html) return;
    const marginLeftValue = Math.ceil(
      Number(window.getComputedStyle(menuNav).marginLeft.split('px')[0])
    );
    const marginRightValue = Math.ceil(
      Number(window.getComputedStyle(menuNav).marginRight.split('px')[0])
    );
    const check = menuNav.scrollWidth - mainContainer1.offsetWidth;
    // Show/Hide the arrows
    if (menuNav.scrollWidth > mainContainer1.offsetWidth) {
      slideRight.classList.remove('hidden');
      slideLeft.classList.add('hidden');
    } else {
      slideRight.classList.add('hidden');
      slideLeft.classList.add('hidden');
      menuNav.style.marginLeft = '0px';
      menuNav.style.marginRight = '0px';
    }
    if (!(Html.getAttribute('dir') === 'rtl')) {
      // LTR check the width and adjust the menu in screen
      if (menuNav.scrollWidth > mainContainer1.offsetWidth) {
        if (Math.abs(check) < Math.abs(marginLeftValue)) {
          menuNav.style.marginLeft = -check + 'px';
          slideLeft.classList.remove('hidden');
          slideRight.classList.add('hidden');
        }
      }
      if (marginLeftValue == 0) {
        slideLeft.classList.add('hidden');
        slideRight.classList.remove('hidden');
      } else {
        slideLeft.classList.remove('hidden');
      }
    } else {
      // RTL check the width and adjust the menu in screen
      if (menuNav.scrollWidth > mainContainer1.offsetWidth) {
        if (Math.abs(check) < Math.abs(marginRightValue)) {
          menuNav.style.marginRight = -check + 'px';
          slideLeft.classList.remove('hidden');
          slideRight.classList.add('hidden');
        }
      }
      if (marginRightValue == 0) {
        slideLeft.classList.add('hidden');
      } else {
        slideLeft.classList.remove('hidden');
      }
    }
    if (marginLeftValue != 0 || marginRightValue != 0) {
      slideLeft.classList.remove('hidden');
    }
  }
}
