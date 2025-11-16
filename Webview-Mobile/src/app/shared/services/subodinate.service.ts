import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { SubWarningDailyModel, SubWarningModel, SubWarningTimeListModel } from '../models/subodinate.model';
import { PageModel } from '../models/page.model';
import { Observable, forkJoin } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class SubodinateService {

baseUrl = "/warning-timestamp/"

constructor(private http:HttpClient, ) { }

getsubWarning(companyId: string, memberId: string){
  return this.http.get<SubWarningModel[]>(this.baseUrl  + companyId + "/" + "sub/" + memberId)
}

getsubWarningDaily(companyId: string, memberId: string, stDate: string, endDate: string){
  return this.http.get<SubWarningDailyModel>("/warning-timestamp/" +
          companyId +
          "/" + "sub/" + memberId + "/" +
          stDate +
          "/" +
          endDate +
          "?size=10000")
}

getsubWarningTimeList(companyId: string, memberId: string){
  return this.http.get<SubWarningTimeListModel[]>(this.baseUrl + "group-date/" + companyId + "/" + memberId)
}

// approveWarningTime(body: any){
//   return this.http.post("/warning-timestamp", body)
// }
approveWarningTime(body: {
  companyId: string,
  memberId: string,
  employeeCode: string,
  approveId : string,
  approveStatus : number,
  approveType : number,
  locationName : string,
  swipeDateTime : string
}){
  return this.http.post("/warning-timestamp", body)
}


getListByPageSizePG(companyId: string, page: number, size: number) {
  return this.http.get<PageModel<SubWarningModel>>(this.baseUrl + 'company/' + companyId +
      '?size=' + size + '&page=' +
      page)
}

getListAllPageSizePG(companyId: string): Observable<SubWarningModel[]> {
  return this.http
    .get<PageModel<SubWarningModel>>(this.baseUrl + 'company/' + companyId +'?size=1&page=0')
    .pipe(
      switchMap((checkData: any) => {
        const size = 500;
        const numOfPages = checkData.totalElements > 0 ? (checkData.totalElements / size) : 1;
        const parallelList: Observable<PageModel<SubWarningModel>>[] = [];

        for (let page = 0; page < numOfPages; page++) {
          parallelList.push(
            this.getListByPageSizePG(companyId, page, size)
          );
        }
        return forkJoin(parallelList).pipe(
          map((response) => {
            let data: SubWarningModel[] = [];
            for (let i = 0; i < response.length; i++) {
              data = data.concat(response[i].content);
            }
            return data;
          })
        );
      })
    );
}

getWarningDailyZeeme(companyId: string, stDate: string, endDate: string, page: number){
  return this.http.get<any>(this.baseUrl + "company/" + companyId + "/" + stDate + "/" + endDate + "?size=30000&page=" + page)
}

getWarningDaily(companyId: string, stDate: string, endDate: string){
  return this.http.get<SubWarningDailyModel>(
    this.baseUrl + 
    companyId +
    "/" +
    stDate +
    "/" +
    endDate +
    "?size=1000")
}

}
