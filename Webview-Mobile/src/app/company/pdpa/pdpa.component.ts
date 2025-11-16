import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { PdpaModel } from 'src/app/shared/models/pdpa.model';
import { PdpaService } from 'src/app/shared/services/pdpa.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { v4 as uuidv4 } from 'uuid';

@Component({
  selector: 'app-pdpa',
  templateUrl: './pdpa.component.html',
  styleUrls: ['./pdpa.component.scss']
})
export class PdpaComponent implements OnInit {

  versionName: string
  pdpaModel: PdpaModel
  lang:string
  checkBoxPdPa = false
  remoteIps = ""
  ipAddress: string;
  checkPdPaMenu: ""
  landingCheck=true
  constructor(
    private pdpaService: PdpaService,
    private router: Router,
    private tokenService: TokenService,
    private translateService:TranslateService,
    public datepipe: DatePipe,
    private http:HttpClient
  ) {
  }

  ngOnInit() {
    this.getPDPA();
    this.getIP();
  }

  getPDPA(){
    this.lang = this.translateService.currentLang
    this.pdpaService.getpdpaLatestVersion().subscribe( respons => {
      if(respons){
        this.pdpaService.getpdpaConsent(respons.version, this.tokenService.getUser().member.memberId).subscribe(result => {
          this.pdpaModel = respons
          if (result) {
            this.router.navigate(["/company/home-company"]);
          }else{
            this.landingCheck = false
          }
        })
      }
    }
    )
  }

  onSubmit() {
    let currentTime = new Date();
    let uuid = uuidv4();
    let dateTranfrom = this.datepipe.transform(
      currentTime,
      'yyyy-MM-dd HH:mm:ss'
    );
    let body = {
      consentId: uuid,
      version: this.pdpaModel.version,
      memberId: this.tokenService.getUser().member.memberId,
      consentDatetime: dateTranfrom,
      remoteIp: this.ipAddress,
    };
    this.pdpaService.consent(body).subscribe( result => {
      if(result) {
        this.router.navigate(["/company/home-company"]);
      }
    })
  }

  getIP()
  {
    fetch('https://api.ipify.org?format=json')
    .then(response => response.json())
    .then(data => {
      this.ipAddress = data.ip
        // console.log(data.ip);
    })
    .catch(error => {
        // console.log('Error:', error);
    });
  }
}
