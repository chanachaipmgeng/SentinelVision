import { CommonModule } from "@angular/common";
import { Component, ElementRef, ViewChild, ViewEncapsulation } from '@angular/core';
import { SharedModule } from "../../../shared/shared.module";
import { NgSelectModule } from "@ng-select/ng-select";
import { CompanyLocationModel } from "../../models/company-location.model";
import { CompanyLocationService } from "../../services/company-location.service";
import { TokenService } from "../../../shared/services/token.service";
import swal from 'sweetalert';
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { FormsModule } from "@angular/forms";
import { GoogleMap, GoogleMapsModule, MapAdvancedMarker, MapInfoWindow } from "@angular/google-maps";
import { environment } from "../../../../environments/environment";
import { mountPlaceAutocomplete } from "../../../shared/utils/place-autocomplete";

@Component({
  selector: 'app-company-location',
  standalone: true,
  imports: [CommonModule,
    SharedModule,
    TranslateModule,
    NgSelectModule,
    FormsModule,
    GoogleMapsModule, MapAdvancedMarker
  ],
  templateUrl: './company-location.component.html',
  styleUrl: './company-location.component.css',
  encapsulation: ViewEncapsulation.None
})
export class CompanyLocationComponent {
  @ViewChild('placeAutocompleteHost', { static: false }) placeAutocompleteHost!: ElementRef<HTMLElement>;
  @ViewChild(GoogleMap) map!: GoogleMap;
  @ViewChild(MapInfoWindow) infoWindow: MapInfoWindow | undefined;
  @ViewChild('closeModal') public childModal?: ElementRef;
  @ViewChild('modalDetail') public modalDetail?: ElementRef;
  action = "new";
  allSelected = false;
  someSelected = false;
  itemsList: CompanyLocationModel[] = []
  filterList: CompanyLocationModel[] = []
  selectModel: CompanyLocationModel;
  empList: CompanyLocationModel[] = []
  selectedItems = new Map<string, boolean>();
  descName = 'engName'
  pageIndex = 0;
  get searchTerm(): string {
    return this._searchTerm;
  }
  set searchTerm(val: string) {
    this.pageIndex = 0;
    this.allSelected = false
    this._searchTerm = val;
    if (val != '') {
      this.filterList = this.filter(val);
    } else {
      this.updatePagedItems()
    }
  }
  readonly mapId = environment.googleMapsMapId;
  center: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  zoom = 5;
  radius = 50;
  markerOptions: google.maps.marker.AdvancedMarkerElementOptions = { gmpDraggable: false };
  markerPositions: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  _searchTerm = "";
  companyId = ""

  constructor(private comLocationService: CompanyLocationService, public translate: TranslateService, private tokenService: TokenService) {
    this.selectModel = new CompanyLocationModel(undefined, this.translate);
    this.companyId = this.tokenService.getSelectCompany().companyId;
    this.getLocation()
  }
  ngOnInit(): void {}

  async initPlaceAutocomplete() {
    const host = this.placeAutocompleteHost?.nativeElement;
    if (!host) {
      return;
    }

    await mountPlaceAutocomplete(host, (place) => {
      this.selectModel.latitude = place.lat;
      this.selectModel.longitude = place.lng;
      if (place.name) {
        this.selectModel.locationName = place.name;
      }
      this.center = { lat: place.lat, lng: place.lng };
      this.markerPositions = this.center;
    });
  }

  private schedulePlaceAutocomplete() {
    setTimeout(() => void this.initPlaceAutocomplete(), 150);
  }

  get mapCenter(): google.maps.LatLngLiteral {
    return {
      lat: this.toCoord(this.selectModel.latitude, 13.7563),
      lng: this.toCoord(this.selectModel.longitude, 100.5018),
    };
  }

  getLocation() {
    this.comLocationService.getLists(this.companyId).subscribe(result => {
      // Service already maps with TranslateService — do not rebuild without it
      // (getStatus() needs translateService.instant).
      this.itemsList = result || [];
      this.updatePagedItems()
    })
  }

