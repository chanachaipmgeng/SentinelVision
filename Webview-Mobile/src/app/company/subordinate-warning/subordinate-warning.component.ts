import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslateService } from '@ngx-translate/core';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { TimestampModel } from 'src/app/shared/models/timestamp.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TimestampService } from 'src/app/shared/services/timestamp.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { DatePipe } from '@angular/common';
import * as moment from 'moment';
import swal from 'sweetalert';
import { CompanyLocationService } from 'src/app/shared/services/company-location.service';
import { CompanyLocationModel } from 'src/app/shared/models/company-location.model';
@Component({
  selector: 'app-subordinate-warning',
  templateUrl: './subordinate-warning.component.html',
  styleUrls: ['./subordinate-warning.component.scss'],
})
export class SubordinateWarningComponent {
  public dateRange: { start: Date, end: Date } = { start: new Date(new Date().getFullYear(), new Date().getMonth(), 1), end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 24) };
  isLocation = false;
  public options: any = {
    "autoApply": true,

    ranges: this.translate.currentLang == 'th' ? {
      'วันนี้': [moment(), moment()],
      '7 วันล่าสุด': [moment().subtract(6, 'days'), moment()],
      '30 วันล่าสุด': [moment().subtract(29, 'days'), moment()],
      'เดือนนี้': [moment().startOf('month'), moment().endOf('month')]
    } : {
      'Today': [moment(), moment()],
      'Last 7 Days': [moment().subtract(6, 'days'), moment()],
      'Last 30 Days': [moment().subtract(29, 'days'), moment()],
      'This Month': [moment().startOf('month'), moment().endOf('month')]
    },
    "locale": {
      "format": "DD/MM/YYYY",
      "separator": " - ",
      "applyLabel": "ตกลง",
      "cancelLabel": "ยกเลิก",
      "fromLabel": "จาก",
      "toLabel": "ถึง",
      "daysOfWeek": this.translate.instant("NameDayShort"),
      "monthNames": this.translate.instant("NameMonth"),
      "customRangeLabel": this.translate.instant("Range date"),
      "firstDay": 1,
      direction: 'daterange-center shadow'
    },

    "alwaysShowCalendars": true,
    "startDate": this.dateRange.start,
    "endDate": this.dateRange.end,
  };

  listTimeStampLog: TimestampModel[] = []
  selectedTime: any
  latitude: number = 13.8051584
  longitude: number = 100.5018
  timestampModel: TimestampModel = new TimestampModel()
  locationModel: CompanyLocationModel = new CompanyLocationModel()
  memberId = this.tokenService.getUser().member.memberId
  employeeModel: EmployeeModel = new EmployeeModel()
  constructor(private timestampService: TimestampService, private tokenService: TokenService, public datepipe: DatePipe, public translate: TranslateService,
    private modalService: NgbModal,
    private route: ActivatedRoute,
    private employeeService: EmployeeService,
    private companyLocation: CompanyLocationService
  ) {
    this.getTimestamp()
  }

  public selectedDate(value: any, datepicker?: any) {


    // any object can be passed to the selected event and it will be passed back here
    datepicker.start = value.start;
    datepicker.end = value.end;

    // use passed valuable to update state
    this.dateRange.start = value.start;
    this.dateRange.end = value.end;
    this.getTimestamp()
  }

  getTimestamp() {
    this.timestampService.getListsSearch(this.tokenService.getSelectCompany().companyId, "", new Date(this.dateRange.start).toISOString(), new Date(this.dateRange.end).toISOString()).subscribe(result => {
      this.listTimeStampLog = result.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
      this.listTimeStampLog = this.listTimeStampLog.filter(e => e.employee.bossId == this.tokenService.getUser().member.memberId)
      this.listTimeStampLog = this.listTimeStampLog.filter(e => e.timestampType == 0)
      console.log(this.listTimeStampLog)
    })
  }


  openMap(content: any, timestamp: TimestampModel) {
    this.isLocation = false;
    this.timestampModel = new TimestampModel(timestamp, this.translate)
    this.modalService.open(content, { centered: true, size: 'lg' });
  }

  approve() {
    swal({
      title: "Are you sure?",
      text: "คุณต้องการบันทึกหรือไม่",
      icon: "warning",
      dangerMode: false,
      buttons: ["Cancel", "Confirm"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.timestampModel.timestampType = 1
          this.timestampService.update(this.timestampModel).subscribe(result => {
            swal("Save Success!!", "อนุมัติการลงเวลาสำเร็จ", "success");
            this.modalService.dismissAll('Cross click')
            this.getTimestamp()
          })
          if (this.isLocation) {
            this.locationModel = new CompanyLocationModel()
            this.locationModel.companyId = this.timestampModel.companyId
            this.locationModel.latitude = this.timestampModel.latitude
            this.locationModel.longitude = this.timestampModel.longitude
            this.locationModel.locationName = this.timestampModel.locationName
            this.locationModel.locationType = 0
            this.locationModel.startDate = new Date().toISOString()
            this.locationModel.endDate = new Date().toISOString()
            this.companyLocation.save(this.locationModel.companyId, this.locationModel).subscribe(result => {
              swal("Save Success!!", "บันทึกสถานที่สำเร็จ", "success");
            })
          }
        }
      });
  }

  disapprove() {
    swal({
      title: "Are you sure?",
      text: "คุณต้องการบันทึกหรือไม่",
      icon: "warning",
      dangerMode: false,
      buttons: ["Cancel", "Confirm"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.timestampModel.timestampType = 3
          this.timestampService.update(this.timestampModel).subscribe(result => {
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.modalService.dismissAll('Cross click')
            this.getTimestamp()
          })
        }
      });
  }


  // selectAll() {
  //   this.subWarningDailySelect = this.subWarningDailySelect.map((x: any) => {
  //     return { ...x, isSelected: this.checkedAll };
  //   });
  // }

  // approveAll() {
  //   const modalRef = this.modalService.open(AlertComponent, { centered: true });
  //   modalRef.componentInstance.message = 'Do you want to confirm?';
  //   modalRef.componentInstance.confirmModal = true;
  //   modalRef.result.then(
  //     (respone) => {
  //       const swipeDateTime = this.subWarningDailySelect
  //         .filter((x: any) => x.isSelected)
  //         .map((x: any) => x.swipeDateTime + x.memberId);
  //       const selectData = this.subWarningDailyModel.datas.filter(
  //         (x) =>
  //           swipeDateTime.findIndex(
  //             (y: string) => y == x.swipeDateTime + x.memberId
  //           ) > -1
  //       );
  //       let check = 0;
  //       selectData.forEach((x, i) => {
  //         const body = {
  //           companyId: this.tokenService.getSelectCompany().companyId,
  //           memberId: x.memberId,
  //           employeeCode: x.employeeCode,
  //           approveId: this.tokenService.getUser().member.memberId,
  //           approveStatus: 1,
  //           approveType: 1,
  //           locationName: '',
  //           swipeDateTime: x.swipeDateTime,
  //         };
  //         this.subodinateService.approveWarningTime(body).subscribe(
  //           (result) => {
  //             check = check + 1;
  //             if (i == selectData.length - 1) {
  //               if (check == selectData.length) {
  //                 const modalRef = this.modalService.open(AlertComponent, {
  //                   centered: true,
  //                 });
  //                 modalRef.componentInstance.message = 'STATUS.Success';
  //               } else {
  //                 const modalRef = this.modalService.open(AlertComponent, {
  //                   centered: true,
  //                 });
  //                 modalRef.componentInstance.message = 'STATUS.Fail';
  //               }
  //               this.getWarningDaily();
  //             }
  //           },
  //           (error) => {
  //             if (i == selectData.length - 1 && check != selectData.length) {
  //               const modalRef = this.modalService.open(AlertComponent, {
  //                 centered: true,
  //               });
  //               modalRef.componentInstance.message = 'STATUS.Fail';
  //             }
  //             this.getWarningDaily();
  //           }
  //         );
  //       });
  //     },
  //     (error) => {}
  //   );
  // }

  // goSubWarningTimeMap(data: DataModel) {
  //   this.router.navigate([
  //     '/company/sub-warning-timestamp-map',
  //     {
  //       data: JSON.stringify(data),
  //       startdate: this.convertDate(new Date()),
  //       enddate: this.convertDate(new Date()),
  //       path: '/company/subordinate-warning/',
  //       startDate: this.convertDate(new Date()),
  //     },
  //   ]);
  // }

  // checkSelect() {
  //   return this.byDateFilter()?.every((x) => x.isSelected == false);
  // }
}
