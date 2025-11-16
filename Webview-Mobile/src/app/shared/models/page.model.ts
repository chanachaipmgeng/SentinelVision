export interface PageModel<T> {
  content: T[];
  pageable: PageAble;
  totalElements: number;
  totalPages: number;
  last: boolean;
  size: number;
  sort: Sort;
  numberOfElements: number;
  first: boolean;
  empty: boolean;
}
export interface PageAble {
  sort?: Sort;
  offset?: number;
  pageNumber?: number;
  pageSize?: number;
  paged?: boolean;
  unpaged?: boolean;
}
export interface Sort {
  unsorted?: boolean;
  sorted?: boolean;
  empty?: boolean;
}
