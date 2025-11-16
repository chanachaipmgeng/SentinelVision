import { AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, Input, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { FullCalendarComponent } from "@fullcalendar/angular";
import { TranslateService } from '@ngx-translate/core';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { CalendarOptions } from '@fullcalendar/core'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import { NgbActiveModal, NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { TimestampService } from 'src/app/shared/services/timestamp.service';
import { DatePipe } from '@angular/common';
import { TimestampModel } from 'src/app/shared/models/timestamp.model';
import { AuthService } from 'src/app/shared/services/auth.service';
import { CompanyService } from 'src/app/shared/services/company.service';
import { MyHRConfigModel } from 'src/app/shared/models/myhr.models';
import { environment } from 'src/environments/environment';
import { ActivatedRoute } from '@angular/router';
import { CompanyModel } from 'src/app/shared/models/company.model';
@Component({
  selector: 'app-home-company',
  templateUrl: './home-company.component.html',
  styleUrls: ['./home-company.component.css']
})
export class HomeCompanyComponent implements OnInit {
  public dateRange: { start: Date, end: Date } = { start: new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate(), 0, 0, 0), end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, new Date().getDate(), 0, 0, 0) };
  public dateRangeCalendar: { start: Date, end: Date } = { start: new Date(new Date().getFullYear(), new Date().getMonth(), 1), end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 24) };
  @ViewChild('iframe', { static: false }) iframe: ElementRef;
  @ViewChild('container', { static: false }) container: ElementRef;
  wTime = 0;
  lTime = 0;
  oTime = 0;
  lateTime = 0;
  absent = 0;
  aTime = "0.00";
  isChecked: boolean = false;
  employeeModel: EmployeeModel = new EmployeeModel()
  companyModel: CompanyModel = this.tokenService.getSelectCompany()
  currentDate = new Date()
  token = "";
  @ViewChild("fullCalendar") fullCalendar: FullCalendarComponent | undefined;
  calendarOptions: CalendarOptions = {
    plugins: [dayGridPlugin, interactionPlugin],
    initialView: 'dayGridMonth',
    // height: 400,
    locale: this.translateService.currentLang == "th" ? "th" : "en",
    headerToolbar: {
      start: "title",
      center: "",
      end: "",
    },
    // eventClick: this.eventCalendarClick.bind(this),
    contentHeight: "auto",
    handleWindowResize: true,
    // dayMaxEvents: true,
    dayMaxEventRows:2
  };
  timeList: TimestampModel[] = []
  isSubEmp = false;
  constructor(private translateService: TranslateService, private employeeService: EmployeeService, private tokenService: TokenService, private changeDetectorRef: ChangeDetectorRef, private modalService: NgbModal, private timestampService: TimestampService, public datepipe: DatePipe, private auth: AuthService, private companyService: CompanyService, private route: ActivatedRoute) { }
  ngOnInit(): void {
    this.getDataEmp()
    this.getSub()
  }

  getDataEmp() {
    this.employeeService.getMemberById(this.companyModel.companyId!, this.tokenService.getUser().member.memberId).subscribe(result => {
      this.employeeModel = result
      this.getTimestamp()
      this.getTimestampCalendar()
    })
  }

  getTimestampCalendar() {
    this.timestampService.getListsSearch(this.tokenService.getSelectCompany().companyId, this.employeeModel.company_employeeId, new Date(this.dateRangeCalendar.start).toISOString(), new Date(this.dateRangeCalendar.end).toISOString()).subscribe(result => {
      // this.timeList = result.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
      let events: any = []
      result.forEach((x, i) => {
        events.push({
          id: x.timestampId,
          title: x.getStatus(),
          start: x.timestamp,
          backgroundColor: "#2962ff",
          borderColor: "#2962ff",
          textColor: "#ffffff"
        })


      })
      this.calendarOptions.events = events;
      this.changeDetectorRef.markForCheck();

    })
  }


  getTimestamp() {
    this.timestampService.getListsSearch(this.tokenService.getSelectCompany().companyId, this.employeeModel.company_employeeId, new Date(this.dateRange.start).toISOString(), new Date(this.dateRange.end).toISOString()).subscribe(result => {
      this.timeList = result.sort((a, b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 5)
      // this.changeDetectorRef.markForCheck();
    })
  }

  doCheck() {
    let html = document.getElementsByTagName('html')[0];
    this.isChecked = !this.isChecked;
    if (this.isChecked == true) {
      html.classList.add('dark-mode');
    } else {
      html.classList.remove('dark-mode');
    }
  }

  getSub() {
    this.employeeService.getSubordinateList(this.tokenService.getSelectCompany().companyId, this.tokenService.getUser().member.memberId).subscribe(result => {
      if (result.length > 0) {
        this.isSubEmp = true;
      }
    })
  }



}

@Component({
  selector: 'calendar-popup',
  template: `
  <div class="modal-header">
    <span class="text-primary m-0">เวลาการทำงาน</span>
    <button type="button" class="btn-close" aria-label="Close" (click)="activeModal.dismiss('Cross click')"></button>
  </div>
  <div class="modal-body">
    <p>{{ message }}</p>
  </div>
`,
})
export class InfoComponent {
  @Input() message = ""
  constructor(public activeModal: NgbActiveModal) {

  }
}
