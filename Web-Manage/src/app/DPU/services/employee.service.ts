import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { map, tap, switchMap, filter, reduce } from "rxjs/operators";
import { PageResponseModel, ResponseModel } from '../models/base.model';
import { forkJoin, Observable } from 'rxjs';
import { EmployeeModel } from '../models/employee.model';
import { CompanyModel } from '../models/company.model';

@Injectable({
  providedIn: 'root'
})
export class EmployeeService {

  apiBaseUrl = "/employees/company";
  constructor(
    private http: HttpClient,
    private translateService: TranslateService
  ) { }

  getById(id: Number) {
    return this.http
      .get<EmployeeModel>(this.apiBaseUrl + "/" + id)
      .pipe(map((e) => new EmployeeModel(e, this.translateService)));
  }

  getLists(companyId: string) {
    return this.http
      .get<EmployeeModel[]>(this.apiBaseUrl + "/" + companyId)
      .pipe(
        map((e) => e.map((e) => new EmployeeModel(e, this.translateService)))
      );
  }

  getMemberById(companyId: string, memberId: string) {
    return this.http
      .get<EmployeeModel>(this.apiBaseUrl + "/" + companyId + "/member/" + memberId)
      .pipe(map((e) => new EmployeeModel(e, this.translateService)));
  }

  getListByPageSize(body: { page: number; size: number }) {
    return this.http
      .get<PageResponseModel<EmployeeModel>>(this.apiBaseUrl, {
        params: body,
      })
      .pipe(
        map((page) => {
          return {
            ...page,
            content: page.content.map(
              (e) => new EmployeeModel(e, this.translateService)
            ),
          };
        })
      );
  }

  getListAllPageSize(): Observable<EmployeeModel[]> {
    return this.http
      .get<PageResponseModel<EmployeeModel>>(this.apiBaseUrl, {
        params: { page: 0, size: 1 },
      })
      .pipe(
        switchMap((checkData: any) => {
          //console.log("checkData="+checkData)
          const size = 500;

          const numOfPages = checkData.totalElements / size;
          const parallelList: Observable<PageResponseModel<EmployeeModel>>[] = [];

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
              let data: EmployeeModel[] = [];
              for (let i = 0; i < response.length; i++) {
                data = data.concat(response[i].content);
              }
              return data;
            })
          );

        })


      );
  }

  save(body: EmployeeModel, companyId: string) {
    return this.http.post<ResponseModel>(this.apiBaseUrl + "/" + companyId, new EmployeeModel(body));
  }

  update(body: EmployeeModel, companyId: string) {
    return this.http.put<ResponseModel>(this.apiBaseUrl + "/" + companyId, new EmployeeModel(body));
  }

  delete(companyId: string, body: EmployeeModel) {
    const options = {
      headers: new HttpHeaders({
        "Content-Type": "application/json",
      }),
      body: new EmployeeModel(body),
    };
    return this.http.delete<ResponseModel>(this.apiBaseUrl + "/" + companyId + "/" + body.company_employeeId, options);
  }

  getCompanyAdmin(memberId: string) {
    return this.http
      .get<CompanyModel[]>("/employees/member/" + memberId + "/companies-admin")
      .pipe(
        map((e) => e.map((e) => new CompanyModel(e, this.translateService)))
      );
  }


}
