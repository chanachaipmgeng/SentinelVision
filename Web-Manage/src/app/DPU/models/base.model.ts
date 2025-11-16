import { TranslateService } from '@ngx-translate/core';

export class BaseModel{
   translateService: TranslateService;

   constructor(data?: Partial<any> ,translateService?: TranslateService){
      Object.assign(this , data);
      this.translateService = translateService!;

   }
}


export interface Sort {
  empty: boolean;
  unsorted: boolean;
  sorted: boolean;
}

export interface Pageable {
  offset: number;
  sort: Sort;
  unpaged: boolean;
  paged: boolean;
  pageNumber: number;
  pageSize: number;
}

export interface PageResponseModel<T> {
  totalPages: number;
  totalElements: number;
  size: number;
  content: T[];
  number: number;
  sort: Sort;
  pageable: Pageable;
  numberOfElements: number;
  first: boolean;
  last: boolean;
  empty: boolean;
}

export interface ResponseModel {
  message: string;
  statusCode: number;
  resultObject?: any;
  fail: boolean;
  actionStatus: string;
  none: boolean;
  success: boolean;
}
