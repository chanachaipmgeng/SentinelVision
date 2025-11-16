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
@Component({
  selector: 'app-subordinate-timestamp',
  templateUrl: './subordinate-timestamp.component.html',
  styleUrls: ['./subordinate-timestamp.component.scss']
})
export class SubordinateTimestampComponent {
  public dateRange: { start: Date, end: Date } = { start: new Date(new Date().getFullYear(), new Date().getMonth(), 1), end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 24) };
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
  memberId = this.tokenService.getUser().member.memberId
  employeeModel: EmployeeModel = new EmployeeModel()
  constructor(private timestampService: TimestampService, private tokenService: TokenService, public datepipe: DatePipe, public translate: TranslateService,
    private modalService: NgbModal,
    private route: ActivatedRoute,
    private employeeService: EmployeeService
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
    })
  }


  openMap(content: any, timestamp: TimestampModel) {
    this.timestampModel = timestamp
    this.modalService.open(content, { centered: true, size: 'lg' });
  }

}
