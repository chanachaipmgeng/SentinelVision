import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { Data, Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { filter, map, mergeMap } from 'rxjs/operators';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { NativeMobileService } from 'src/app/shared/services/native-mobile.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-headermenu',
  templateUrl: './headermenu.component.html',
  styleUrls: ['./headermenu.component.scss']
})
export class HeadermenuComponent implements OnInit {
  pageInfo?: Data = Object.create(null);
  employeeModel: EmployeeModel
  isBack = false
  checkRole = false
  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute,
    private titleService: Title,
    private employeeService: EmployeeService,
    private tokenService: TokenService,
    private mobileService : NativeMobileService
  ) {


    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .pipe(map(() => this.activatedRoute))
      .pipe(
        map(route => {
          while (route.firstChild) {
            route = route.firstChild;
          }
          return route;
        })
      )
      .pipe(filter(route => route.outlet === 'primary'))
      .pipe(mergeMap(route => route.data))
      .subscribe(event => {
        if (event['isBack']) {
          this.isBack = true;
        } else {
          this.isBack = false
        }
        this.titleService.setTitle(event['title']);
        this.pageInfo = event;
      });
  }

  ngOnInit(): void {
    this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId).subscribe(result => {
      this.employeeModel = result
      console.log(this.employeeModel)
    })
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

  backnav() {
    window.history.back();
    return false;
  }

  gonave() {
    window.history.go(-2);
    return false;
  }
}
