import { Component, OnInit } from '@angular/core';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-dashboard-company',
  templateUrl: './dashboard-company.component.html',
  styleUrls: ['./dashboard-company.component.css'],
})
export class DashboardCompanyComponent implements OnInit {
  public daterange: any = {};
  historyLink = '/company/timestamp-log/0';

  public options: any = {
    locale: { format: 'DD-MM-YYYY', direction: 'daterange-center shadow' },
    alwaysShowCalendars: false,
  };

  constructor(private tokenService: TokenService) {}

  ngOnInit(): void {
    const memberId = this.tokenService.getUser()?.member?.memberId;
    if (memberId) {
      this.historyLink = `/company/timestamp-log/${memberId}`;
    }
  }

  public selectedDate(value: any, datepicker?: any) {
    datepicker.start = value.start;
    datepicker.end = value.end;
    this.daterange.start = value.start;
    this.daterange.end = value.end;
    this.daterange.label = value.label;
  }
}
