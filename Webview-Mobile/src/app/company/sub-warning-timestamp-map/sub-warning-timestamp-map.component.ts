import { HttpParams } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { DataModel } from 'src/app/shared/models/subodinate.model';
import { SubodinateService } from 'src/app/shared/services/subodinate.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { __param } from 'tslib';

@Component({
  selector: 'app-sub-warning-timestamp-map',
  templateUrl: './sub-warning-timestamp-map.component.html',
  styleUrls: ['./sub-warning-timestamp-map.component.scss']
})
export class SubWarningTimestampMapComponent implements OnInit {

  data?: DataModel
  memberId: string = "";
  companyId: string = "";
  memberName: string = "";
  employeeCode: string = "";
  swipDateTime: string = "";
  swipeTypeName: string = "";
  // lat: string = "";
  // lng: string = "";
  pictureTimeStamp: string = "";
  // date: string = "";
  // typename: string = "";
  longitude: number = 0;
  latitude: number = 0;

  appoveType = 1;
  locationName: string = ""


  path: string
  startdate: string
  enddate: string

  constructor(
    private tokenService: TokenService,
    private modalService: NgbModal,
    public activatedRoute: ActivatedRoute,
    private router: Router,
    private subodinateService: SubodinateService
  ) {
    this.activatedRoute.params.subscribe(params => {
      this.data = params['data'] ? JSON.parse(params['data']) : undefined
      if (this.data) {
        this.memberId = this.data.memberId
        this.companyId = this.data.companyId
        this.pictureTimeStamp = this.data.stampFileName
        this.memberName = this.data.memberName
        this.swipDateTime = this.data.swipeDateTime
        this.swipeTypeName = this.data.swipeTypeName
        this.latitude = Number(this.data.lat)
        this.longitude = Number(this.data.lng)
        this.employeeCode = this.data.employeeCode
      }
      this.startdate = params.startdate
      this.enddate = params.enddate
      this.path = params.path
    })
  }


  ngOnInit() {
  }


  submit(data: number) {
    let body = {
      companyId: this.companyId,
      memberId: this.memberId,
      employeeCode: this.employeeCode,
      approveId: this.tokenService.getUser().member.memberId,
      approveStatus: data,
      approveType: this.appoveType,
      locationName: this.locationName,
      swipeDateTime: this.swipDateTime,
    }
    if (this.appoveType == 2 && this.locationName == "") {
      const modalRef = this.modalService.open(AlertComponent, { centered: true })
      modalRef.componentInstance.message = "MESSAGE.Please enter the name of the place."
    } else {
      const modalRef = this.modalService.open(AlertComponent, { centered: true })
      modalRef.componentInstance.message = "Do you want to confirm?"
      modalRef.componentInstance.confirmModal = true
      modalRef.result.then(respone => {
        // console.log("asaas", body)
        this.subodinateService.approveWarningTime(body).subscribe(result => {
          const modalRef = this.modalService.open(AlertComponent, { centered: true })
          modalRef.componentInstance.message = "STATUS.Success"
          // this.router.navigate(['/company/subordinate-warning-timestamp/' + this.memberId, {
          //   startdate: this.startdate,
          //   enddate: this.enddate
          // }]);
          this.router.navigate([this.path, {
            startdate: this.startdate,
            enddate: this.enddate
          }]);
        },
          error => {
            const modalRef = this.modalService.open(AlertComponent, { centered: true })
            modalRef.componentInstance.message = "STATUS.Fail"
          }
        )
      }, error => {

      }
      )
    }

  }



}
