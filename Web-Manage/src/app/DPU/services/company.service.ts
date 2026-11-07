import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { map, tap, switchMap, filter, reduce } from "rxjs/operators";
import { PageResponseModel, ResponseModel } from '../models/base.model';
import { forkJoin, Observable } from 'rxjs';
import { CompanyModel } from '../models/company.model';


@Injectable({
  providedIn: 'root'
})
export class CompanyService {

  apiBaseUrl = "/companys";
  constructor(
    private http: HttpClient,
    private translateService: TranslateService
  ) { }

  getById(id: string) {
    return this.http
      .get<CompanyModel>(this.apiBaseUrl + "/" + id)
      .pipe(map((e) => new CompanyModel(e, this.translateService)));
  }

  getLists() {
    return this.http
      .get<CompanyModel[]>(this.apiBaseUrl)
      .pipe(
        map((e) => e.map((e) => new CompanyModel(e, this.translateService)))
      );
  }

  getListByPageSize(body: { page: number; size: number }) {
    return this.http
      .get<PageResponseModel<CompanyModel>>(this.apiBaseUrl, {
        params: body,
      })
      .pipe(
        map((page) => {
          return {
            ...page,
            content: page.content.map(
              (e) => new CompanyModel(e, this.translateService)
            ),
          };
        })
      );
  }

  getListAllPageSize(): Observable<CompanyModel[]> {
    return this.http
      .get<PageResponseModel<CompanyModel>>(this.apiBaseUrl, {
        params: { page: 0, size: 1 },
      })
      .pipe(
        switchMap((checkData: any) => {
          //console.log("checkData="+checkData)
          const size = 500;

          const numOfPages = checkData.totalElements / size;
          const parallelList: Observable<PageResponseModel<CompanyModel>>[] = [];

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
              let data: CompanyModel[] = [];
              for (let i = 0; i < response.length; i++) {
                data = data.concat(response[i].content);
              }
              return data;
            })
          );

        })


      );
  }

  save(body: CompanyModel) {
    return this.http.post<ResponseModel>(this.apiBaseUrl, new CompanyModel(body));
  }

  update(body: CompanyModel) {
    return this.http.put<ResponseModel>(this.apiBaseUrl + "/" + body.companyId, new CompanyModel(body));
  }


  delete(body: CompanyModel) {
    const options = {
      headers: new HttpHeaders({
        "Content-Type": "application/json",
      }),
      body: new CompanyModel(body),
    };
    return this.http.delete<ResponseModel>(this.apiBaseUrl + "/" + body.companyId);
  }

  /** D5 tenant lifecycle / quotas (system admin). */
  suspend(companyId: string) {
    return this.http.post<any>(`${this.apiBaseUrl}/${companyId}/suspend`, {});
  }

  resume(companyId: string) {
    return this.http.post<any>(`${this.apiBaseUrl}/${companyId}/resume`, {});
  }

  offboard(companyId: string, purgeDevices = true) {
    return this.http.post<any>(`${this.apiBaseUrl}/${companyId}/offboard`, { purgeDevices });
  }

  getQuotas(companyId: string) {
    return this.http.get<any>(`${this.apiBaseUrl}/${companyId}/quotas`);
  }

  putQuotas(companyId: string, body: {
    packageCode?: string | null;
    maxDevices?: number | null;
    maxEmployees?: number | null;
    gpuPriority?: number;
  }) {
    return this.http.put<any>(`${this.apiBaseUrl}/${companyId}/quotas`, body);
  }

}
