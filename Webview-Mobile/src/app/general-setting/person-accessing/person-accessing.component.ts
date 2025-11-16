import { Component, OnInit } from '@angular/core';
import { DeviceModel } from 'src/app/shared/models/member.model';
import { MemberService } from 'src/app/shared/services/member.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-person-accessing',
  templateUrl: './person-accessing.component.html',
  styleUrls: ['./person-accessing.component.scss']
})
export class PersonAccessingComponent implements OnInit {

  device: DeviceModel

  constructor(
    private memberService: MemberService,
    private tokenService: TokenService
  ) { }

  ngOnInit() {

    this.getDeviceAccessList();
  }

  getDeviceAccessList(){
    this.memberService.getDeviceAccessList(this.tokenService.getUser().member.memberId).subscribe( result =>{
      this.device = result
    })
  }
}
