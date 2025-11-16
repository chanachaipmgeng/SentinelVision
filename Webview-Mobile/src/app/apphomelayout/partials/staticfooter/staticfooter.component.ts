import { Component, OnInit } from '@angular/core';
import { NativeMobileService } from 'src/app/shared/services/native-mobile.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-staticfooter',
  templateUrl: './staticfooter.component.html',
  styleUrls: ['./staticfooter.component.scss']
})
export class StaticfooterComponent implements OnInit {
  public isVisited = false;
  constructor(private mobileService: NativeMobileService, private tokenService: TokenService) { }

  ngOnInit(): void {
  }

  checkVisited() {
    this.isVisited = !this.isVisited;
  }

  goTimestamp() {
    this.mobileService.goTimestamp(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId)
  }

  menuopen() {
    const body = document.getElementsByTagName('body')[0];
    // if(sessionStorage.getItem("pin")){
    //   body.classList.toggle('menu-open');
    // }else{
    //   this.mobileService.callShowPin()
    // }
    body.classList.toggle('menu-open');
  }
}
