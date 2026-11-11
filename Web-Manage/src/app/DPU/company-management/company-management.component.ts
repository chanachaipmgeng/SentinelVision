import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { TokenService } from '../../shared/services/token.service';
import { CompanyService } from '../services/company.service';

@Component({
    selector: 'app-company-management',
    templateUrl: './company-management.component.html',
    styleUrls: ['./company-management.component.css'],
    standalone: false
})
export class InstallManagementComponent implements OnInit {
  companyId = ""
  constructor(private router: Router, private route: ActivatedRoute, private comService: CompanyService, private tokenService: TokenService) {

  }

  ngOnInit() {
    this.companyId = this.route.snapshot.paramMap.get('companyId')!;
    this.comService.getById(this.companyId).subscribe(result => {
      this.tokenService.saveSelectCompany(result);
      // this.router.navigate(["/company",""]);
    })
  }
}
