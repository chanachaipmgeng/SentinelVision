import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class RecruitmentService {
  baseUrl = "/recruitment"
  constructor(private http: HttpClient) { }


  applyCompany(body:any) {
    return this.http.post(this.baseUrl + '/apply', body)
  }


}
