import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { NgApexchartsModule } from 'ng-apexcharts';
import { SharedModule } from '../../../shared/shared.module';
import { TranslateModule } from '@ngx-translate/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CompanyService } from '../../services/company.service';
import { TokenService } from '../../../shared/services/token.service';

@Component({
  selector: 'app-home-installer',
  templateUrl: './home-installer.component.html',
  standalone: true,
  imports: [CommonModule, SharedModule, NgApexchartsModule, TranslateModule],
  styleUrls: ['./home-installer.component.css']
})
export class HomeInstallerComponent implements OnInit {
  companyId = ""
  constructor(private router: Router, private route: ActivatedRoute, private comService: CompanyService, private tokenService: TokenService) {
    this.companyId = this.route.snapshot.paramMap.get('companyId')!;
    this.comService.getById(this.companyId).subscribe(result => {
      console.log("SAVEEE")
      this.tokenService.saveSelectCompany(result);
      // this.router.navigate(["/company"]);
    })
  }

  ngOnInit() {

  }

}
