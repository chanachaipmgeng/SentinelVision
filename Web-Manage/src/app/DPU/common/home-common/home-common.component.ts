import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-home-common',
  imports: [RouterModule, SharedModule],
  standalone: true,
  templateUrl: './home-common.component.html',
  styleUrls: ['./home-common.component.css']
})
export class HomeCommonComponent {}
