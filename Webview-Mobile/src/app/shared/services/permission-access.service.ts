import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({
  providedIn: "root",
})
export class PermissionAccessService {
  baseUrl = "/permission-access"
  constructor(private http: HttpClient) {
  }

  getlistHrConfig(companyId: string, memberId: string) {
    return this.http.get(this.baseUrl + '/company/' + companyId + '/' + memberId)
  }

  setConfig(body: {
    companyId: string,
    memberId: string,
    type: string,
    // type:  "PAYSLIP" | "ZEEPAY"
    status: number,
    editBy: string,
    editName: string
    // editName: ""
  }
  ) {
    return this.http.post(this.baseUrl, body)
  }
}
