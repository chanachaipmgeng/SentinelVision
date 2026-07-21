import { Component, OnInit } from '@angular/core';
import { NativeMobileService } from 'src/app/shared/services/native-mobile.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-staticfooter',
  templateUrl: './staticfooter.component.html',
  styleUrls: ['./staticfooter.component.scss'],
})
export class StaticfooterComponent implements OnInit {
  historyLink = '/company/timestamp-log/0';

  constructor(
    private mobileService: NativeMobileService,
    private tokenService: TokenService,
  ) {}

  ngOnInit(): void {
    const memberId = this.tokenService.getUser()?.member?.memberId;
    if (memberId) {
      this.historyLink = `/company/timestamp-log/${memberId}`;
    }
  }
}
