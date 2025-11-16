import { ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, Input, OnInit, ViewChild, inject } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { LangChangeEvent, TranslateService } from '@ngx-translate/core';
import { NativeMobileService } from 'src/app/shared/services/native-mobile.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-news-event-detail',
  templateUrl: './news-event-detail.component.html',
  styleUrls: ['./news-event-detail.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NewsEventDetailComponent implements OnInit {
  @Input() topic: string = ""
  @Input() desc: string = ""
  @Input() picUrl: string = ""
  @Input() startDate: string = ""
  @Input() endDate: string = ""
  @Input() place: string = ""
  @Input() file: string = ""
  private tagDiv: ElementRef | undefined;
  activeModal = inject(NgbActiveModal);
  @ViewChild("tagDiv") set content(content: ElementRef) {
    this.tagDiv = content;
  }
  constructor(
    public cdr: ChangeDetectorRef,
    public translateService: TranslateService,
    private mobileService: NativeMobileService,
    private tokenService: TokenService
  ) {
  }

  ngOnInit() {
    this.tagDiv!.nativeElement.innerHTML = this.desc
  }

  downloadFile(url: string) {
    // this.mobileService.downloadFile(url, this.tokenService.getTokenMyHR()!)
  }

}
