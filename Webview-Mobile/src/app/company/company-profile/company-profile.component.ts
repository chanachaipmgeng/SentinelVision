import { Component, OnInit } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { CompanyLocationModel } from 'src/app/shared/models/company-location.model';
import { CompanyModel } from 'src/app/shared/models/company.model';
import { CompanyService } from 'src/app/shared/services/company.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-company-profile',
  templateUrl: './company-profile.component.html',
  styleUrls: ['./company-profile.component.scss']
})
export class CompanyProfileComponent implements OnInit {

  companyModel?: CompanyModel = new CompanyModel()
  locationList?: CompanyLocationModel[]
  markers: {
    latitude: number,
    longitude: number,
    data: CompanyLocationModel
  }[] = []
  longitude = 100.9502941;
  latitude = 13.5975159;

  locationSelect?: CompanyLocationModel
  constructor(private companyService: CompanyService,
    private tokenService: TokenService,
    private modalService: NgbModal) { }

  ngOnInit() {
    this.profileCompany()
    this.location()
  }

  profileCompany() {
    this.companyService.getById(this.tokenService.getSelectCompany().companyId).subscribe(result => {
      this.companyModel = result
    })
  }

  location() {
    // this.companyService.getLocationCompany(this.tokenService.getSelectCompany().companyId).subscribe(result => {
    //   this.locationList = result
    //   if (this.locationList.length > 0) {
    //     this.longitude = Number(this.locationList[0].lng)
    //     this.latitude = Number(this.locationList[0].lat)
    //   }
    //   this.locationList.forEach(x => {
    //     this.markers.push({ latitude: Number(x.lat), longitude: Number(x.lng), data: x });
    //     this.latitude = Number(x.lat)
    //     this.longitude = Number(x.lng)
    //   })
    // })
  }

  changeLoc(companyMaps: CompanyLocationModel) {
    this.longitude = Number(companyMaps.longitude)
    this.latitude = Number(companyMaps.latitude)
  }

  openDetail(content: any, companyMaps: CompanyLocationModel) {
    this.locationSelect = companyMaps
    this.modalService.open(content, { centered: true, size: 'lg' });
  }

}
