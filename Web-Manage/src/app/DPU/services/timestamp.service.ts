import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { map, tap, switchMap, filter, reduce } from "rxjs/operators";
import { PageResponseModel, ResponseModel } from '../models/base.model';
import { forkJoin, Observable } from 'rxjs';
import { TimestampModel } from '../models/timestamp.model';

@Injectable({
  providedIn: 'root'
})
export class TimestampService {
  apiBaseUrl = "/timestamp/company";
  constructor(
    private http: HttpClient,
    private translateService: TranslateService
  ) { }

  getById(id: Number) {
    return this.http
      .get<TimestampModel>(this.apiBaseUrl + "/" + id)
      .pipe(map((e) => new TimestampModel(e, this.translateService)));
  }

  getLists(companyId: string) {
    return this.http
      .get<TimestampModel[]>(this.apiBaseUrl + "/" + companyId)
      .pipe(
        map((e) => e.map((e) => new TimestampModel(e, this.translateService)))
      );
  }

  getListsSearch(companyId: string, company_employeeId?: string, startDate?: string, endDate?: string, timestampType?: string) {
    return this.http
      .get<TimestampModel[]>("/timestamp/search/company/" + companyId + "?company_employeeId=" + company_employeeId + "&startDate=" + startDate + "&endDate=" + endDate + (timestampType ? "&timestampType=" + timestampType : ""))
      .pipe(
        map((e) => e.map((e) => new TimestampModel(e, this.translateService)))
      );
  }

  getListByPageSize(body: { page: number; size: number }) {
    return this.http
      .get<PageResponseModel<TimestampModel>>(this.apiBaseUrl, {
        params: body,
      })
      .pipe(
        map((page) => {
          return {
            ...page,
            content: page.content.map(
              (e) => new TimestampModel(e, this.translateService)
            ),
          };
        })
      );
  }

  getListAllPageSize(): Observable<TimestampModel[]> {
    return this.http
      .get<PageResponseModel<TimestampModel>>(this.apiBaseUrl, {
        params: { page: 0, size: 1 },
      })
      .pipe(
        switchMap((checkData: any) => {
          //console.log("checkData="+checkData)
          const size = 500;

          const numOfPages = checkData.totalElements / size;
          const parallelList: Observable<PageResponseModel<TimestampModel>>[] = [];

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
              let data: TimestampModel[] = [];
              for (let i = 0; i < response.length; i++) {
                data = data.concat(response[i].content);
              }
              return data;
            })
          );

        })


      );
  }

  save(companyId: string, body: TimestampModel) {
    return this.http.post<TimestampModel>(this.apiBaseUrl + "/" + companyId, new TimestampModel(body));
  }

  update(companyId: string, body: TimestampModel) {
    return this.http.put<ResponseModel>(this.apiBaseUrl + "/" + companyId + "/" + body.timestampId, new TimestampModel(body));
  }

  delete(companyId: string, body: TimestampModel) {
    const options = {
      headers: new HttpHeaders({
        "Content-Type": "application/json",
      }),
      body: new TimestampModel(body),
    };
    return this.http.delete<ResponseModel>(this.apiBaseUrl + "/" + companyId + "/" + body.timestampId, options);
  }
}
