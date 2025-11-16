import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { TokenService } from '../../shared/services/token.service';
import { UserRole, UserRoleModel } from '../models/user-role-model';
import { map, tap, switchMap, filter, reduce } from "rxjs/operators";
import { PageResponseModel, ResponseModel } from '../models/base.model';
import { forkJoin, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class UserRoleService {
  apiBaseUrl = "/user-role";
  constructor(
    private http: HttpClient,
    private translateService: TranslateService
  ) { }

  getById(id: Number) {
    return this.http
      .get<UserRoleModel>(this.apiBaseUrl + "/" + id)
      .pipe(map((e) => new UserRole(e, this.translateService)));
  }

  getLists() {
    return this.http
      .get<UserRoleModel[]>(this.apiBaseUrl + "/lists")
      .pipe(
        map((e) => e.map((e) => new UserRole(e, this.translateService)))
      );
  }

  getListByPageSize(body: { page: number; size: number }) {
    return this.http
      .get<PageResponseModel<UserRoleModel>>(this.apiBaseUrl, {
        params: body,
      })
      .pipe(
        map((page) => {
          return {
            ...page,
            content: page.content.map(
              (e) => new UserRole(e, this.translateService)
            ),
          };
        })
      );
  }

  getListAllPageSize(): Observable<UserRoleModel[]> {
    return this.http
      .get<PageResponseModel<UserRoleModel>>(this.apiBaseUrl, {
        params: { page: 0, size: 1 },
      })
      .pipe(
        switchMap((checkData: any) => {
          //console.log("checkData="+checkData)
          const size = 500;

          const numOfPages = checkData.totalElements / size;
          const parallelList: Observable<PageResponseModel<UserRoleModel>>[] = [];

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
              let data: UserRoleModel[] = [];
              for (let i = 0; i < response.length; i++) {
                data = data.concat(response[i].content);
              }
              return data;
            })
          );

        })


      );
  }

  save(body: UserRoleModel) {
    return this.http.post<ResponseModel>(this.apiBaseUrl, new UserRole(body));
  }

  delete(body: UserRoleModel) {
    const options = {
      headers: new HttpHeaders({
        "Content-Type": "application/json",
      }),
      body: new UserRole(body),
    };
    return this.http.delete<ResponseModel>(this.apiBaseUrl, options);
  }
}
