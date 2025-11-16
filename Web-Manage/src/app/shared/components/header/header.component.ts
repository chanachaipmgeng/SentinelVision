import { Component, ElementRef, Renderer2 } from '@angular/core';
import { Menu, NavService } from '../../services/nav.service';
import { TokenService } from '../../services/token.service';
import { TranslateService } from '@ngx-translate/core';
import { UserModel } from '../../user-auth.model';
import { UserProfileModel } from '../../../DPU/models/user.model';
interface Item {
  id: number;
  name: string;
  type: string;
  title: string;
  // Add other properties as needed
}
@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})

export class HeaderComponent {
  userModel : UserProfileModel = new UserProfileModel(this.tokenService.getUser().member,this.translate)
  adminRole = false
  cartItemCount: number = 5;
  notificationCount: number = 5;
  public isCollapsed = true;
  public selectedLanguage = "";
  constructor(public navServices: NavService,
    private elementRef: ElementRef, private renderer: Renderer2,
    private tokenService: TokenService,
    private translate: TranslateService) {

    this.translate.use(
      sessionStorage.getItem("Lang") != null
        ? sessionStorage.getItem("Lang")!
        : "th"
    );

    this.selectedLanguage =
      sessionStorage.getItem("Lang") != null
        ? sessionStorage.getItem("Lang")!
        : "th";
  }
  isFullScreen = false;
  fullScreenIconVisible = true;
  exitFullScreenIconVisible = false;

  changeLanguage(lang: any) {
    sessionStorage.setItem("Lang", lang);
    this.translate.use(lang);
    this.selectedLanguage = lang;
  }


  toggleFullScreen() {
    this.isFullScreen = !this.isFullScreen;
    this.fullScreenIconVisible = !this.isFullScreen;
    this.exitFullScreenIconVisible = this.isFullScreen;
  }
  themeChange(type: string, type1: string, type2: string) {
    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('class', type);
    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('style', "");
    localStorage.removeItem("ynex-background-mode-body");
    localStorage.removeItem("ynex-background-mode-dark");
    localStorage.setItem('ynex-theme-mode', type);
    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('data-header-styles', type1);
    localStorage.setItem('ynex-header-mode', type1);
    this.elementRef.nativeElement.ownerDocument.documentElement?.setAttribute('data-menu-styles', type2);
    localStorage.setItem('ynex-menu-mode', type2);
    const htmlElement = this.elementRef.nativeElement.ownerDocument.documentElement;

    if (type == 'dark') {
      const darkbtn = document.querySelector(
        '#switcher-dark-theme'
      ) as HTMLInputElement;
      darkbtn.checked = true;
      this.renderer.setAttribute(htmlElement, 'data-menu-style', 'dark');

    } else {
      const lightbtn = document.querySelector(
        '#switcher-light-theme'
      ) as HTMLInputElement;
      lightbtn.checked = true;
      this.renderer.setAttribute(htmlElement, 'data-menu-style', 'light');

    }
  }
  toggleSidebar() {
    let html = this.elementRef.nativeElement.ownerDocument.documentElement;
    // const windowObject: any = window;
    if (localStorage.getItem('data-toggled') == 'true') {
      document.querySelector('html')?.getAttribute('data-toggled') ==
        'icon-overlay-close';
    } else if (html?.getAttribute('data-vertical-style') == 'overlay') {
      document.querySelector('html')?.getAttribute('data-toggled') != null
        ? document.querySelector('html')?.removeAttribute('data-toggled')
        : document
          .querySelector('html')
          ?.setAttribute('data-toggled', 'icon-overlay-close');
    } else if (localStorage.getItem('ynex-sidemenu-styles') == 'closed') {
      html?.setAttribute(
        'data-toggled',
        html?.getAttribute('data-toggled') == 'close-menu-close'
          ? ''
          : 'close-menu-close'
      );
    } else if (localStorage.getItem('ynex-sidemenu-styles') == 'icontext') {
      html?.setAttribute(
        'data-toggled',
        html?.getAttribute('data-toggled') == 'icon-text-close'
          ? ''
          : 'icon-text-close'
      );
    } else if (localStorage.getItem('ynex-sidemenu-styles') == 'detached') {
      html?.setAttribute(
        'data-toggled',
        html?.getAttribute('data-toggled') == 'detached-close'
          ? ''
          : 'detached-close'
      );
    } else if (localStorage.getItem('ynex-sidemenu-styles') == 'doublemenu') {
      html?.setAttribute(
        'data-toggled',
        html?.getAttribute('data-toggled') == 'double-menu-close'
          ? 'double-menu-open'
          : 'double-menu-close'
      );

      // document.querySelector('.slide-menu')?.classList.add('double-menu-active');
    }

    if (window.innerWidth <= 992) {
      html?.setAttribute(
        'data-toggled',
        html?.getAttribute('data-toggled') == 'open' ? 'close' : 'open'
      );
      if (html?.getAttribute('data-toggled') == 'open') {
        document.querySelector('#responsive-overlay')?.classList.add('active');
      }
    }
  }
  // Search
  public menuItems!: Menu[];
  public items!: Menu[];
  public text!: string;
  public SearchResultEmpty: boolean = false;
  ngOnInit() {
    this.adminRole = this.tokenService.getUser().member.role == 99 ? true : false
    console.log("Admin",this.adminRole)
    this.navServices.items.subscribe((menuItems) => {
      this.items = menuItems;
    });
  }

