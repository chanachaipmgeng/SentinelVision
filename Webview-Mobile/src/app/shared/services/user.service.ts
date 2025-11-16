import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { TokenService } from '../../shared/services/token.service';
import { UserProfileModel } from '../models/user.model';
import { map, tap, switchMap, filter, reduce } from "rxjs/operators";
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

  getById(id: Number) {
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
        switchMap((checkData: any) => {
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


  resetPass(email: string) {
    let tempBody = {
      "email": email
    }
    return this.http.put<ResponseModel>(this.apiBaseUrl + "/send-reset-password", tempBody);
  }

  resetPassUser(oldPassword: string, password: string) {
    let tempBody = {
      "oldPassword": oldPassword,
      "password": password
    }
    return this.http.put<ResponseModel>(this.apiBaseUrl + "/reset-password", tempBody);
  }



  delete(body: UserProfileModel) {
    const options = {
      headers: new HttpHeaders({
        "Content-Type": "application/json",
      }),
      body: new UserProfileModel(body),
    };
    return this.http.delete<ResponseModel>(this.apiBaseUrl + "/" + body.memberId);
  }
}
