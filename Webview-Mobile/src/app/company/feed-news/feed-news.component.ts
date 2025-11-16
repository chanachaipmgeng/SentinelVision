import { Component, OnInit, inject } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslateService } from '@ngx-translate/core';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { NewsEventDetailComponent } from '../news-event-detail/news-event-detail.component';

@Component({
  selector: 'app-feed-news',
  templateUrl: './feed-news.component.html',
  styleUrls: ['./feed-news.component.css']
})
export class FeedNewsComponent implements OnInit {
  news: any[] = [];
  tevent: any[] = [];
  currentDate = new Date()
  private detailModal = inject(NgbModal);
  constructor(private employeeService: EmployeeService, private tokenService: TokenService, private translateService: TranslateService) { }

  ngOnInit() {
  }



  openModalDetail(item: any) {
    // console.log(item)
    // let modalRef = this.detailModal.open(NewsEventDetailComponent, { centered: true, size: 'lg' });
    // modalRef.componentInstance.topic = item.getTopicDesc()
    // modalRef.componentInstance.desc = item.getDetailDesc()
    // modalRef.componentInstance.startDate = item.startDate
    // modalRef.componentInstance.endDate = item.endDate
    // modalRef.componentInstance.picUrl = item.getPictureUrl()
  }

  openModalEventDetail(item: any) {
    console.log(item)
    let modalRef = this.detailModal.open(NewsEventDetailComponent, { centered: true, size: 'lg' });
    modalRef.componentInstance.topic = item.getTopicDesc()
    modalRef.componentInstance.desc = item.getDetailDesc()
    modalRef.componentInstance.startDate = item.dateStart
    modalRef.componentInstance.endDate = item.dateEnd
    modalRef.componentInstance.picUrl = item.getPictureUrl()
    modalRef.componentInstance.place = item.getPlaceDesc()
    modalRef.componentInstance.file = item.getFileEvent()
  }
}
