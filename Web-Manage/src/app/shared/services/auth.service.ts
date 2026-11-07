import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ProfileModel, UserModel } from '../user-auth.model';
@Injectable({
  providedIn: 'root',
})
export class AuthService {
  apiBaseUrl = "/auth";
  constructor(
    private http: HttpClient,
  ) {
  }

  login(username: string, password: string, totpCode?: string) {
    const body: any = {
      username: username,
      password: password,
    };
    if (totpCode && totpCode.trim()) {
      body.totpCode = totpCode.trim();
    }
    return this.http.post<UserModel>(this.apiBaseUrl + '/login', body);
  }

  refreshToken(token: string) {
    return this.http.post<any>(this.apiBaseUrl + "/refresh-token", {
      "refreshToken": token
    });
  }

  register(body: UserModel) {
    return this.http.post<any>(this.apiBaseUrl + "/register", new ProfileModel());
  }

}
