import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import {
  DataModel,
  SubWarningDailyModel,
  SubWarningModel,
} from 'src/app/shared/models/subodinate.model';
import { SubodinateService } from 'src/app/shared/services/subodinate.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-emp-warning-time',
  templateUrl: './emp-warning-time.component.html',
  styleUrls: ['./emp-warning-time.component.scss'],
})
export class EmpWarningTimeComponent implements OnInit {
  subWarningModel: SubWarningModel[] = [];
  // subWarningDailyModel: SubWarningDailyModel [] = []
  subWarningDailyModel: SubWarningDailyModel = {
    datas: [],
    employeeDatas: [],
  };
  subWarningDailySelect: any;

  constructor(
    private subodinateService: SubodinateService,
    private tokenService: TokenService,
    private modalService: NgbModal,
    private router: Router
  ) {}

  ngOnInit() {
    this.getWarningAll();
    this.getWarningDaily();
  }

  getWarningAll() {
    this.subodinateService
      .getListAllPageSizePG(this.tokenService.getSelectCompany().companyId)
      .subscribe((result) => {
        this.subWarningModel = result;
        // console.log('result :',this.subWarningModel)
        console.log('result :', result);
      });
  }

  startDate = this.convertDate(new Date());
  // startDate = new Date(2024,4,9)

  getWarningDaily() {
    this.subodinateService
      .getWarningDaily(
        this.tokenService.getSelectCompany().companyId,
        this.startDate,
        this.startDate
      )
      .subscribe((result) => {
        // console.log('result = ', result);
        // this.tokenService.getDevice;
        this.subWarningDailyModel = result;
        this.subWarningDailySelect = result.datas.map((x) => {
          return { ...x, isSelected: false };
        });

        // this.subWarningDailyModel.datas = this.subWarningDailyModel.datas.map(
        //   (x) => {
        //     if(this.tokenService.getDevice()== "ios"){
        //       return { ...x, swipeDateTime: x.swipeDateTime.replace(" ", "T").replace("+0000", "") };
        //     }else{
        //       return x
        //     }
        //   }
        // );
      });
  }

  private convertDate(d: Date): string {
    return [
      d.getFullYear(),
      this.pad(d.getMonth() + 1),
      this.pad(d.getDate()),
    ].join('-');
  }

  private pad(s: number): string {
    return s < 10 ? '0' + s : s.toString();
  }

  searchAll = '';
  searchDaily = '';

  byPersonFilter(data: SubWarningModel[]): SubWarningModel[] {
    return data.filter(
      (x) =>
        (x.firstName + ' ' + x.lastName)
          .toLowerCase()
          .indexOf(this.searchAll.trim().toLowerCase()) != -1
    );
  }

  byDateFilter(): any[] {
    return this.subWarningDailySelect?.filter((x: any) =>
      x.memberName?.toLowerCase().includes(this.searchDaily.toLowerCase())
    );
  }

  checkedAll: any;

  selectAll() {
    this.subWarningDailySelect = this.subWarningDailySelect.map((x: any) => {
      return { ...x, isSelected: this.checkedAll };
    });
  }

  // approveAll(){}
  approveAll() {
    const modalRef = this.modalService.open(AlertComponent, { centered: true });
    modalRef.componentInstance.message = 'Do you want to confirm?';
    modalRef.componentInstance.confirmModal = true;
    modalRef.result.then(
      (respone) => {
        const swipeDateTime = this.subWarningDailySelect
          .filter((x: any) => x.isSelected)
          .map((x: any) => x.swipeDateTime + x.memberId);
        const selectData = this.subWarningDailyModel.datas.filter(
          (x) =>
            swipeDateTime.findIndex(
              (y: string) => y == x.swipeDateTime + x.memberId
            ) > -1
        );
        let check = 0;
        selectData.forEach((x, i) => {
          const body = {
            companyId: this.tokenService.getSelectCompany().companyId,
            memberId: x.memberId,
            employeeCode: x.employeeCode,
            approveId: this.tokenService.getUser().member.memberId,
            approveStatus: 1,
            approveType: 1,
            locationName: '',
            swipeDateTime: x.swipeDateTime,
          };
          this.subodinateService.approveWarningTime(body).subscribe(
            (result) => {
              check = check + 1;

            },
            (error) => {}
          );
          if (i == selectData.length - 1) {
            setTimeout(() => {
              if ((check == selectData.length)) {
                const modalRef = this.modalService.open(AlertComponent, {
                  centered: true,
                });
                modalRef.componentInstance.message = 'STATUS.Success';
              } else {
                const modalRef = this.modalService.open(AlertComponent, {
                  centered: true,
                });
                modalRef.componentInstance.message = 'STATUS.Fail';
              }
              this.getWarningDaily();
            }, 1000);
          }
        });
      },
      (error) => {}
    );
  }

  // goSubWarningTimeMap(){}
  goSubWarningTimeMap(data: DataModel) {
    this.router.navigate([
      '/company/sub-warning-timestamp-map',
      {
        data: JSON.stringify(data),
        startdate: this.convertDate(new Date()),
        enddate: this.convertDate(new Date()),
        path: '/company/employees-warning-time/',
      },
    ]);
  }
  checkSelect() {
    return this.byDateFilter()?.every((x) => x.isSelected == false);
  }
}
