import { Component, OnInit } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { CompanyLocationModel } from 'src/app/shared/models/company-location.model';
import { CompanyModel } from 'src/app/shared/models/company.model';
import { CompanyLocationService } from 'src/app/shared/services/company-location.service';
import { CompanyService } from 'src/app/shared/services/company.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-contact-us',
  templateUrl: './contact-us.component.html',
  styleUrls: ['./contact-us.component.scss']
})
export class ContactUsComponent implements OnInit {

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
    private companyLocationService: CompanyLocationService,
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
    this.companyLocationService.getLists(this.tokenService.getSelectCompany().companyId).subscribe(result => {
      this.locationList = result
      if (this.locationList.length > 0) {
        this.longitude = Number(this.locationList[0].longitude)
        this.latitude = Number(this.locationList[0].latitude)
      }
      this.locationList.forEach(x => {
        this.markers.push({ latitude: Number(x.latitude), longitude: Number(x.longitude), data: x });
        this.latitude = Number(x.latitude)
        this.longitude = Number(x.longitude)
      })
    })
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
