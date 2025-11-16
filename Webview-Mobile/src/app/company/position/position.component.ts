import { Component, OnInit } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslateService } from '@ngx-translate/core';
import { AlertComponent } from 'src/app/shared/component/alert/alert.component';
import { PositionModel } from 'src/app/shared/models/position.model';
import { PositionService } from 'src/app/shared/services/position.service';
import { TokenService } from 'src/app/shared/services/token.service';

@Component({
  selector: 'app-position',
  templateUrl: './position.component.html',
  styleUrls: ['./position.component.scss']
})
export class PositionComponent implements OnInit {

  positionModel: PositionModel[] = []
  search = ""
  positionName = ""
  headModal = ""
  constructor(
    private positionService: PositionService,
    private tokenService: TokenService,
    private translate: TranslateService,
    private modalService: NgbModal
  ) { }

  ngOnInit() {
    this.getPositionList();
  }

  getPositionList() {
    this.positionService.getLists(this.tokenService.getSelectCompany().companyId).subscribe(result => {
      this.positionModel = result
    })
  }

  positionListFilter(data: PositionModel[]): PositionModel[] {
    return data.filter(x => x.getName()?.toLowerCase().indexOf(this.search.toLowerCase()) != -1)
  }

  deletePosition(position: PositionModel) {
    const modalRef = this.modalService.open(AlertComponent, { centered: true })
    modalRef.componentInstance.headModal = "Delete Position"
    modalRef.componentInstance.message = "Do you want to confirm?"
    modalRef.componentInstance.confirmModal = true
    modalRef.result.then(respone => {
      this.positionService.delete(position).subscribe((response: any) => {
        this.getPositionList();
        const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
        modalAlertRef.componentInstance.message = "STATUS.Success"
      }, error => {
        const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
        modalAlertRef.componentInstance.message = "STATUS.Fail"
      })
    })
  }

  addPositionOpen(content: any, position?: PositionModel) {
    this.headModal = position ? "Edit Position" : "Add Position"
    const modalRef = this.modalService.open(content, { centered: true })
    modalRef.result.then((result) => {
      if (position) {
        this.positionService.update(position).subscribe((response: any) => {
          this.getPositionList();
          const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
          modalAlertRef.componentInstance.message = "STATUS.Success"
        }, error => {
          const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
          modalAlertRef.componentInstance.message = "STATUS.Fail"
        })
      } else {
        this.positionService.save(position!).subscribe((response: any) => {
          this.getPositionList();
          const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
          modalAlertRef.componentInstance.message = "STATUS.Success"
        }, error => {
          const modalAlertRef = this.modalService.open(AlertComponent, { centered: true })
          modalAlertRef.componentInstance.message = "STATUS.Fail"
        })
      }
    }, (reason) => {

    });
  }

}

