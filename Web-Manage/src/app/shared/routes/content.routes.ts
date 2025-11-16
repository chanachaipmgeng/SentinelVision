import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { admin, dashboardRoutingModule } from '../../components/dashboards/dashboard.routes';
import { advanceduiRoutingModule } from '../../components/advancedui/advancedui.routes';
import { pagesRoutingModule } from '../../components/pages/pages.routes';
import { ecommerceRoutingModule } from '../../components/pages/ecommerce/ecommerce.routes';
import { filemanagerRoutingModule } from '../../components/pages/file-manager/filemanager.routes';
import { invoiceRoutingModule } from '../../components/pages/invoice/invoice.routes';
import { taskRoutingModule } from '../../components/tasks/task.routes';
import { chartsRoutingModule } from '../../components/charts/charts.routes';
import { apexchartsRoutingModule } from '../../components/charts/apexcharts/apex.routes';
import { blogRoutingModule } from '../../components/pages/blog/blog.routes';
import { mailRoutingModule } from '../../components/pages/email/email.routes';
import { uielementsRoutingModule } from '../../components/uielements/uielements.routes';
import { utilitiesRoutingModule } from '../../components/utilities/utilities.routes';
import { appsRoutingModule } from '../../components/apps/apps.routes';
import { crmRoutingModule } from '../../components/apps/crm/crm.routes';
import { cryptoRoutingModule } from '../../components/apps/crypto/crypto.routes';
import { jobsRoutingModule } from '../../components/apps/jobs/jobs.routes';
import { projectsRoutingModule } from '../../components/apps/projects/projects.routes';
import { nftRoutingModule } from '../../components/apps/nft/nft.routes';
import { FormEditorsRoutingModule } from '../../components/forms/form-editors/form-editors.routes';
import { formelementsRoutingModule } from '../../components/forms/form-elements/form-elements.routes';
import { formsRoutingModule } from '../../components/forms/forms.routes';
import { mapsRoutingModule } from '../../components/maps/maps.routes';
import { iconsRoutingModule } from '../../components/icons/icons.routes';
import { widgetsRoutingModule } from '../../components/widgets/widgets.routes';
import { tablesRoutingModule } from '../../components/tables/tables.routes';
import { CommonManageModule } from '../../DPU/common/common.module';
import { CompanyManagementModule } from '../../DPU/company-management/company-management.module';


export const content: Routes = [

  {
    path: '', children: [
       ...dashboardRoutingModule.routes,
       ...advanceduiRoutingModule.routes,
       ...pagesRoutingModule.routes,
      ...ecommerceRoutingModule.routes,
       ...filemanagerRoutingModule.routes,
       ...invoiceRoutingModule.routes,
       ...taskRoutingModule.routes,
       ...chartsRoutingModule.routes,
       ...apexchartsRoutingModule.routes,
       ...blogRoutingModule.routes,
       ...mailRoutingModule.routes,
       ...uielementsRoutingModule.routes,
       ...utilitiesRoutingModule.routes,
       ...appsRoutingModule.routes,
       ...crmRoutingModule.routes,
       ...cryptoRoutingModule.routes,
       ...jobsRoutingModule.routes,
       ...projectsRoutingModule.routes,
       ...nftRoutingModule.routes,
       ...FormEditorsRoutingModule.routes,
       ...formelementsRoutingModule.routes,
       ...formsRoutingModule.routes,
       ...mapsRoutingModule.routes,
       ...iconsRoutingModule.routes,
       ...widgetsRoutingModule.routes,
       ...tablesRoutingModule.routes,
      ...CommonManageModule.routes,
      ...CompanyManagementModule.routes
    ]
  }


];
@NgModule({
  imports: [RouterModule.forRoot(admin)],
  exports: [RouterModule]
})
export class SaredRoutingModule { }
