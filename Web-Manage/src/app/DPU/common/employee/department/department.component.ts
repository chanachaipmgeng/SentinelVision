import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, ElementRef, ViewChild } from '@angular/core';
import { NgSelectModule } from "@ng-select/ng-select";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { SharedModule } from "../../../../shared/shared.module";
import { DepartmentService } from "../../../services/department.service";
import { DepartmentModel } from "../../../models/department.model";
import { FormsModule } from "@angular/forms";
import swal from 'sweetalert';
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { ActivatedRoute } from "@angular/router";
import { TokenService } from "../../../../shared/services/token.service";
@Component({
  selector: 'app-department',
  standalone: true,
  imports: [
    CommonModule,
    SharedModule,
    TranslateModule,
    NgSelectModule,
    FormsModule,
    MatPaginator
  ],
  templateUrl: './department.component.html',
  styleUrl: './department.component.css'
})
export class DepartmentComponent {
  @ViewChild('closeModal') public childModal?: ElementRef;
  @ViewChild('modalDetail') public modalDetail?: ElementRef;
  allSelected = false;
  someSelected = false;
  companyId = ""
  itemsList: DepartmentModel[] = []
  filterList: DepartmentModel[] = [];
  selectModel: DepartmentModel = new DepartmentModel()
  selectedItems = new Map<string, boolean>();
  pageIndex = 0;
  isEdit = false;
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
  constructor(private departmentService: DepartmentService, private tokenService: TokenService, public translate: TranslateService) {
    this.companyId = this.tokenService.getSelectCompany().companyId;;
    this.getDepartment()
  }

  getDepartment() {
    this.departmentService.getLists(this.companyId).subscribe(result => {
      this.itemsList = result
      this.updatePagedItems()
    })
  }

  filter(v: string) {
    this.pageIndex = 0;
    return this.itemsList?.filter(
      (x) =>
        x.departmentId?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.thName?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.engName?.toLowerCase().indexOf(v.toLowerCase()) !== -1
    );
  }

  delete(item: DepartmentModel) {
    swal({
      title: "Are you sure?",
      text: "You won't be able to revert this!",
      icon: "warning",
      timer: 1000,
      dangerMode: true,
      buttons: ["Cancel", "Yes,Delete it!"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.departmentService.delete(item).subscribe(result => {
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.getDepartment()
          })
        }

      });
  }

  new() {
    this.isEdit = false
    this.selectModel = new DepartmentModel()
  }

  view(item: DepartmentModel) {
    this.isEdit = true;
    this.selectModel = new DepartmentModel(item)
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
          this.selectModel.companyId = this.companyId
          if (!this.isEdit) {
            this.departmentService.save(this.selectModel).subscribe(result => {
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.getDepartment()
              this.childModal?.nativeElement.click()
            })
          } else {
            this.departmentService.update(this.selectModel).subscribe(result => {
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.getDepartment()
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
      this.selectedItems.set(item.departmentId, this.allSelected);
    });
    this.someSelected = this.itemsList.some(item => this.selectedItems.get(item.departmentId));
  }

  onCheckboxChange(departmentId: string) {
    const isSelected = this.selectedItems.get(departmentId) || false;
    this.selectedItems.set(departmentId, !isSelected);
    this.allSelected = this.itemsList.every(item => this.selectedItems.get(item.departmentId));
    this.someSelected = this.itemsList.some(item => this.selectedItems.get(item.departmentId));
  }

  deleteSelect() {
    let employeeInfo = '';
    this.selectedItems.forEach((isSelected, departmentId) => {
      if (isSelected) {
        const item = this.itemsList.find(item => item.departmentId === departmentId);
        if (item) {
          employeeInfo += `${this.translate.instant('ชื่อตำแหน่ง')}: ${item.getName()}\n`;
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
          this.selectedItems.forEach((isSelected, departmentId) => {
            if (isSelected) {
              const item = this.itemsList.find(item => item.departmentId === departmentId);
              if (item) {
                this.departmentService.delete(item).subscribe(result => {
                  swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
                  this.getDepartment();
                });
              }
            }
          });
        }
      });
  }

}
