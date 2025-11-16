import { DatePipe } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslateService } from '@ngx-translate/core';
import * as moment from 'moment';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { TimestampModel } from 'src/app/shared/models/timestamp.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TimestampService } from 'src/app/shared/services/timestamp.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-timestamp-log',
  templateUrl: './timestamp-log.component.html',
  styleUrls: ['./timestamp-log.component.scss']
})
export class TimestampLogComponent implements OnInit {
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
  latitude: number
  longitude: number
  timestampModel: TimestampModel = new TimestampModel()
  memberId = this.tokenService.getUser().member.memberId
  employeeModel: EmployeeModel = new EmployeeModel()
  constructor(private timestampService: TimestampService, private tokenService: TokenService, public datepipe: DatePipe, public translate: TranslateService,
    private modalService: NgbModal,
    private route: ActivatedRoute,
    private employeeService: EmployeeService
  ) {
    this.route.paramMap.subscribe(params => {
      if (params.get('memberId')) {
        this.memberId = params.get('memberId')!
        this.employeeService.getMemberById(this.tokenService.getSelectCompany().companyId, this.memberId).subscribe(result => {
          this.employeeModel = result
          this.getTimestamp()
        })
      }
    });

  }

  ngOnInit() {
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
    this.timestampService.getListsSearch(this.tokenService.getSelectCompany().companyId, this.employeeModel.company_employeeId,new Date(this.dateRange.start).toISOString(), new Date(this.dateRange.end).toISOString()).subscribe(result => {
      this.listTimeStampLog = result.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    })
  }

  selecteTime(item: TimestampModel) {
    this.timestampModel = item
  }

  openMap(content: any, item: TimestampModel) {
    this.timestampModel = item
    console.log(this.timestampModel)
    this.modalService.open(content, { centered: true, size: 'lg' });
  }


}
