import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";
import { UserGroup } from "./user-group.model";

export interface MenuModel {
  menuId: string;
  thName: string;
  engName: string;
  url: string;
  prev?: MenuModel;
  next?: MenuModel;
  group: UserGroup;
  module: ModuleMenuModel;
}

export class Menu extends BaseModel implements MenuModel {
  menuId: string;
  thName: string;
  engName: string;
  url: string;
  prev?: MenuModel;
  next?: MenuModel;
  group: UserGroup;
  module: ModuleMenuModel;
  constructor(
    data?: Partial<MenuModel>,
    translateService? : TranslateService
  ) {
    super(data,translateService);
    this.menuId = data?.menuId!;
    this.thName = data?.thName!;
    this.engName = data?.engName!;
    this.url = data?.url!
    this.prev = data?.prev  ? new Menu(data?.prev, this.translateService) : undefined
    this.next = data?.next  ? new Menu(data?.next, this.translateService) : undefined
    this.group = new UserGroup(data?.group, this.translateService)
    this.module = new ModuleMenu(data?.module, this.translateService)
  }

  getName(): string {
    return this.translateService.currentLang == "th"
      ? this.thName
      : this.engName;
  }
}

export interface ModuleMenuModel {
  moduleId: string;
  thName: string;
  engName: string;
}

export class ModuleMenu extends BaseModel implements ModuleMenuModel {
  moduleId: string;
  thName: string;
  engName: string;
  constructor(
    data?: Partial<ModuleMenuModel>,
    translateService? : TranslateService
  ) {
    super(data,translateService);
    this.moduleId = data?.moduleId!;
    this.thName = data?.thName!;
    this.engName = data?.engName!;
  }

  getName(): string {
    return this.translateService.currentLang == "th"
      ? this.thName
      : this.engName;
  }
}
