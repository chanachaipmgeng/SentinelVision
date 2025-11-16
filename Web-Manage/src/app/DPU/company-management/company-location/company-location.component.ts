import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, ElementRef, ViewChild, ViewEncapsulation } from '@angular/core';
import { SharedModule } from "../../../shared/shared.module";
import { NgSelectModule } from "@ng-select/ng-select";
import { CompanyLocationModel } from "../../models/company-location.model";
import { CompanyLocationService } from "../../services/company-location.service";
import { TokenService } from "../../../shared/services/token.service";
import swal from 'sweetalert';
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { FormsModule } from "@angular/forms";
import { RouterModule } from "@angular/router";
import { GoogleMap, GoogleMapsModule, MapInfoWindow, MapMarker } from "@angular/google-maps";
@Component({
  selector: 'app-company-location',
  standalone: true,
  imports: [CommonModule,
    SharedModule,
    TranslateModule,
    NgSelectModule,
    FormsModule,
    GoogleMapsModule, MapMarker
  ],
  templateUrl: './company-location.component.html',
  styleUrl: './company-location.component.css',
  encapsulation: ViewEncapsulation.None
})
export class CompanyLocationComponent {
  @ViewChild('searchBox', { static: false }) searchBoxElement!: ElementRef;
  @ViewChild(GoogleMap) map!: GoogleMap;
  @ViewChild(MapInfoWindow) infoWindow: MapInfoWindow | undefined;
  @ViewChild('closeModal') public childModal?: ElementRef;
  @ViewChild('modalDetail') public modalDetail?: ElementRef;
  action = "new";
  allSelected = false;
  someSelected = false;
  itemsList: CompanyLocationModel[] = []
  filterList: CompanyLocationModel[] = []
  selectModel: CompanyLocationModel = new CompanyLocationModel()
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
  center: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  zoom = 5;
  radius = 50;
  markerOptions: google.maps.MarkerOptions = { draggable: false };
  markerPositions: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  autocompleteInput: string = '';
  _searchTerm = "";
  companyId = ""
  adressType: string = 'geocode';

  @ViewChild('addresstext') addresstext: any;

  constructor(private comLocationService: CompanyLocationService, public translate: TranslateService, private tokenService: TokenService) {
    this.companyId = this.tokenService.getSelectCompany().companyId;;
    this.getLocation()
  }
  ngOnInit(): void {}

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
      this.selectModel.latitude =  place.geometry.location.lat()
      this.selectModel.longitude =  place.geometry.location.lng()
      this.selectModel.locationName = place.name!
      // this.center = {
      //   lat: place.geometry.location.lat(),
      //   lng: place.geometry.location.lng(),
      // };

      // this.markerPositions = this.center;
      // console.log(`📍 New Location: ${this.center.lat}, ${this.center.lng}`);
    });
  }

  getLocation() {
    this.comLocationService.getLists(this.companyId).subscribe(result => {
      this.itemsList = result
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
    this.selectModel = new CompanyLocationModel()
    this.selectModel.latitude = 0.00
    this.selectModel.longitude = 0.00
  }

  view(item: CompanyLocationModel) {
    this.action = 'edit'
    this.selectModel = new CompanyLocationModel(item)
    this.markerPositions = { lat: this.selectModel.latitude, lng: this.selectModel.longitude }
    console.log(this.selectModel)
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
              console.log(result)
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.getLocation()
              this.childModal?.nativeElement.click()
            })
          } else if (this.action == 'edit') {
            this.comLocationService.update(this.companyId, this.selectModel).subscribe(result => {
              console.log(result)
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
    this.markerPositions = { lat: this.selectModel.latitude, lng: this.selectModel.longitude }
  }

  addMarker(event: google.maps.MapMouseEvent, marker: MapMarker) {
    console.log(event)
    console.log(marker)
    this.selectModel.latitude = event.latLng!.toJSON().lat
    this.selectModel.longitude = event.latLng!.toJSON().lng
    this.markerPositions = { lat: event.latLng!.toJSON().lat, lng: event.latLng!.toJSON().lng }
    if (this.infoWindow && marker.title) {
      this.infoWindow.open(marker);
    }
  }
}
