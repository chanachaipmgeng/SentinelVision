import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { map, switchMap } from "rxjs/operators";
import { PageResponseModel, ResponseModel } from '../models/base.model';
import { forkJoin, Observable } from 'rxjs';
import { TimestampModel } from '../models/timestamp.model';
import {
  DataTableQueryInput,
  PageEnvelope,
  buildDataTableQuery,
  normalizePageEnvelope,
  toDataTableParams,
} from '../../shared/utils/data-table-query';

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

  getListsSearch(companyId: string, company_employeeId?: string, startDate?: string, endDate?: string, timestampType?: string, approvalStatus?: string) {
    const params = new URLSearchParams();
    if (company_employeeId) params.set('company_employeeId', company_employeeId);
    if (startDate) params.set('startDate', startDate);
    if (endDate) params.set('endDate', endDate);
    if (timestampType) params.set('timestampType', timestampType);
    if (approvalStatus) params.set('approvalStatus', approvalStatus);
    const qs = params.toString();
    const url = "/timestamp/search/company/" + companyId + (qs ? "?" + qs : "");
    return this.http
      .get<TimestampModel[]>(url)
      .pipe(
        map((e) => e.map((e) => new TimestampModel(e, this.translateService)))
      );
  }

  /** Server-side search page (Phase E2). */
  searchPage(
    companyId: string,
    input: DataTableQueryInput & {
      company_employeeId?: string;
      startDate?: string;
      endDate?: string;
      timestampType?: string;
      approvalStatus?: string;
    } = {},
  ): Observable<PageEnvelope<TimestampModel>> {
    const query = buildDataTableQuery(input);
    const params = new HttpParams({
      fromObject: toDataTableParams(query, {
        company_employeeId: input.company_employeeId,
        startDate: input.startDate,
        endDate: input.endDate,
        timestampType: input.timestampType,
        approvalStatus: input.approvalStatus,
      }),
    });
    return this.http
      .get<PageEnvelope<TimestampModel> | TimestampModel[]>(
        `/timestamp/search/company/${companyId}`,
        { params },
      )
      .pipe(
        map((payload) => {
          const page = normalizePageEnvelope(payload);
          return {
            ...page,
            items: page.items.map((row) => new TimestampModel(row, this.translateService)),
          };
        }),
      );
  }

  exportReport(
    companyId: string,
    format: 'xlsx' | 'csv' = 'xlsx',
    company_employeeId?: string,
    startDate?: string,
    endDate?: string,
    timestampType?: string,
    approvalStatus?: string,
    mode: 'raw' | 'payroll' = 'raw'
  ): Observable<Blob> {
    const params = new URLSearchParams();
    params.set('format', format);
    params.set('mode', mode);
    if (company_employeeId) params.set('company_employeeId', company_employeeId);
    if (startDate) params.set('startDate', startDate);
    if (endDate) params.set('endDate', endDate);
    if (timestampType) params.set('timestampType', timestampType);
    if (approvalStatus) params.set('approvalStatus', approvalStatus);
    const url = `/timestamp/export/company/${companyId}?${params.toString()}`;
    return this.http.get(url, { responseType: 'blob' });
  }

  getShiftSettings(companyId: string): Observable<any> {
    return this.http.get(`${this.apiBaseUrl}/${companyId}/shift-settings`);
  }

  updateShiftSettings(companyId: string, body: any): Observable<any> {
    return this.http.put(`${this.apiBaseUrl}/${companyId}/shift-settings`, body);
  }

  approve(companyId: string, timestampId: string, body: { approve: boolean; rejectReason?: string; approvedBy?: string }) {
    return this.http.post<TimestampModel>(
      this.apiBaseUrl + "/" + companyId + "/" + timestampId + "/approval",
      body
    ).pipe(map((e) => new TimestampModel(e, this.translateService)));
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
