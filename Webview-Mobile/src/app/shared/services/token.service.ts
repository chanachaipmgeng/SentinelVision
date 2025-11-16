import { Injectable } from "@angular/core";
import { UserProfileModel } from "../models/user.model";
import { Router } from "@angular/router";
import { NativeMobileService } from "./native-mobile.service";
import { CompanyService } from "./company.service";
import { AuthService } from "./auth.service";
import { CompanyModel } from "../models/company.model";
import { UserModel } from "../models/user-auth.model";

// import jwt_decode from "jwt-decode";

const TOKEN_KEY = 'auth-token';
const REFRESHTOKEN_KEY = 'auth-refreshtoken';
const USER_KEY = 'auth-user';
const USER_DATA_KEY = 'auth-user-data';
const COMPANY = 'company';

@Injectable({
  providedIn: "root",
})
export class TokenService {
  constructor(private router: Router, private mobileService: NativeMobileService, private companyService: CompanyService, private auth: AuthService) { }

  signOut(): void {
    window.localStorage.clear();
    localStorage.clear();
    this.router.navigate(["/auth/splash"]);
  }

  public saveToken(token: string): void {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.setItem(TOKEN_KEY, token);

    const user = this.getUser();
    if (user.access_token) {
      this.saveUser({ ...user, access_token: token });
    }
  }

  public getUser(): UserModel {
    const user = window.localStorage.getItem(USER_KEY);
    if (user) {
      return JSON.parse(user);
    }

    return new UserModel();
  }

  public getToken(): string | null {
    return window.localStorage.getItem(TOKEN_KEY);
  }

  public saveRefreshToken(token: string): void {
    window.localStorage.removeItem(REFRESHTOKEN_KEY);
    window.localStorage.setItem(REFRESHTOKEN_KEY, token);
  }

  public getRefreshToken(): string | null {
    return window.localStorage.getItem(REFRESHTOKEN_KEY);
  }

  public saveUser(user: any): void {
    window.localStorage.removeItem(USER_KEY);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  public saveUserData(user: string): void {
    window.localStorage.removeItem(USER_DATA_KEY);
    window.localStorage.setItem(USER_DATA_KEY, user);
  }

  public getUserData(): UserProfileModel {
    // return window.localStorage.getItem(USER_DATA_KEY);
    const user = window.localStorage.getItem(USER_DATA_KEY);
    if (user) {
      return new UserProfileModel(JSON.parse(user));
    }

    return new UserProfileModel();
  }

  public saveSelectCompany(company: CompanyModel): void {
    window.localStorage.removeItem(COMPANY);
    window.localStorage.setItem(COMPANY, JSON.stringify(new CompanyModel(company)));
  }

  public getSelectCompany(): CompanyModel {
    const company = window.localStorage.getItem(COMPANY);
    if (company) {
      return new CompanyModel(JSON.parse(company));
    }
    return new CompanyModel();
  }
}
