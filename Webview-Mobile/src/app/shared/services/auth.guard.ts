import { Injectable } from '@angular/core';
import {
  CanActivate,
  ActivatedRouteSnapshot,
  RouterStateSnapshot,
  Router
} from '@angular/router';
import { Observable } from 'rxjs';
import { TokenService } from './token.service';
import { NativeMobileService } from './native-mobile.service';

@Injectable({
  providedIn: 'root'
})

export class AuthGuard implements CanActivate {

  constructor(private router: Router, private tokenService: TokenService, private mobileService: NativeMobileService) { }

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    if (this.tokenService.getToken()) {
      if (state.url == '/') {
        // this.mobileService.mobileLogin(this.tokenService.getUser().member, this.tokenService.getUser().access_token)
        if (this.tokenService.getSelectCompany()) {
          this.router.navigate(['/company/home-company']);
        }
      }
      return true;
    }
    // not logged in so redirect to login page with the return url
    this.router.navigate(['/auth/splash']);
    return false;
  }

  canActivateChild(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    if (this.tokenService.getToken()) {
      // logged in so return true
      return true;
    }

    // not logged in so redirect to login page with the return url
    this.router.navigate(['/auth/splash']);
    return false;
  }
}
