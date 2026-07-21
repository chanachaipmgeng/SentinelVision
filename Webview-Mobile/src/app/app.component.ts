import { Component, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { Location } from '@angular/common';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  constructor(private translate: TranslateService, private location: Location) { }

  ngOnInit(): void {
    this.translate.use(
      localStorage.getItem("Lang") != null
        ? localStorage.getItem("Lang")!
        : "th"
    );
    if (localStorage.getItem('data-color')) {
      let bodyEl = document.getElementsByTagName('body')[0];
      let currentClass: any = bodyEl.getAttribute('data-color');
      bodyEl.classList.remove(currentClass)
      bodyEl.classList.add(localStorage.getItem('data-color')!)
      bodyEl.setAttribute('data-color', localStorage.getItem('data-color')!);
      localStorage.setItem("data-color", localStorage.getItem('data-color')!)
    }else {
      let bodyEl = document.getElementsByTagName('body')[0];
      bodyEl.setAttribute('data-color', 'theme-teal');
      bodyEl.classList.add('theme-teal');
      localStorage.setItem("data-color", 'theme-teal')
    }

    if (localStorage.getItem('data-bg')) {
      let bodyEl = document.getElementsByTagName('body')[0];
      let currentClass: any = bodyEl.getAttribute('data-bg');
      bodyEl.classList.remove(currentClass)
      bodyEl.classList.add(localStorage.getItem('data-bg')!)
      bodyEl.setAttribute('data-bg', localStorage.getItem('data-bg')!);
      localStorage.setItem("data-bg", localStorage.getItem('data-bg')!)
    } else {
      let bodyEl = document.getElementsByTagName('body')[0];
      bodyEl.setAttribute('data-bg', 'bg-3');
      localStorage.setItem("data-bg", 'bg-3')
    }

    if (localStorage.getItem('data-bg')) {
      let bodyEl = document.getElementsByTagName('body')[0];
      let currentClass: any = bodyEl.getAttribute('data-bg');
      bodyEl.classList.remove(currentClass)
      bodyEl.classList.add(localStorage.getItem('data-bg')!)
      bodyEl.setAttribute('data-bg', localStorage.getItem('data-bg')!);
      localStorage.setItem("data-bg", localStorage.getItem('data-bg')!)
    }

    if (localStorage.getItem('isdarkmode') == "true") {
      localStorage.setItem('isdarkmode', 'false');
    }

    window.addEventListener('message', (event) => {
      if (event.data === 'backButtonPressed') {
        this.onIframeBackButtonPressed();
      }
    });
  }

  onIframeBackButtonPressed() {
    this.location.back()
  }
}


