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
    return this.http.post<ResponseModel>(this.apiBaseUrl + "/" + companyId, this.toApiPayload(body));
  }

  update(body: EmployeeModel, companyId: string) {
    return this.http.put<ResponseModel>(this.apiBaseUrl + "/" + companyId, this.toApiPayload(body));
  }

  /** Strip empty optional fields that otherwise cause FastAPI 422 validation errors. */
  private toApiPayload(body: EmployeeModel): Record<string, unknown> {
    const m = body?.member || ({} as any);
    const blank = (v: any) => v === '' || v === undefined || v === null;
    const member: Record<string, unknown> = {
      email: m.email,
      firstName: blank(m.firstName) ? null : m.firstName,
      lastName: blank(m.lastName) ? null : m.lastName,
      picture: blank(m.picture) ? null : m.picture,
      phoneNumber: blank(m.phoneNumber) ? null : m.phoneNumber,
      birthDate: blank(m.birthDate) ? null : m.birthDate,
      address: blank(m.address) ? null : m.address,
      emergencyContactName: blank(m.emergencyContactName) ? null : m.emergencyContactName,
      emergencyContactPhone: blank(m.emergencyContactPhone) ? null : m.emergencyContactPhone,
      attachmentUrls: blank(m.attachmentUrls) ? null : m.attachmentUrls,
    };
    const position = body?.position?.positionId
      ? {
          positionId: body.position.positionId,
          thName: body.position.thName || null,
          engName: body.position.engName || null,
        }
      : null;
    const department = body?.department?.departmentId
      ? {
          departmentId: body.department.departmentId,
          thName: body.department.thName || null,
          engName: body.department.engName || null,
        }
      : null;
    return {
      member,
      position,
      department,
      employeeId: blank(body.employeeId) ? null : body.employeeId,
      salary: blank(body.salary) ? 0 : Number(body.salary),
      bossId: blank(body.bossId) ? null : body.bossId,
      companyRoleType: body.companyRoleType ?? 0,
      empType: body.empType ?? 1,
      startDate: blank(body.startDate) ? null : body.startDate,
      company_employeeId: blank(body.company_employeeId) ? undefined : body.company_employeeId,
    };
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

  downloadImportTemplate(companyId: string) {
    return this.http.get(this.apiBaseUrl + "/" + companyId + "/import-template", {
      responseType: "blob",
    });
  }

  importExcel(companyId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return this.http.post<EmployeeImportResult>(
      this.apiBaseUrl + "/" + companyId + "/import",
      formData
    );
  }

}

export interface EmployeeImportCreatedRow {
  row: number;
  email: string;
  company_employeeId: string;
  employeeId: string;
}

export interface EmployeeImportErrorRow {
  row: number;
  email: string;
  message: string;
}

export interface EmployeeImportResult {
  total: number;
  success: number;
  failed: number;
  created: EmployeeImportCreatedRow[];
  errors: EmployeeImportErrorRow[];
}