  Search(searchText: string) {
    if (!searchText) return this.menuItems = [];
    // items array which stores the elements
    const items: Item[] = [];
    // Converting the text to lower case by using toLowerCase() and trim() used to remove the spaces from starting and ending
    searchText = searchText.toLowerCase().trim();
    this.items.filter((menuItems: Menu) => {
      // checking whether menuItems having title property, if there was no title property it will return
      if (!menuItems?.title) return false;
      //  checking wheteher menuitems type is text or string and checking the titles of menuitems
      if (menuItems.type === 'link' && menuItems.title.toLowerCase().includes(searchText)) {
        // Converting the menuitems title to lowercase and checking whether title is starting with same text of searchText
        if (menuItems.title.toLowerCase().startsWith(searchText)) { // If you want to get all the data with matching to letter entered remove this line(condition and leave items.push(menuItems))
          // If both are matching then the code is pushed to items array
          items.push(menuItems as Item);
        }
      }
      //  checking whether the menuItems having children property or not if there was no children the return
      if (!menuItems.children) return false;
      menuItems.children.filter((subItems: Menu) => {
        if (!subItems?.title) return false;
        if (subItems.type === 'link' && subItems.title.toLowerCase().includes(searchText)) {
          if (subItems.title.toLowerCase().startsWith(searchText)) {         // If you want to get all the data with matching to letter entered remove this line(condition and leave items.push(subItems))
            items.push(subItems as Item);
          }

        }
        if (!subItems.children) return false;
        subItems.children.filter((subSubItems: Menu) => {
          if (subSubItems.title?.toLowerCase().includes(searchText)) {
            if (subSubItems.title.toLowerCase().startsWith(searchText)) { // If you want to get all the data with matching to letter entered remove this line(condition and leave items.push(subSubItems))
              items.push(subSubItems as Item);

            }
          }
        });
        return true;
      });
      return this.menuItems = items;
    });
    // Used to show the No search result found box if the length of the items is 0
    if (!items.length) {
      this.SearchResultEmpty = true;
    }
    else {
      this.SearchResultEmpty = false;
    }
    return true;
  }

  //  Used to clear previous search result
  clearSearch() {
    this.text = '';
    this.menuItems = [];
    this.SearchResultEmpty = false;
    return this.text, this.menuItems;
  }
  isCartEmpty: boolean = false;
  isNotifyEmpty: boolean = false;

  removeRow(rowId: string) {
    const rowElement = document.getElementById(rowId);
    if (rowElement) {
      rowElement.remove();


    }
    this.cartItemCount--;
    this.isCartEmpty = this.cartItemCount === 0;
  }
  removeTags(rowId: string) {
    const rowElement = document.getElementById(rowId);
    if (rowElement) {
      rowElement.remove();


    }
  }
  removeNotify(rowId: string) {
    const rowElement = document.getElementById(rowId);
    if (rowElement) {
      rowElement.remove();


    }
    this.notificationCount--;
    this.isNotifyEmpty = this.notificationCount === 0;
  }
  handleCardClick(event: MouseEvent) {
    // Prevent the click event from propagating to the container
    event.stopPropagation();
  }

  logOut() {
    this.tokenService.signOut();
  }
}
