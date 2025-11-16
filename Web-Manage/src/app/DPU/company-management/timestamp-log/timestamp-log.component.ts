import { Component, ElementRef, ViewChild, ViewEncapsulation } from '@angular/core';
import { SharedModule } from '../../../shared/shared.module';
import { SimplebarAngularModule } from 'simplebar-angular';
import { MaterialModuleModule } from '../../../material-module/material-module.module';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { TimestampService } from '../../services/timestamp.service';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { TokenService } from '../../../shared/services/token.service';
import { TimestampModel } from '../../models/timestamp.model';
import swal from 'sweetalert';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import moment from 'moment';
import { EmployeeModel } from '../../models/employee.model';
import { EmployeeService } from '../../services/employee.service';
import { GoogleMapsModule, MapMarker } from '@angular/google-maps';
@Component({
  selector: 'app-timestamp-log',
  templateUrl: './timestamp-log.component.html',
  standalone: true,
  imports: [CommonModule,
    SharedModule,
    TranslateModule,
    NgSelectModule,
    FormsModule,
    GoogleMapsModule, MapMarker,
    RouterModule,
    FlatpickrModule],
  styleUrls: ['./timestamp-log.component.css'],
  providers: [FlatpickrDefaults],
  encapsulation: ViewEncapsulation.None
})
export class TimestampLogComponent {
  public dateRange: { from: Date, to: Date } = { from: new Date(new Date().getFullYear(), new Date().getMonth(), 1), to: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0) };
  public options: any = {
    "autoApply": true,

    ranges: this.translate.currentLang == 'th' ? {
      'วันนี้': [moment(), moment()],
      '7 วันล่าสุด': [moment().subtract(6, 'days'), moment()],
      '30 วันล่าสุด': [moment().subtract(29, 'days'), moment()],
      'เดือนนี้': [moment().startOf('month'), moment().endOf('month')]
    } : {
      'Today': [moment(), moment()],
      'Last 7 Days': [moment().subtract(6, 'days'), moment()],
      'Last 30 Days': [moment().subtract(29, 'days'), moment()],
      'This Month': [moment().startOf('month'), moment().endOf('month')]
    },
    "locale": {
      "format": "DD/MM/YYYY",
      "separator": " - ",
      "applyLabel": "ตกลง",
      "cancelLabel": "ยกเลิก",
      "fromLabel": "จาก",
      "toLabel": "ถึง",
      "daysOfWeek": this.translate.instant("NameDayShort"),
      "monthNames": this.translate.instant("NameMonth"),
      "customRangeLabel": this.translate.instant("Range date"),
      "firstDay": 1,
      direction: 'daterange-center shadow'
    },

    "alwaysShowCalendars": true,
    "startDate": this.dateRange.from,
    "endDate": this.dateRange.to,
  };
  @ViewChild('closeModal') public childModal?: ElementRef;
  @ViewChild('modalDetail') public modalDetail?: ElementRef;
  action = "new";
  allSelected = false;
  someSelected = false;
  itemsList: TimestampModel[] = []
  filterList: TimestampModel[] = []
  selectModel?: TimestampModel
  empList: EmployeeModel[] = []
  empSelect = ""
  statusSelect = ""
  descName = 'engName'
  pageIndex = 0;
  center: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  zoom = 5;
  markerOptions: google.maps.MarkerOptions = { draggable: false };
  markerPositions: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
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

  _searchTerm = "";
  companyId = ""
  constructor(private timeService: TimestampService, public translate: TranslateService, private tokenService: TokenService, private employeeService: EmployeeService, private route: ActivatedRoute) {
    this.empSelect = this.route.snapshot.paramMap.get('company_employeeId') || "";
    this.companyId = this.tokenService.getSelectCompany().companyId;;
    this.getTimestamp()
    this.getEmp()
  }

  ngOnInit(): void {

  }

  getTimestamp() {
    this.pageIndex = 0;
    console.log(this.dateRange)
    this.timeService.getListsSearch(this.tokenService.getSelectCompany().companyId, this.empSelect, new Date(this.dateRange.from).toISOString(), new Date(this.dateRange.to).toISOString(), this.statusSelect).subscribe(result => {
      this.itemsList = result.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
      this.updatePagedItems()
    })
  }

  getEmp() {
    this.employeeService.getLists(this.companyId).subscribe(result => {
      this.empList = result
    })
  }

  searchTime() {
    console.log(this.dateRange)
  }

  filter(v: string) {
    return this.itemsList?.filter(
      (x) =>
        x.company_employeeId?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.timestampId?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.timestamp?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.locationName?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.getStatus().toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.timestamp.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.employee.getFullname().toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.employee.position.getName().toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.employee.department.getName().toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.employee.employeeId.toLowerCase().indexOf(v.toLowerCase()) !== -1
    );
  }

  delete(item: TimestampModel) {
    swal({
      title: "Are you sure?",
      text: "You won't be able to revert this!",
      icon: "warning",

      dangerMode: true,
      buttons: ["Cancel", "Yes,Delete it!"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.timeService.delete(this.companyId, item).subscribe(result => {
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.getTimestamp()
          })
        }

      });
  }

  new() {
    this.action = 'add'
    this.selectModel = new TimestampModel()
    this.selectModel.latitude = 0.00
    this.selectModel.longitude = 0.00
  }

  view(item: TimestampModel) {
    this.action = 'edit'
    this.selectModel = new TimestampModel(item, this.translate)
    console.log(this.selectModel)
  }

  approveTime(item: TimestampModel) {
    swal({
      title: "Are you sure?",
      text: "คุณต้องการบันทึกหรือไม่",
      icon: "warning",
      dangerMode: false,
      buttons: ["Cancel", "Confirm"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          item.timestampType = 1;
          this.timeService.update(this.companyId, item).subscribe(result => {
            console.log(result)
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.selectModel = undefined
            this.getTimestamp()
            this.childModal?.nativeElement.click()
          })

        }
      });
  }

  disapproveTime(item: TimestampModel) {
    swal({
      title: "Are you sure?",
      text: "คุณต้องการบันทึกหรือไม่",
      icon: "warning",
      dangerMode: false,
      buttons: ["Cancel", "Confirm"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          item.timestampType = 3;
          this.timeService.update(this.companyId, item).subscribe(result => {
            console.log(result)
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.selectModel = undefined
            this.getTimestamp()
            this.childModal?.nativeElement.click()
          })
        }
      });
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
            this.timeService.save(this.companyId, this.selectModel!).subscribe(result => {
              console.log(result)
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.getTimestamp()
              this.childModal?.nativeElement.click()
            })
          } else if (this.action == 'edit') {
            this.timeService.update(this.companyId, this.selectModel!).subscribe(result => {
              console.log(result)
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.getTimestamp()
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
}
