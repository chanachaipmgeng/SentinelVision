import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { map, tap, switchMap, filter, reduce } from "rxjs/operators";
import { PageResponseModel, ResponseModel } from '../models/base.model';
import { forkJoin, Observable } from 'rxjs';
import { DepartmentModel } from '../models/department.model';

@Injectable({
  providedIn: 'root'
})
export class DepartmentService {

  apiBaseUrl = "/departments";
  constructor(
    private http: HttpClient,
    private translateService: TranslateService
  ) { }

  getById(id: Number) {
    return this.http
      .get<DepartmentModel>(this.apiBaseUrl + "/" + id)
      .pipe(map((e) => new DepartmentModel(e, this.translateService)));
  }

  getLists(companyId: string) {
    return this.http
      .get<DepartmentModel[]>(this.apiBaseUrl + "/company/" + companyId)
      .pipe(
        map((e) => e.map((e) => new DepartmentModel(e, this.translateService)))
      );
  }

  getListByPageSize(body: { page: number; size: number }) {
    return this.http
      .get<PageResponseModel<DepartmentModel>>(this.apiBaseUrl, {
        params: body,
      })
      .pipe(
        map((page) => {
          return {
            ...page,
            content: page.content.map(
              (e) => new DepartmentModel(e, this.translateService)
            ),
          };
        })
      );
  }

  getListAllPageSize(): Observable<DepartmentModel[]> {
    return this.http
      .get<PageResponseModel<DepartmentModel>>(this.apiBaseUrl, {
        params: { page: 0, size: 1 },
      })
      .pipe(
        switchMap((checkData: any) => {
          //console.log("checkData="+checkData)
          const size = 500;

          const numOfPages = checkData.totalElements / size;
          const parallelList: Observable<PageResponseModel<DepartmentModel>>[] = [];

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
              let data: DepartmentModel[] = [];
              for (let i = 0; i < response.length; i++) {
                data = data.concat(response[i].content);
              }
              return data;
            })
          );

        })


      );
  }

  save(body: DepartmentModel) {
    return this.http.post<ResponseModel>(this.apiBaseUrl, new DepartmentModel(body));
  }

  update(body: DepartmentModel) {
    return this.http.put<ResponseModel>(this.apiBaseUrl + "/" + body.departmentId, new DepartmentModel(body));
  }

  delete(body: DepartmentModel) {
    const options = {
      headers: new HttpHeaders({
        "Content-Type": "application/json",
      }),
      body: new DepartmentModel(body),
    };
    return this.http.delete<ResponseModel>(this.apiBaseUrl + "/" + body.departmentId, options);
  }

}