  filter(v: string) {
    return this.itemsList?.filter(
      (x) =>
        x.locationId?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.locationName?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.getStatus().toLowerCase().indexOf(v.toLowerCase()) !== -1
    );
  }

  delete(item: CompanyLocationModel) {
    swal({
      title: "Are you sure?",
      text: "You won't be able to revert this!",
      icon: "warning",

      dangerMode: true,
      buttons: ["Cancel", "Yes,Delete it!"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.comLocationService.delete(this.companyId, item).subscribe(result => {
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.getLocation()
          })
        }

      });
  }

  new() {
    this.action = 'add'
    this.selectModel = new CompanyLocationModel(undefined, this.translate)
    this.selectModel.latitude = 13.7563
    this.selectModel.longitude = 100.5018
    this.center = this.mapCenter
    this.markerPositions = this.mapCenter
    this.schedulePlaceAutocomplete()
  }

  view(item: CompanyLocationModel) {
    this.action = 'edit'
    this.selectModel = new CompanyLocationModel(item, this.translate)
    this.center = this.mapCenter
    this.markerPositions = this.mapCenter
    this.schedulePlaceAutocomplete()
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
        if (willDelete) {
          if (this.action == 'add') {
            this.comLocationService.save(this.companyId, this.selectModel).subscribe(result => {
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.getLocation()
              this.childModal?.nativeElement.click()
            })
          } else if (this.action == 'edit') {
            this.comLocationService.update(this.companyId, this.selectModel).subscribe(result => {
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.getLocation()
              this.childModal?.nativeElement.click()
            })
          }

        }

      });


  }

  updatePagedItems() {
    const startIndex = this.pageIndex * 10;
    const endIndex = startIndex + 10;
    this.filterList = this.itemsList.slice(startIndex, endIndex);
  }

  toggleAll(event: any) {
    this.allSelected = event.target.checked;
    this.selectedItems.clear();
    this.itemsList.forEach(item => {
      this.selectedItems.set(item.locationId, this.allSelected);
    });
    this.someSelected = this.itemsList.some(item => this.selectedItems.get(item.locationId));
  }

  onCheckboxChange(locationId: string) {
    const isSelected = this.selectedItems.get(locationId) || false;
    this.selectedItems.set(locationId, !isSelected);
    this.allSelected = this.itemsList.every(item => this.selectedItems.get(item.locationId));
    this.someSelected = this.itemsList.some(item => this.selectedItems.get(item.locationId));
  }

  deleteSelect() {
    let employeeInfo = '';
    this.selectedItems.forEach((isSelected, locationId) => {
      if (isSelected) {
        const item = this.itemsList.find(item => item.locationId === locationId);
        if (item) {
          employeeInfo += `${this.translate.instant('ชื่อตำแหน่ง')}: ${item.locationName}\n`;
        }
      }
    });

    swal({
      title: "Are you sure?",
      text: employeeInfo,
      icon: "warning",
      dangerMode: true,
      buttons: ["Cancel", "Yes, Delete it!"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.selectedItems.forEach((isSelected, locationId) => {
            if (isSelected) {
              const item = this.itemsList.find(item => item.locationId === locationId);
              if (item) {
                this.comLocationService.delete(this.companyId, item).subscribe(result => {
                  swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
                  this.getLocation();
                });
              }
            }
          });
        }
      });
  }

  changeMarker() {
    this.selectModel.latitude = this.toCoord(this.selectModel.latitude, 13.7563);
    this.selectModel.longitude = this.toCoord(this.selectModel.longitude, 100.5018);
    this.center = this.mapCenter;
    this.markerPositions = this.mapCenter;
  }

  addMarker(event: google.maps.MapMouseEvent) {
    if (!event.latLng) {
      return;
    }
    const lat = event.latLng.toJSON().lat;
    const lng = event.latLng.toJSON().lng;
    this.selectModel.latitude = lat;
    this.selectModel.longitude = lng;
    this.center = { lat, lng };
    this.markerPositions = { lat, lng };
  }

  private toCoord(value: unknown, fallback: number): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
}
