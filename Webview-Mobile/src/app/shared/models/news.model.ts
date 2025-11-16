import { SafeUrl } from "@angular/platform-browser";

export class NewsModel {
  companyId: string;
  newsId: string;
  topic: string;
  image_url: string;
  source_url?: string;
  detail: string;
  createBy?: string;
  createName?: string;
  createDatetime?: string;

  constructor(init?: Partial<NewsModel>) {
    Object.assign(this, init);
  }

  get shortDetail() {
    const idx = this.detail.indexOf("<img ");
    if (idx > -1) {
      return this.detail.substring(0, idx);
    } else {
      return this.detail;
    }
  }
}

export class NewsFullModel {
  companyId: string;
  companyName: string;
  content: string;
  contentType: number;
  detail: string;
  endDatetime: string;
  id: number;
  newsPicture: string;
  picShow: any;
  newsStatus: number;
  newsStatusName: String;
  newsType: number;
  newsTypeName : string;
  newsUrl: string;
  priority: number;
  remark: string;
  startDatetime: string;
  subject: string;
  showType: number;
  layout : number;
  constructor(init?: Partial<NewsFullModel>) {
    if (init) {
      this.companyId = init.companyId!;
      this.companyName = init.companyName!;
      this.content = init.content!;
      this.contentType = init.contentType!;
      this.detail = init.detail!;
      this.id = init.id!;
      this.newsPicture = init.newsPicture!;
      this.newsStatus = init.newsStatus!;
      this.newsStatusName = init.newsStatus == 0 ? "WAITING" : ((init.newsStatus==1) ? "APPROVED" : "REJECT");
      this.newsType = init.newsType!;
      this.newsTypeName = init.newsType == 0 ? "PRIVATE" : ((init.newsType==1) ? "PUBLIC" : "ADS");
      this.newsUrl = init.newsUrl!;
      this.priority = init.priority!;
      this.remark = init.remark!;
      this.startDatetime = init.startDatetime!;
      this.endDatetime = init.endDatetime!;
      this.subject = init.subject!;
      this.showType = init.showType!;
      this.layout = init.layout!;
    }
  }
}

export class CompanyNewsModel {
  companyId: string;
  companyName: string;
  id: number;
  newsId: number;
}
