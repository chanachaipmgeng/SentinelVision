import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [
    CommonModule,
  ],
  template: `<p>user-management works!</p>`,
  styleUrl: './user-management.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserManagementComponent { }
