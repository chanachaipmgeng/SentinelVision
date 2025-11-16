import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, ElementRef, ViewChild, ViewEncapsulation } from '@angular/core';
import { SharedModule } from "../../../shared/shared.module";
import { GoogleMapsModule, MapInfoWindow, MapMarker } from '@angular/google-maps';
import { NgSelectModule } from "@ng-select/ng-select";
import { ActivatedRoute, Router } from "@angular/router";
import { TokenService } from "../../../shared/services/token.service";
import { CompanyService } from "../../services/company.service";
import { CompanyModel } from "../../models/company.model";
import { FormsModule } from "@angular/forms";
import { FileUploadModule } from 'ng2-file-upload';
import { FileItem, FileUploader, ParsedResponseHeaders } from "ng2-file-upload";
import { TranslateModule } from '@ngx-translate/core';
import swal from 'sweetalert';
import { environment } from "../../../../environments/environment";
@Component({
  selector: 'app-company-info',
  standalone: true,
  imports: [SharedModule, NgSelectModule, CommonModule, FormsModule, FileUploadModule, TranslateModule, NgSelectModule, GoogleMapsModule, MapMarker],
  templateUrl: './company-info.component.html',
  styleUrl: './company-info.component.css',
  encapsulation: ViewEncapsulation.None
})
export class CompanyInfoComponent {
  @ViewChild(MapInfoWindow) infoWindow: MapInfoWindow | undefined;
  center: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  zoom = 4;
  markerOptions: google.maps.MarkerOptions = { draggable: false };
  markerPositions: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  companyId = ""
  companyModel: CompanyModel = new CompanyModel()
  uploaderProfile: FileUploader | undefined;
  uploadErrorMsg: string = "";
  @ViewChild('searchBox', { static: false }) searchBoxElement!: ElementRef;
  constructor(private router: Router, private route: ActivatedRoute, private comService: CompanyService, private tokenService: TokenService) {
    this.companyId = this.tokenService.getSelectCompany().companyId;
    this.getCompanyInfo()
    this.uploadConfig()
  }

  async ngAfterViewInit() {
    // await this.loadGoogleMapsAPI();
    this.initAutocomplete();
  }

  initAutocomplete() {
    if (!this.searchBoxElement || !this.searchBoxElement.nativeElement) {
      console.error("❌ SearchBox element not found!");
      return;
    }

    const input = this.searchBoxElement.nativeElement;
    const searchBox = new google.maps.places.SearchBox(input);

    searchBox.addListener('places_changed', () => {
      const places = searchBox.getPlaces();
      if (!places || places.length === 0) return;

      const place = places[0];
      if (!place.geometry || !place.geometry.location) return;
      this.companyModel.latitude = place.geometry.location.lat()
      this.companyModel.longitude = place.geometry.location.lng()
      // this.center = {
      //   lat: place.geometry.location.lat(),
      //   lng: place.geometry.location.lng(),
      // };

      // this.markerPositions = this.center;
      // console.log(`📍 New Location: ${this.center.lat}, ${this.center.lng}`);
    });
  }

  uploadConfig() {
    this.uploaderProfile = new FileUploader({
      url: environment.baseUrl + "/api/upload-image",
      isHTML5: true,
      authToken: this.tokenService.getToken()!,
    });

    this.uploaderProfile.onAfterAddingFile = (fileItem: FileItem) => {
      fileItem.withCredentials = false;
      this.uploadErrorMsg = "";

      while (this.uploaderProfile!.queue.length > 1) {
        this.uploaderProfile!.queue[0].remove();
      }

      if (fileItem.file.size > 5000000) {
        this.uploadErrorMsg = "maximum file size 5mb.";
        swal("Opp!!", "ไม่สามารถอัพโหลดได้", "info");
        fileItem.isCancel = true;
        return;
      }

      if (fileItem.file.type!.indexOf("image") === -1) {
        this.uploadErrorMsg = "please upload image only.";
        swal("Opp!!", "ไม่สามารถอัพโหลดได้", "info");
        fileItem.isCancel = true;
        return;
      }

      fileItem.upload();
    };

    this.uploaderProfile.onCompleteItem = (
      item: FileItem,
      response: string,
      status: number,
      headers: ParsedResponseHeaders
    ) => {
      if (item.isSuccess) {
        const res = JSON.parse(response);
        console.log("res", res);
        this.companyModel.picture = res.filename
        swal(res.message, "บันทึกสำเร็จ", "success");

      } else {
        this.uploadErrorMsg = "cannot upload file.";
        swal("Opp!!", "ไม่สามารถอัพโหลดได้", "info");
      }
    };
  }

  changeMarker() {
    this.markerPositions = { lat: this.companyModel.latitude, lng: this.companyModel.longitude }
  }

  addMarker(event: google.maps.MapMouseEvent, marker: MapMarker) {
    console.log(event)
    console.log(marker)
    this.companyModel.latitude = event.latLng!.toJSON().lat
    this.companyModel.longitude = event.latLng!.toJSON().lng
    this.markerPositions = { lat: event.latLng!.toJSON().lat, lng: event.latLng!.toJSON().lng }
    if (this.infoWindow && marker.title) {
      this.infoWindow.open(marker);
    }
  }

  getCompanyInfo() {
    this.comService.getById(this.companyId).subscribe(result => {
      ;
      this.companyModel = result
      this.tokenService.saveSelectCompany(result);
      console.log("companyModel", this.companyModel)
    })
  }

  reset() {
    this.getCompanyInfo()
  }

  save() {
    swal({
      title: "Are you sure?",
      text: "คุณต้องการบันทึกหรือไม่",
      icon: "warning",
      dangerMode: false,
      buttons: ["Cancel", "Confirm"],
    })
      .then((willDelete: any) => {
        this.comService.update(this.companyModel).subscribe(result => {
          swal("Update Success!!", "บันทึกข้อมูลสมาชิก", "success");
          this.getCompanyInfo()
        })

      });
  }
}
