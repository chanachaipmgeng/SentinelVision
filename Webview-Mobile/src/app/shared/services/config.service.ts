import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { ConfigMenuModel } from '../models/config-menu.model';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  constructor(private http: HttpClient) { }
  getConfigMenu(companyId: string) {
    this.http.get<ConfigMenuModel>(environment.baseUrl + "/ZeemeConfig/company-config/" + companyId).subscribe(reponse => {
      window.sessionStorage.setItem('listMenu', reponse.zeemeMenu);
    }, error => {
      window.sessionStorage.setItem('listMenu', "[]");
    })
  }
  getListMenu(): { img: string, routerLink: string, show: boolean, tdesc: string, url?: string }[] {
    const listmenu = window.sessionStorage.getItem('listMenu')
    return JSON.parse(listmenu ? listmenu : "[]")
  }
}
