import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { PdpaModel } from '../models/pdpa.model';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PdpaService {

linkZeeserver = 'https://zeeserver.myhr.co.th'
ip = "https://api.ipify.org/?format=json"

constructor(private http: HttpClient) { }

getpdpaLatestVersion(){
  return this.http.get<PdpaModel>(this.linkZeeserver + "/ZeemeConfig/pdpa/latest-version")
}
getpdpaConsent(version: number, memberId: string){
  return this.http.get<PdpaModel>("/member/pdpa-consent-first/" + version + "/" + memberId)
}

consent(body: any){
  return this.http.post("/member/pdpa-consent",body)
}



}
