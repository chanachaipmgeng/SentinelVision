import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-company-profile-myhr',
  templateUrl: './company-profile-myhr.component.html',
  styleUrls: ['./company-profile-myhr.component.css']
})
export class CompanyProfileMyhrComponent implements OnInit {
  private tagDiv: ElementRef | undefined;
  @ViewChild("tagDiv") set content(content: ElementRef) {
    this.tagDiv = content;
  }
  history: any[] | any;
  currentLang = "";
  constructor(
    public cdr: ChangeDetectorRef,
    public translateService: TranslateService,
    private tokenService: TokenService) { }

  ngOnInit() {
    // this.myhrService.getCompanyHistory().subscribe((comHis) => {
    //   this.currentLang = this.translateService.currentLang;
    //   this.history = comHis;
    //   console.log("s", this.history);
    //   //   this.history[0].tdesc = this.history[0].tdesc!.replace(
    //   //     new RegExp('img', "g"),
    //   //     'img style="height:253px!important; width:450px!important;"'
    //   //   );
    //   //   this.history[0].edesc = this.history[0].edesc!.replace(
    //   //     new RegExp('img', "g"),
    //   //     'img style="height:253px!important; width:450px!important;"'
    //   //   );
    //   this.history[0].tdesc = this.history[0].tdesc!.replaceAll(
    //     'src="/hr/FileDownload',
    //     'src="' + this.tokenService.getMyHRConfig()!.myhrUrl + "/FileDownload"
    //   );

    //   this.history[0].edesc = this.history[0].edesc!.replaceAll(
    //     'src="/hr/FileDownload',
    //     'src="' + this.tokenService.getMyHRConfig()!.myhrUrl + "/FileDownload"
    //   );
    //   if (this.translateService.currentLang == "th") {
    //     this.tagDiv!.nativeElement.insertAdjacentHTML(
    //       "beforeend",
    //       this.history[0].tdesc!
    //     );
    //   } else {
    //     this.tagDiv!.nativeElement.insertAdjacentHTML(
    //       "beforeend",
    //       this.history[0].edesc!
    //     );
    //   }
    //   //   this.tagDiv!.nativeElement.removeAttribute("style");
    // });
    // this.cdr.markForCheck();
  }

}
