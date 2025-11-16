import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { DeviceModel, MemberModel } from '../models/member.model';

@Injectable({
  providedIn: 'root',
})
export class MemberService {
  baseUrl = '/member';
  constructor(private http: HttpClient) { }

  getPersonalInfo(memberId: string) {
    return this.http.get<MemberModel>(this.baseUrl + '/' + memberId);
  }

  updatePersonalInfo(model: MemberModel) {
    return this.http.put(this.baseUrl + '/profile', model);
  }

  changePassword(model: { memberId: string, oldPassword: string, newPassword: string }) {
    return this.http.put(this.baseUrl + '/change-password', model);
  }

  updatePictureProfile(body: {
    memberId: string,
    photoData: string
  }) {
    return this.http.put(this.baseUrl + "/profile/picture", body, { responseType: "text" })
  }

  getDeviceAccessList(memberId: string) {
    return this.http.get<DeviceModel>(this.baseUrl + '/' + memberId + "/" + "device-access-list");
  }

}  
