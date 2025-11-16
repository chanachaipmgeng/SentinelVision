import {
  NewsModel,
  NewsFullModel,
  CompanyNewsModel,
} from './../models/news.model';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from 'src/environments/environment';
import { map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AdsService {
  linkPrd = 'https://zeeme.myhr.co.th'

  constructor(private http: HttpClient) { }

  getNewsListCompany(companyId: string): Promise<NewsFullModel[]> {
    return new Promise((resolve, reject) => {
      this.http
        .get<NewsFullModel[]>(
          this.linkPrd + '/ZeemeAds/zee-me-news/company/' +
          companyId
        )
        .subscribe((response) => {
          console.log(response);
          resolve(response);
        });
    });
  }

  getAllNews(): Promise<NewsFullModel[]> {
    return new Promise((resolve, reject) => {
      this.http
        .get<NewsFullModel[]>(
          this.linkPrd + '/ZeemeAds/zee-me-news'
        )
        .subscribe((response) => {
          console.log(response);
          resolve(response.map((e) => new NewsFullModel(e)));
        });
    });
  }

  getNewsFullModel(newId: string): Promise<NewsFullModel> {
    return new Promise((resolve, reject) => {
      this.http
        .get<NewsFullModel>(
          this.linkPrd + '/ZeemeAds/zee-me-news/' + newId
        )
        .subscribe((response) => {
          resolve(new NewsFullModel(response));
        });
    });
  }

  deleteNewsFullModel(newId: string): Promise<NewsFullModel> {
    return new Promise((resolve, reject) => {
      this.http
        .delete<NewsFullModel>(
          this.linkPrd + '/ZeemeAds/zee-me-news/' + newId
        )
        .subscribe((response) => {
          resolve(response);
        });
    });
  }

  getCompanyByNews(newId: string): Promise<CompanyNewsModel[]> {
    return new Promise((resolve, reject) => {
      this.http
        .get<CompanyNewsModel[]>(
          this.linkPrd + '/ZeemeAds/company-news/news/' + newId
        )
        .subscribe((response) => {
          console.log(response);
          resolve(response);
        });
    });
  }

  updateNews(model: NewsFullModel): Promise<NewsFullModel> {
    return new Promise((resolve, reject) => {
      console.log(model);
      this.http
        .put<NewsFullModel>(
          this.linkPrd + '/ZeemeAds/zee-me-news/',
          model
        )
        .subscribe((response) => {
          resolve(response);
        });
    });
  }

  updateComNewsList(
    newId: string,
    model: CompanyNewsModel[]
  ): Promise<CompanyNewsModel[]> {
    return new Promise((resolve, reject) => {
      console.log(model);
      this.http
        .post<CompanyNewsModel[]>(
          this.linkPrd + '/ZeemeAds/company-news/' + newId,
          model
        )
        .subscribe((response) => {
          resolve(response);
        });
    });
  }
  deleteComNewsList(newId: string, model: CompanyNewsModel): Promise<CompanyNewsModel> {
    return new Promise((resolve, reject) => {
      console.log(model);
      this.http
        .delete<CompanyNewsModel>(
          this.linkPrd + '/ZeemeAds/company-news/' + model.companyId + '/' + newId
        )
        .subscribe((response) => {
          resolve(response);
        });
    });
  }

  createNews(model: NewsFullModel): Promise<NewsFullModel> {
    return new Promise((resolve, reject) => {
      this.http
        .post<NewsFullModel>(
          this.linkPrd + '/ZeemeAds/zee-me-news/',
          model
        )
        .subscribe((response) => {
          resolve(response);
        });
    });
  }

  // getAllNews(companyId: string): Promise<NewsModel[]> {
  //   return new Promise((resolve, reject) => {
  //     // resolve(this.mock);
  //     this.http
  //       .get<NewsModel[]>(this.apiMain + "/list/" + companyId)
  //       .subscribe((response) => {
  //         resolve([...response, ...this.mock]);
  //       });
  //   });
  // }

  getApproveNews(companyId: string): Observable<NewsFullModel[]> {
    return this.http.get<NewsFullModel[]>(
      this.linkPrd + '/ZeemeAds/zee-me-news/company-status/1'
    );
  }

  getActiveNewsCompany(companyId: string): Observable<NewsFullModel[]> {
    return this.http.get<NewsFullModel[]>(
      this.linkPrd + '/ZeemeAds/zee-me-news/active-company/' +
      companyId
    );
  }

  getAdsPublic(memberId: string, layout: number){
    return this.http.get<NewsFullModel[]>(
      this.linkPrd + '/ZeemeAds/zee-me-news/public/member/' +
      memberId + "/" + layout
    )
  }

  getAdsPrivate(companyId: string, layout: number): Observable<NewsFullModel[]> {
    return this.http.get<NewsFullModel[]>(
      this.linkPrd + '/ZeemeAds/zee-me-news/private/company/' +
      companyId + "/" + layout
    );
  }

  getListCompanyByMemberId(memberId: string): Observable<any> {
    return this.http.get<any>('https://zeeme.myhr.co.th/ZeemeApi/rest/member/company/' + memberId);
  }
}
