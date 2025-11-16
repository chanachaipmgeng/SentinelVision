import { Component, ElementRef, ViewChild } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { CompanyModel } from '../../models/company.model';
import swal from 'sweetalert';
import { CompanyService } from '../../services/company.service';
import { MatPaginator } from '@angular/material/paginator';
import { FormsModule } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';
import { CommonModule } from '@angular/common';
import { FileUploadModule } from 'ng2-file-upload';
import { FileItem, FileUploader, ParsedResponseHeaders } from "ng2-file-upload";
import { environment } from '../../../../environments/environment';
import { TokenService } from '../../../shared/services/token.service';

@Component({
  selector: 'app-company-manage',
  standalone: true,
  imports: [
    CommonModule,
    SharedModule,
    TranslateModule,
    NgSelectModule,
    FormsModule,
    MatPaginator,
    RouterModule,
    FileUploadModule
  ],
  templateUrl: './company-manage.component.html',
  styleUrl: './company-manage.component.css',
})
export class CompanyManageComponent {
  @ViewChild('closeModal') public childModal?: ElementRef;
  @ViewChild('modalDetail') public modalDetail?: ElementRef;
  action = "new";
  allSelected = false;
  someSelected = false;
  itemsList: CompanyModel[] = []
  filterList: CompanyModel[] = []
  selectModel: CompanyModel = new CompanyModel()
  selectedItems = new Map<string, boolean>();
  empList: CompanyModel[] = []
  descName = 'engName'
  pageIndex = 0;
  uploaderProfile: FileUploader | undefined;
  uploadErrorMsg: string = "";
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
  constructor(private comService: CompanyService, public translate: TranslateService, private tokenService: TokenService) {
    this.uploadConfig()
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
        this.selectModel.picture = res.filename
        swal(res.message, "บันทึกสำเร็จ", "success");

      } else {
        this.uploadErrorMsg = "cannot upload file.";
        swal("Opp!!", "ไม่สามารถอัพโหลดได้", "info");
      }
    };
  }

  ngOnInit(): void {
    this.comService.getLists().subscribe(result => {
      this.itemsList = result
      this.updatePagedItems()
    })
  }

  filter(v: string) {
    return this.itemsList?.filter(
      (x) =>
        x.companyId?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.companyName?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.companyCode?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.companyInfo?.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.address.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.ownerName.toLowerCase().indexOf(v.toLowerCase()) !== -1 ||
        x.getStatus().toLowerCase().indexOf(v.toLowerCase()) !== -1
    );
  }

  delete(item: CompanyModel) {
    swal({
      title: "Are you sure?",
      text: "You won't be able to revert this!",
      icon: "warning",

      dangerMode: true,
      buttons: ["Cancel", "Yes,Delete it!"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.comService.delete(item).subscribe(result => {
            swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
            this.ngOnInit()
          })
        }

      });
  }

  new() {
    this.action = 'add'
    this.selectModel = new CompanyModel()
    this.selectModel.status = 1;
    this.selectModel.address = "";
    this.selectModel.latitude = 0.00
    this.selectModel.longitude = 0.00
    this.selectModel.picture = ""
  }

  view(item: CompanyModel) {
    this.action = 'edit'
    this.selectModel = new CompanyModel(item)
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
            this.comService.save(this.selectModel).subscribe(result => {
              console.log(result)
              swal("Save Success!!", "บันทึกข้อมูลสมาชิก", "success");
              this.ngOnInit()
              this.childModal?.nativeElement.click()
            })
          } else if (this.action == 'edit') {
            this.comService.update(this.selectModel).subscribe(result => {
              console.log(result)
              swal("Update Success!!", "บันทึกข้อมูลสมาชิก", "success");
              this.ngOnInit()
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
      this.selectedItems.set(item.companyId, this.allSelected);
    });
    this.someSelected = this.itemsList.some(item => this.selectedItems.get(item.companyId));
  }

  onCheckboxChange(companyId: string) {
    const isSelected = this.selectedItems.get(companyId) || false;
    this.selectedItems.set(companyId, !isSelected);
    this.allSelected = this.itemsList.every(item => this.selectedItems.get(item.companyId));
    this.someSelected = this.itemsList.some(item => this.selectedItems.get(item.companyId));
  }

  deleteSelect() {
    let employeeInfo = '';
    this.selectedItems.forEach((isSelected, companyId) => {
      if (isSelected) {
        const item = this.itemsList.find(item => item.companyId === companyId);
        if (item) {
          employeeInfo += `${this.translate.instant('บริษัท')}: ${item.companyName}\n`;
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
          this.selectedItems.forEach((isSelected, companyId) => {
            if (isSelected) {
              const item = this.itemsList.find(item => item.companyId === companyId);
              if (item) {
                this.comService.delete(item).subscribe(result => {
                  swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
                  this.ngOnInit();
                });
              }
            }
          });
        }
      });
  }

  adjustSelect(status: number) {
    let title = "Are you sure?"
    let employeeInfo = ''; // ตัวแปรสำหรับเก็บข้อมูลพนักงาน
    this.selectedItems.forEach((isSelected, memberId) => {
      if (isSelected) {
        const company = this.itemsList.find(company => company.companyId === memberId);
        if (company) {
          employeeInfo += `${this.translate.instant('Fullname')}: ${company.companyName}\n`;
        }
      }
    });
    swal({
      title: title,
      text: employeeInfo,
      icon: "warning",
      dangerMode: false,
      buttons: ["Cancel", "Confirm"],
    })
      .then((willDelete: any) => {
        if (willDelete) {
          this.selectedItems.forEach((isSelected, companyId) => {
            if (isSelected) {
              const company = this.itemsList.find(company => company.companyId === companyId);
              if (company) {
                company.status = status
                this.comService.update(company).subscribe(result => {
                  swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
                  this.ngOnInit();
                });
              }
            }
          });
        }

      });
  }

}
