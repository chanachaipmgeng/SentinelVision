import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, ElementRef, ViewChild } from '@angular/core';
import { NgSelectModule } from "@ng-select/ng-select";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { SharedModule } from "../../../../shared/shared.module";
import { PositionService } from "../../../services/position.service";
import { PositionModel } from "../../../models/position.model";
import { FormsModule } from "@angular/forms";
import swal from 'sweetalert';
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { ActivatedRoute } from "@angular/router";
import { TokenService } from "../../../../shared/services/token.service";
@Component({
  selector: 'app-position',
  standalone: true,
  imports: [
    CommonModule,
    SharedModule,
    TranslateModule,
    NgSelectModule,
    FormsModule,
    MatPaginator
  ],
  templateUrl: './position.component.html',
  styleUrl: './position.component.css'
})
export class PositionComponent {
  @ViewChild('closeModal') public childModal?: ElementRef;
  @ViewChild('modalDetail') public modalDetail?: ElementRef;
  allSelected = false;
  someSelected = false;
  companyId = ""
  itemsList: PositionModel[] = []
  filterList: PositionModel[] = [];
  selectModel: PositionModel = new PositionModel()
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
  constructor(private positionService: PositionService, private tokenService: TokenService, public translate: TranslateService) {
    this.companyId = this.tokenService.getSelectCompany().companyId;;
    this.getPosition()
  }

  ngOnInit(): void {
  }

  getPosition() {
    this.positionService.getLists(this.companyId).subscribe(result => {
      this.itemsList = result
      this.updatePagedItems()
    })
  }

  filter(v: string) {
    this.pageIndex = 0;
    return this.itemsList?.filter(
      (x) =>
        x.positionId?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.thName?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.engName?.toLowerCase().indexOf(v.toLowerCase()) !== -1
    );
  }

  delete(item: PositionModel) {
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
          this.positionService.delete(item).subscribe(result => {
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.getPosition()
          })
        }

      });
  }

  new() {
    this.isEdit = false
    this.selectModel = new PositionModel()
  }

  view(item: PositionModel) {
    this.isEdit = true;
    this.selectModel = new PositionModel(item)
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
            this.positionService.save(this.selectModel).subscribe(result => {
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.getPosition()
              this.getPosition()
              this.childModal?.nativeElement.click()
            })
          } else {
            this.positionService.update(this.selectModel).subscribe(result => {
              swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
              this.getPosition()
              this.getPosition()
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
      this.selectedItems.set(item.positionId, this.allSelected);
    });
    this.someSelected = this.itemsList.some(item => this.selectedItems.get(item.positionId));
  }

  onCheckboxChange(positionId: string) {
    const isSelected = this.selectedItems.get(positionId) || false;
    this.selectedItems.set(positionId, !isSelected);
    this.allSelected = this.itemsList.every(item => this.selectedItems.get(item.positionId));
    this.someSelected = this.itemsList.some(item => this.selectedItems.get(item.positionId));
  }

  deleteSelect() {
    let employeeInfo = '';
    this.selectedItems.forEach((isSelected, positionId) => {
      if (isSelected) {
        const item = this.itemsList.find(item => item.positionId === positionId);
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
          this.selectedItems.forEach((isSelected, positionId) => {
            if (isSelected) {
              const item = this.itemsList.find(item => item.positionId === positionId);
              if (item) {
                this.positionService.delete(item).subscribe(result => {
                  swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
                  this.getPosition();
                });
              }
            }
          });
        }
      });
  }

}
