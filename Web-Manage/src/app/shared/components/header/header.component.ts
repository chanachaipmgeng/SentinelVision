import { Component, ElementRef, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Menu, NavService } from '../../services/nav.service';
import { TokenService } from '../../services/token.service';
import { TranslateService } from '@ngx-translate/core';
import { UserProfileModel } from '../../../DPU/models/user.model';

interface Item {
  id: number;
  name: string;
  type: string;
  title: string;
}

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})

export class HeaderComponent implements OnInit {
  userModel : UserProfileModel = new UserProfileModel(this.tokenService.getUser().member,this.translate)
  adminRole = false
  cartItemCount: number = 0;
  notificationCount: number = 0;
  public isCollapsed = true;
  public selectedLanguage = "";
  constructor(public navServices: NavService,
    private elementRef: ElementRef,
    private tokenService: TokenService,
    private translate: TranslateService,
    private http: HttpClient) {

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

  private loadPendingBadge(): void {
    if (!this.tokenService.getToken()) {
      return;
    }
    this.http.get<{ pending: number }>('/notifications/pending-count').subscribe({
      next: (res) => {
        this.notificationCount = res?.pending || 0;
        this.cartItemCount = this.notificationCount;
      },
      error: () => {
        this.notificationCount = 0;
        this.cartItemCount = 0;
      },
    });
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
  toggleSidebar() {
    const html = this.elementRef.nativeElement.ownerDocument.documentElement as HTMLElement;
    if (!html) return;

    // Mobile: slide-in drawer
    if (window.innerWidth <= 992) {
      const next = html.getAttribute('data-toggled') === 'open' ? 'close' : 'open';
      html.setAttribute('data-toggled', next);
      const overlay = document.querySelector('#responsive-overlay');
      if (next === 'open') {
        overlay?.classList.add('active');
      } else {
        overlay?.classList.remove('active');
      }
      return;
    }

    // Desktop: fully hide / show the sidebar (not icon-rail collapse)
    const hiddenStates = new Set([
      'dpu-sidebar-hidden',
      'icon-overlay-close',
      'close-menu-close',
    ]);
    const current = html.getAttribute('data-toggled') || '';
    if (hiddenStates.has(current)) {
      html.removeAttribute('data-toggled');
    } else {
      html.setAttribute('data-toggled', 'dpu-sidebar-hidden');
    }
    html.removeAttribute('icon-overlay');
  }
  // Search
  public menuItems!: Menu[];
  public items!: Menu[];
  public text!: string;
  public SearchResultEmpty: boolean = false;
  ngOnInit() {
    this.adminRole = this.tokenService.getUser().member.role == 99 ? true : false
    this.loadPendingBadge();
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
