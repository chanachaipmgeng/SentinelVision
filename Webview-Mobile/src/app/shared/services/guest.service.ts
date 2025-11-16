import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { DeviceModel, MemberModel } from '../models/member.model';

@Injectable({
  providedIn: 'root',
})
export class GuestService {
  baseUrl = '/guest';
  constructor(private http: HttpClient) { }

  checkMail(body: {
    firstName: string,
    lastName: string,
    mobileNumber: string,
    sex: number,
    email: string,
    password: string,
    birthDate: string,
    idCard: string,
    passportNo: string,
    nationality: string,
    profilePhoto: string
  }) {
    return this.http.post<MemberModel>(this.baseUrl + '/validate-register', body);
  }

  register(body: {
    firstName: string,
    lastName: string,
    mobileNumber: string,
    sex: number,
    email: string,
    password: string,
    birthDate: string,
    idCard: string,
    passportNo: string,
    nationality: string,
    profilePhoto: string
  }) {
    return this.http.post<MemberModel>(this.baseUrl + '/register', body);
  }
  getQR2fauthen(body:any) {
    return this.http.post<any>(this.baseUrl + '/qr2fauthen', body)
  }
}  
