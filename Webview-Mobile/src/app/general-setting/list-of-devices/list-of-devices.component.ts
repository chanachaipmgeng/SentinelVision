import { Component, OnInit } from '@angular/core';
import { DeviceModel } from 'src/app/shared/models/member.model';
import { MemberService } from 'src/app/shared/services/member.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-list-of-devices',
  templateUrl: './list-of-devices.component.html',
  styleUrls: ['./list-of-devices.component.scss']
})
export class ListOfDevicesComponent implements OnInit {

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
      console.log("werwer", result)
    })
  }

}
