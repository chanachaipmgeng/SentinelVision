import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { map, tap, switchMap, filter, reduce } from "rxjs/operators";
import { PageResponseModel, ResponseModel } from '../models/base.model';
import { forkJoin, Observable } from 'rxjs';
import { CompanyLocationModel } from '../models/company-location.model';

@Injectable({
  providedIn: 'root'
})
export class CompanyLocationService {
  apiBaseUrl = "/company-locations/company";
  constructor(
    private http: HttpClient,
    private translateService: TranslateService
  ) { }

  getById(id: Number) {
    return this.http
      .get<CompanyLocationModel>(this.apiBaseUrl + "/" + id)
      .pipe(map((e) => new CompanyLocationModel(e, this.translateService)));
  }

  getLists(companyId: string) {
    return this.http
      .get<CompanyLocationModel[]>(this.apiBaseUrl + "/" + companyId)
      .pipe(
        map((e) => e.map((e) => new CompanyLocationModel(e, this.translateService)))
      );
  }

  getListByPageSize(body: { page: number; size: number }) {
    return this.http
      .get<PageResponseModel<CompanyLocationModel>>(this.apiBaseUrl, {
        params: body,
      })
      .pipe(
        map((page) => {
          return {
            ...page,
            content: page.content.map(
              (e) => new CompanyLocationModel(e, this.translateService)
            ),
          };
        })
      );
  }

  getListAllPageSize(): Observable<CompanyLocationModel[]> {
    return this.http
      .get<PageResponseModel<CompanyLocationModel>>(this.apiBaseUrl, {
        params: { page: 0, size: 1 },
      })
      .pipe(
        switchMap((checkData: any) => {
          //console.log("checkData="+checkData)
          const size = 500;

          const numOfPages = checkData.totalElements / size;
          const parallelList: Observable<PageResponseModel<CompanyLocationModel>>[] = [];

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
              let data: CompanyLocationModel[] = [];
              for (let i = 0; i < response.length; i++) {
                data = data.concat(response[i].content);
              }
              return data;
            })
          );

        })


      );
  }

  save(companyId: string, body: CompanyLocationModel) {
    return this.http.post<ResponseModel>(this.apiBaseUrl + "/" + companyId, new CompanyLocationModel(body));
  }

  update(companyId: string, body: CompanyLocationModel) {
    return this.http.put<ResponseModel>(this.apiBaseUrl + "/" + companyId + "/" + body.locationId, new CompanyLocationModel(body));
  }

  delete(companyId: string, body: CompanyLocationModel) {
    const options = {
      headers: new HttpHeaders({
        "Content-Type": "application/json",
      }),
      body: new CompanyLocationModel(body),
    };
    return this.http.delete<ResponseModel>(this.apiBaseUrl + "/" + companyId + "/" + body.locationId, options);
  }
}
