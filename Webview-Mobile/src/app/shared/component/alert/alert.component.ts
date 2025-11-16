import { Component, EventEmitter, Input, Output } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-alert',
  templateUrl: './alert.component.html',
  styleUrls: ['./alert.component.scss']
})
export class AlertComponent {
  @Input() message = ""
  @Input() headModal = "Alert"
  @Input() confirmModal = false
  constructor(public activeModal: NgbActiveModal) {

  }
}
