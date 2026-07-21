import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { UserService } from '../../../DPU/services/user.service';
import swal from 'sweetalert';

@Component({
  selector: 'app-cover',
  standalone: true,
  imports: [SharedModule, CommonModule, RouterModule, FormsModule],
  templateUrl: './cover.component.html',
  styleUrls: ['./cover.component.scss']
})
export class CoverComponent {
  email = '';

  constructor(private userService: UserService) {}

  resetPass(): void {
    this.userService.resetPass(this.email).subscribe(() => {
      swal('Save Success!!', 'บันทึกข้อมูลสำเร็จ', 'success');
    });
  }
}
