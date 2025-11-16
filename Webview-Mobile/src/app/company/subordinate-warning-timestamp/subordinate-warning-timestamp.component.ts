import { DatePipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslateService } from '@ngx-translate/core';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import {
  DataModel,
  SubWarningTimeListModel,
} from 'src/app/shared/models/subodinate.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { NativeMobileService } from 'src/app/shared/services/native-mobile.service';
import { SubodinateService } from 'src/app/shared/services/subodinate.service';
import { TokenService } from 'src/app/shared/services/token.service';
import * as moment from 'moment';

@Component({
  selector: 'app-subordinate-warning-timestamp',
  templateUrl: './subordinate-warning-timestamp.component.html',
  styleUrls: ['./subordinate-warning-timestamp.component.scss'],
})
export class SubordinateWarningTimestampComponent implements OnInit {
  subWarningTimeList: SubWarningTimeListModel[] = [];
  employee: EmployeeModel = new EmployeeModel();
  memberIdParam: string = '';
  public dateRange: { start: Date; end: Date } = {
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 24),
  };
  public options: any = {
    autoApply: true,

    ranges:
      this.translate.currentLang == 'th'
        ? {
            วันนี้: [moment(), moment()],
            '7 วันล่าสุด': [moment().subtract(6, 'days'), moment()],
            '30 วันล่าสุด': [moment().subtract(29, 'days'), moment()],
            เดือนนี้: [moment().startOf('month'), moment().endOf('month')],
          }
        : {
            Today: [moment(), moment()],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
          },
    locale: {
      format: 'DD/MM/YYYY',
      separator: ' - ',
      applyLabel: 'ตกลง',
      cancelLabel: 'ยกเลิก',
      fromLabel: 'จาก',
      toLabel: 'ถึง',
      daysOfWeek: this.translate.instant('NameDayShort'),
      monthNames: this.translate.instant('NameMonth'),
      customRangeLabel: this.translate.instant('Range date'),
      firstDay: 1,
      direction: 'daterange-center shadow',
    },

    alwaysShowCalendars: true,
    startDate: this.dateRange.start,
    endDate: this.dateRange.end,
  };

  constructor(
    private subodinateService: SubodinateService,
    private tokenService: TokenService,
    private route: ActivatedRoute,
    private mobileService: NativeMobileService,
    private employeeService: EmployeeService,
    public datepipe: DatePipe,
    private modalService: NgbModal,
    private translate: TranslateService,
    private router: Router,
    private activatedRoute: ActivatedRoute
  ) {
    this.memberIdParam = this.route.snapshot.paramMap.get('memberId')!;
    this.activatedRoute.params.subscribe((params) => {
      //   public dateRange: { start: Date, end: Date } = { start: new Date(new Date().getFullYear(), new Date().getMonth(), 1), end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0) };
      if (params.startdate&&params.enddate) {
        const startdate = params.startdate.split('-').map(Number);
        const enddate = params.enddate.split('-').map(Number);
        this.dateRange = {
          start: new Date(startdate[0], startdate[1] - 1, startdate[2]),
          end: new Date(enddate[0], enddate[1] - 1, enddate[2]),
        };
        this.options.startDate =new Date(startdate[0], startdate[1] - 1, startdate[2])
        this.options.endDate =new Date(enddate[0], enddate[1] - 1, enddate[2])
      }
    });
  }

  ngOnInit() {
    this.getPersonalInfo();
    this.getWarningTimeListDay();

  }

  getPersonalInfo() {
    this.employeeService
      .getById(
        this.tokenService.getSelectCompany().companyId,
        this.memberIdParam
      )
      .subscribe((result) => {
        this.employee = result;
        // console.log("this.employeeModel" , this.employee)
      });
  }

  getWarningTimeListDay() {
    this.subodinateService
      .getsubWarningTimeList(
        this.tokenService.getSelectCompany().companyId,
        this.memberIdParam
      )
      .subscribe((result) => {
        this.subWarningTimeList = result;
        console.log('result = ', this.subWarningTimeList);
      });
  }

  public selectedDate(value: any, datepicker?: any) {
    // any object can be passed to the selected event and it will be passed back here
    datepicker.start = value.start;
    datepicker.end = value.end;

    // use passed valuable to update state
    this.dateRange.start = value.start;
    this.dateRange.end = value.end;

    // this.warningTimeFilter();
  }

  warningTimeFilter() {
    const startdate = this.datepipe
      .transform(this.dateRange.start, '2023-09-07')!
      .split('-')
      .join('');
    const enddate = this.datepipe
      .transform(this.dateRange.end, 'yyyy-MM-dd')!
      .split('-')
      .join('');
    return this.subWarningTimeList.filter(
      (x) =>
        x.swipeDate.split('-').join('') <= enddate &&
        x.swipeDate.split('-').join('') >= startdate
    );
  }

  goSubWarningTimeMap(data: DataModel) {
    this.router.navigate([
      '/company/sub-warning-timestamp-map',
      {
        data: JSON.stringify(data),
        startdate: this.datepipe.transform(this.dateRange.start, 'yyyy-MM-dd'),
        enddate: this.datepipe.transform(this.dateRange.end, 'yyyy-MM-dd'),
        path: '/company/subordinate-warning-timestamp/' + this.memberIdParam
  }]);
    // console.log('data : ', data);
  }
}
