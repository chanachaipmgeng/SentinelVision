import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";

export class PositionModel extends BaseModel{
  companyId?: string;
  positionId: string;
  thName: string;
  engName: string;
  constructor(
    data?: Partial<PositionModel>,
    translateService? : TranslateService
  ) {
    super(data,translateService);
    this.companyId = data?.companyId!
    this.positionId = data?.positionId!;
    this.thName = data?.thName!;
    this.engName = data?.engName!;
  }

  getName(): string {
    return this.translateService.currentLang == "th"
      ? this.thName
      : this.engName;
  }
}
