import { Component } from '@angular/core';
import { SharedModule } from '../../../../shared/shared.module';
import { NgSelectModule } from '@ng-select/ng-select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../shared/services/token.service';
import { UserRole } from '../../../../DPU/models/user-role-model';
import { UserService } from '../../../../DPU/services/user.service';
import swal from 'sweetalert';
@Component({
  selector: 'app-mailsettings',
  standalone: true,
  imports: [SharedModule, NgSelectModule, FormsModule, ReactiveFormsModule, CommonModule, TranslateModule],
  templateUrl: './mailsettings.component.html',
  styleUrl: './mailsettings.component.scss'
})
export class MailsettingsComponent {
  roleModel?: number
  currentPassword = ""
  newPassword = ""
  confirmPassword = ""
  selectedLanguage = ['English'];
  Languages = [
    { id: 1, name: 'English' },
    { id: 2, name: 'Arabic' },
    { id: 3, name: 'French' },
    { id: 4, name: 'Hindi' },
  ];
  toggleDisabled() {
    const Language: any = this.Languages[1];
    Language.disabled = !Language.disabled;
  }
  selectedTags = ['select'];
  tags = [
    { id: 1, name: 'Plain' },
    { id: 2, name: 'Relaxed' },
    { id: 3, name: 'Washed' },
    { id: 4, name: 'Solid' },

  ]
  url2 = '';
  onSelectFile2(event: any) {
    if (event.target && event.target.files && event.target.files[0]) {
      const reader = new FileReader();

      reader.readAsDataURL(event.target.files[0]); // read file as data URL

      reader.onload = (event: any) => {
        // called once readAsDataURL is completed
        this.url2 = event.target.result;
      };
    }
  }


  constructor(private tokenService: TokenService, private userService: UserService) {
    this.roleModel = this.tokenService.getUserData().role
  }

  resetPassword() {
    this.userService.resetPassUser(this.currentPassword, this.newPassword).subscribe(result => {
      swal("Save Success!!", "บันทึกข้อมูลสำเร็จ", "success");
    })
  }

}
