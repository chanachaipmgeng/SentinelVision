import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";

export class DepartmentModel extends BaseModel{
  companyId: string;
  departmentId: string;
  thName: string;
  engName: string;
  constructor(
    data?: Partial<DepartmentModel>,
    translateService? : TranslateService
  ) {
    super(data,translateService);
    this.companyId = data?.companyId!;
    this.departmentId = data?.departmentId!;
    this.thName = data?.thName!;
    this.engName = data?.engName!;
  }

  getName(): string {
    return this.translateService.currentLang == "th"
      ? this.thName
      : this.engName;
  }
}
