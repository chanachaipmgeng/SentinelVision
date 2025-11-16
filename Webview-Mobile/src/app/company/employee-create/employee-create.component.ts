import { Component, OnInit } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { EmployeeModel } from 'src/app/shared/models/employee.model';
import { CompanyService } from 'src/app/shared/services/company.service';
import { EmployeeService } from 'src/app/shared/services/employee.service';
import { TokenService } from 'src/app/shared/services/token.service';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { FileItem, FileUploader } from 'ng2-file-upload';
import { Router } from '@angular/router';
import { DepartmentModel } from 'src/app/shared/models/department.model';
import { PositionModel } from 'src/app/shared/models/position.model';


@Component({
  selector: 'app-employee-create',
  templateUrl: './employee-create.component.html',
  styleUrls: ['./employee-create.component.css']
})
export class EmployeeCreateComponent implements OnInit {

  hideUploandImg = true
  pictureUrl = ""
  uploader: FileUploader = new FileUploader({})
  profilePhotoFileName = ""
  profilePhotoError = false

  email = ""
  firstname = ""
  lastname = ""
  mobile = ""
  sex = 2
  password = ""
  confirmPassword = ""
  birthdate = ""
  idCard = ""
  passport = ""
  position = ""
  department = ""
  branch = ""
  boss = ""
  lagacyCode: ""
  taxid: ""

  departmentModel: DepartmentModel[] = []
  positionModel: PositionModel[] = []
  employeeList: EmployeeModel[] = []

  constructor(
    private modalService: NgbModal,
    private employeeService: EmployeeService,
    private companyService: CompanyService,
    private tokenService: TokenService,
    private router: Router
  ) {

    // this.companyService.getListBranch(this.tokenService.getSelectCompany().companyId).subscribe(result => {
    //   this.branchModel = result
    //   console.log("getListBranch", result)
    // })
    // this.companyService.getListDepartment(this.tokenService.getSelectCompany().companyId).subscribe(result => {
    //   this.departmentModel = result
    //   console.log("getListDepartment", result)
    // })
    // this.companyService.getListPosition(this.tokenService.getSelectCompany().companyId).subscribe(result => {
    //   this.positionModel = result
    //   console.log("getListPosition", result)
    // })
    // this.employeeService.getEmpList(this.tokenService.getSelectCompany().companyId).subscribe(response => {
    //   this.employeeList = response
    //   console.log("Boss", response)
    // })
    // this.setUpload()
  }

  ngOnInit() {
    console.log("UserName", this.tokenService.getUser())
  }

  showHideUploandImg() {
    this.hideUploandImg = !this.hideUploandImg
    if (this.hideUploandImg) {
      this.profilePhotoFileName = this.profilePhotoFileName
    }
  }
  setUpload() {
    this.uploader.onAfterAddingFile = (fileItem: FileItem) => {
      console.log("0000", fileItem)
      fileItem.withCredentials = false;
      while (this.uploader.queue.length > 1) {
        this.uploader.queue[0].remove();
      }
      if (fileItem.file.size > 5000000) {
        const modalRef = this.modalService.open(AlertComponent, { centered: true })
        modalRef.componentInstance.message = "maximum file size 5mb.";
        this.profilePhotoFileName = this.profilePhotoFileName
        console.log(this.profilePhotoFileName)
        this.profilePhotoError = true
        fileItem.isCancel = true;
        return;
      } else if (fileItem.file.type.indexOf("image") === -1) {
        const modalRef = this.modalService.open(AlertComponent, { centered: true })
        modalRef.componentInstance.message = "please upload image only.";
        this.profilePhotoFileName = this.profilePhotoFileName

        this.profilePhotoError = true
        fileItem.isCancel = true;
        return;
      } else {
        this.profilePhotoError = false
      }
    };
  }
  onFileSelected(event: any) {
    const file = event.target.files[0];
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      if (reader.result) {
        this.profilePhotoFileName = reader.result.toString()
        // console.log("this.profilePhotoFileName" , this.profilePhotoFileName)
      }
    };
  }
  isUpdateDisabled() {
    if (!this.email || !this.firstname || !this.lastname || this.profilePhotoError
      || !this.password || !this.confirmPassword || !this.branch
      || !this.lagacyCode || this.confirmPassword != this.password
    ) {
      return true
    } else {
      return false
    }
  }
  submit() {
    const body = new EmployeeModel()
    const modalRef = this.modalService.open(AlertComponent, { centered: true })
    modalRef.componentInstance.message = "Do you want to confirm?"
    modalRef.componentInstance.confirmModal = true
    modalRef.result.then(respone => {

      this.employeeService.save(body, this.tokenService.getSelectCompany().companyId).subscribe(
        (response) => {
          if (response.success == true) {

          } else {
            const modalRef = this.modalService.open(AlertComponent, { centered: true })
            modalRef.componentInstance.message = "STATUS.Fail"
          }
        }, error => {
          const modalRef = this.modalService.open(AlertComponent, { centered: true })
          modalRef.componentInstance.message = "STATUS.Fail"
        }
      )
    })


  }




  PassWord: boolean = false;
  showConfirmPass: boolean = false;
  checkOPeror = false

  showPassWord(buttonName: string) {

    if (buttonName == "passWord") {
      this.PassWord = !this.PassWord;
    }
    if (buttonName == "confirm") {
      this.showConfirmPass = !this.showConfirmPass;
    }
  }



}
