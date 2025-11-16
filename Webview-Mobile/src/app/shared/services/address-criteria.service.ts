import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { SubordinateTimestampModel } from '../models/subordinate-timestamp.model';
@Injectable({
  providedIn: "root",
})
export class AddressCriteriaService {
  baseUrl = "/address-criteria"
  constructor(
    private http: HttpClient,
  ) {
  }

  addressCriteria(companyId: string,
    memberId: string,
    empCode: string) {
    return this.http.get(this.baseUrl + "/" + companyId + "/" + memberId + "/" + empCode)
  }

  getLastSubordinateTimestamp(body: {
    companyId: string,
    memberId: string,
    startDateTime: string,
    endDateTime: string
    // startDateTime: 2024-05-16 00:00+0700,
  }) {
    return this.http.post<SubordinateTimestampModel[]>(this.baseUrl + "/get-last-subordinate-timestamp-list", body)
  }

}
