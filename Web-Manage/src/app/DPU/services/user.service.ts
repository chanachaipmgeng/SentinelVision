import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { UserProfileModel } from '../models/user.model';
import { map, switchMap } from "rxjs/operators";
import { PageResponseModel, ResponseModel } from '../models/base.model';
import { forkJoin, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  apiBaseUrl = "/members";
  constructor(
    private http: HttpClient,
    private translateService: TranslateService
  ) { }

  getById(id: number) {
    return this.http
      .get<UserProfileModel>(this.apiBaseUrl + "/" + id)
      .pipe(map((e) => new UserProfileModel(e, this.translateService)));
  }

  getByUsername(username: string) {
    return this.http
      .get<UserProfileModel>(this.apiBaseUrl + "/username/" + username)
  }


  getLists() {
    return this.http
      .get<UserProfileModel[]>(this.apiBaseUrl)
      .pipe(
        map((e) => e.map((e) => new UserProfileModel(e, this.translateService)))
      );
  }

  getListByPageSize(body: { page: number; size: number }) {
    return this.http
      .get<PageResponseModel<UserProfileModel>>(this.apiBaseUrl, {
        params: body,
      })
      .pipe(
        map((page) => {
          return {
            ...page,
            content: page.content.map(
              (e) => new UserProfileModel(e, this.translateService)
            ),
          };
        })
      );
  }

  getListAllPageSize(): Observable<UserProfileModel[]> {
    return this.http
      .get<PageResponseModel<UserProfileModel>>(this.apiBaseUrl, {
        params: { page: 0, size: 1 },
      })
      .pipe(
        switchMap((checkData: PageResponseModel<UserProfileModel>) => {
          //console.log("checkData="+checkData)
          const size = 500;

          const numOfPages = checkData.totalElements / size;
          const parallelList: Observable<PageResponseModel<UserProfileModel>>[] = [];

          for (let page = 0; page < numOfPages; page++) {
            parallelList.push(
              this.getListByPageSize({
                page,
                size,
              })
            );
          }
          return forkJoin(parallelList).pipe(
            map((response) => {
              let data: UserProfileModel[] = [];
              for (let i = 0; i < response.length; i++) {
                data = data.concat(response[i].content);
              }
              return data;
            })
          );

        })


      );
  }

  save(body: UserProfileModel) {
    return this.http.post<ResponseModel>(this.apiBaseUrl, new UserProfileModel(body));
  }

  update(body: UserProfileModel) {
    return this.http.put<ResponseModel>(this.apiBaseUrl + "/" + body.memberId, new UserProfileModel(body));
  }


  /** @deprecated Prefer AuthService.sendResetPassword — kept for callers mid-migration. */
  resetPass(email: string) {
    return this.http.post<ResponseModel>("/auth/send-reset-password", { email });
  }

  /** Complete a password-reset token (or change via /auth/change-password when signed in). */
  resetPassUser(tokenOrOld: string, password: string) {
    // Token-based reset (E4). Callers that still pass oldPassword should use /auth/change-password.
    if ((tokenOrOld || '').length > 40) {
      return this.http.post<ResponseModel>("/auth/reset-password", {
        token: tokenOrOld,
        newPassword: password,
      });
    }
    return this.http.post<ResponseModel>("/auth/change-password", {
      currentPassword: tokenOrOld,
      newPassword: password,
    });
  }



  delete(body: UserProfileModel) {
    const options = {
      headers: new HttpHeaders({
        "Content-Type": "application/json",
      }),
      body: new UserProfileModel(body),
    };
    return this.http.delete<ResponseModel>(this.apiBaseUrl + "/" + body.memberId, options);
  }

  /** System-admin console face-login consent (no company scope). */
  grantBiometricConsent(memberId: string, locale: string = 'th') {
    return this.http.post<Record<string, unknown>>(
      `${this.apiBaseUrl}/${memberId}/biometric-consent`,
      { locale },
    );
  }

  revokeBiometricConsent(memberId: string) {
    return this.http.delete<Record<string, unknown>>(
      `${this.apiBaseUrl}/${memberId}/biometric-consent`,
    );
  }
}
