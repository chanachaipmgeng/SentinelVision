import { ChangeDetectorRef, Component, Input, OnChanges, OnDestroy, OnInit, inject } from '@angular/core';
import { NewsFullModel } from '../shared/models/news.model';
import { AdsService } from '../shared/services/ads.service';
import { ActivatedRoute } from '@angular/router';
import { TokenService } from '../shared/services/token.service';
import { HttpClient, HttpResponse } from '@angular/common/http';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';
import { Observable, BehaviorSubject, Subscription } from 'rxjs';
import { distinctUntilChanged, filter, map, switchMap, tap } from 'rxjs/operators';
import { MemberModel } from '../shared/models/member.model';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { UserModel } from '../shared/models/user-auth.model';
import { CompanyModel } from '../shared/models/company.model';
@Component({
  selector: 'app-apps-service-other',
  templateUrl: './apps-service-other.component.html',
  styleUrls: ['./apps-service-other.component.css']
})
export class AppsServiceOtherComponent implements OnInit {
  adsList: NewsFullModel[] = [];
  ads?: NewsFullModel
  memberModel : UserModel = this.tokenService.getUser()
  companyModel : CompanyModel = this.tokenService.getSelectCompany()
  lang = localStorage.getItem('Lang')
  private detailModal = inject(NgbModal);
  constructor(private http: HttpClient, private adsService: AdsService, private route: ActivatedRoute, private tokenService: TokenService,
              private domSanitizer: DomSanitizer, private modalService: NgbModal) {
    this.adsService.getAdsPublic(this.tokenService.getUser().member.memberId, 1).subscribe(
      (result) => {
        // result.forEach((e, i) => {
        //   this.http.get(e.newsPicture, { responseType: "blob" }).subscribe((response) => {
        //     // this.videoFile = this.sanitizer.bypassSecurityTrustUrl(URL.createObjectURL(result));
        //     result[i].picShow = this.domSanitizer.bypassSecurityTrustUrl(
        //       URL.createObjectURL(response)
        //     );
        //   });
        // });
        console.log("hi!!!!!!!! : ", result)
        this.adsList = result
      },
      (error) => {
        console.log(error);
      }
    );
    // if (this.tokenService.getSelectCompany().companyId) {
    //   this.adsService.getAdsPrivate(this.tokenService.getSelectCompany().companyId, 1).subscribe(
    //     (result) => {
    //       this.adsList = result;
    //     },
    //     (error) => {
    //       console.log(error);
    //     }
    //   );
    // } else {
    //   this.adsService.getAdsPublic(this.tokenService.getUser().member.memberId, 1).subscribe(
    //     (result) => {
    //       this.adsList = result;
    //     },
    //     (error) => {
    //       console.log(error);
    //     }
    //   );
    // }
  }

  ngOnInit(): void { }


  goUrl(url: string, detail: any) {
    // const urls = url
    // .replace('${memberId}', this.memberModel.memberId)
    // .replace('${companyId}', this.companyModel.companyId)
    // .replace('${token}', this.memberModel.access_token)
    // .replace('$lang',localStorage.getItem('Lang')!)
    // console.log(url)
    // alert(url)
    // if (url = urls) {
    //   // alert(url)
    //   // console.log(url)
    //   window.location.href = url
    // } else {
    // this.modalService.open(detail, { centered: true, size: 'lg' });
    // }
  }

  clickAds(ads: NewsFullModel){
    this.ads = ads
  }

  returnContent(adsList: NewsFullModel){
    return this.domSanitizer.bypassSecurityTrustHtml(adsList.content)
  }
}

