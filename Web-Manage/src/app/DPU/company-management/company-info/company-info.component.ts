import { CommonModule } from "@angular/common";
import { Component, ElementRef, ViewChild, ViewEncapsulation } from '@angular/core';
import { SharedModule } from "../../../shared/shared.module";
import { GoogleMapsModule, MapAdvancedMarker, MapInfoWindow } from '@angular/google-maps';
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
import { mountPlaceAutocomplete } from "../../../shared/utils/place-autocomplete";

@Component({
  selector: 'app-company-info',
  standalone: true,
  imports: [SharedModule, NgSelectModule, CommonModule, FormsModule, FileUploadModule, TranslateModule, NgSelectModule, GoogleMapsModule, MapAdvancedMarker],
  templateUrl: './company-info.component.html',
  styleUrl: './company-info.component.css',
  encapsulation: ViewEncapsulation.None
})
export class CompanyInfoComponent {
  @ViewChild(MapInfoWindow) infoWindow: MapInfoWindow | undefined;
  @ViewChild('placeAutocompleteHost', { static: false }) placeAutocompleteHost!: ElementRef<HTMLElement>;

  readonly mapId = environment.googleMapsMapId;
  center: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  zoom = 4;
  markerOptions: google.maps.marker.AdvancedMarkerElementOptions = { gmpDraggable: false };
  markerPositions: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  companyId = ""
  companyModel: CompanyModel = new CompanyModel()
  uploaderProfile: FileUploader | undefined;
  uploadErrorMsg: string = "";

  constructor(private router: Router, private route: ActivatedRoute, private comService: CompanyService, private tokenService: TokenService) {
    this.companyId = this.tokenService.getSelectCompany().companyId;
    this.getCompanyInfo()
    this.uploadConfig()
  }

  async ngAfterViewInit() {
    await this.initPlaceAutocomplete();
  }

  async initPlaceAutocomplete() {
    const host = this.placeAutocompleteHost?.nativeElement;
    if (!host) {
      console.error('Place autocomplete host element not found');
      return;
    }

    await mountPlaceAutocomplete(host, (place) => {
      this.companyModel.latitude = place.lat;
      this.companyModel.longitude = place.lng;
      if (place.address) {
        this.companyModel.address = place.address;
      }
      this.center = { lat: place.lat, lng: place.lng };
      this.markerPositions = this.center;
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
        this.companyModel.picture = res.filename
        swal(res.message, "บันทึกสำเร็จ", "success");

      } else {
        this.uploadErrorMsg = "cannot upload file.";
        swal("Opp!!", "ไม่สามารถอัพโหลดได้", "info");
      }
    };
  }

  get mapCenter(): google.maps.LatLngLiteral {
    return {
      lat: this.toCoord(this.companyModel.latitude, 13.7563),
      lng: this.toCoord(this.companyModel.longitude, 100.5018),
    };
  }

  changeMarker() {
    this.companyModel.latitude = this.toCoord(this.companyModel.latitude, 13.7563);
    this.companyModel.longitude = this.toCoord(this.companyModel.longitude, 100.5018);
    this.center = this.mapCenter;
    this.markerPositions = this.mapCenter;
  }

  addMarker(event: google.maps.MapMouseEvent) {
    if (!event.latLng) {
      return;
    }
    const lat = event.latLng.toJSON().lat;
    const lng = event.latLng.toJSON().lng;
    this.companyModel.latitude = lat;
    this.companyModel.longitude = lng;
    this.center = { lat, lng };
    this.markerPositions = { lat, lng };
  }

  getCompanyInfo() {
    this.comService.getById(this.companyId).subscribe(result => {
      this.companyModel = new CompanyModel(result);
      this.tokenService.saveSelectCompany(result);
      this.center = this.mapCenter;
      this.markerPositions = this.mapCenter;
    })
  }

  private toCoord(value: unknown, fallback: number): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
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
