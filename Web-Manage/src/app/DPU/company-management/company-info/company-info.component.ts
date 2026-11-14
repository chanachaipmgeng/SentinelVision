import { CommonModule } from '@angular/common';
import {
  Component,
  ElementRef,
  OnInit,
  ViewChild,
  ViewEncapsulation, AfterViewInit,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GoogleMapsModule, MapMarker } from '@angular/google-maps';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslateModule } from '@ngx-translate/core';
import { FileItem, FileUploader, FileUploadModule, ParsedResponseHeaders } from 'ng2-file-upload';
import { SharedModule } from '../../../shared/shared.module';
import { LocationMapComponent } from '../../../shared/components/location-map/location-map.component';
import { TokenService } from '../../../shared/services/token.service';
import { CompanyService } from '../../services/company.service';
import { CompanyModel } from '../../models/company.model';
import { environment } from '../../../../environments/environment';
import { mountPlaceAutocomplete } from '../../../shared/utils/place-autocomplete';
import swal from 'sweetalert';

declare global {
  interface Window {
    __dpuMapsAuthFailed?: boolean;
  }
}

@Component({
    selector: 'app-company-info',
    imports: [
        SharedModule,
        NgSelectModule,
        CommonModule,
        FormsModule,
        FileUploadModule,
        TranslateModule,
        GoogleMapsModule,
        MapMarker,
        LocationMapComponent,
    ],
    templateUrl: './company-info.component.html',
    styleUrl: './company-info.component.css',
    encapsulation: ViewEncapsulation.None
})
export class CompanyInfoComponent implements OnInit, AfterViewInit {
  @ViewChild('placeAutocompleteHost', { static: false })
  placeAutocompleteHost!: ElementRef<HTMLElement>;

  readonly markerOptions: google.maps.MarkerOptions = { draggable: false };
  readonly zoom = 14;

  companyId = '';
  companyModel: CompanyModel = new CompanyModel();
  uploaderProfile?: FileUploader;
  uploadErrorMsg = '';
  loading = false;
  saving = false;
  center: google.maps.LatLngLiteral = { lat: 13.7563, lng: 100.5018 };
  regionalPrefs = { timezone: 'Asia/Bangkok', payrollCutoffDay: 25, dateFormat: 'dd/MM/yyyy' };

  get mapCenter(): google.maps.LatLngLiteral {
    return {
      lat: this.toCoord(this.companyModel.latitude, 13.7563),
      lng: this.toCoord(this.companyModel.longitude, 100.5018),
    };
  }

  get mapsReady(): boolean {
    const w = window as Window & { google?: { maps?: { Map?: unknown } } };
    return !window.__dpuMapsAuthFailed && !!w.google?.maps?.Map;
  }

  get mapsLink(): string {
    const { lat, lng } = this.mapCenter;
    return `https://www.google.com/maps?q=${lat},${lng}`;
  }

  get statusTone(): 'ok' | 'pending' {
    return this.companyModel.status === 1 ? 'ok' : 'pending';
  }

  constructor(
    private comService: CompanyService,
    private tokenService: TokenService
  ) {
    this.companyId = this.tokenService.getSelectCompany().companyId;
    this.uploadConfig();
  }

  ngOnInit(): void {
    this.getCompanyInfo();
  }

  async ngAfterViewInit() {
    await this.initPlaceAutocomplete();
  }

  async initPlaceAutocomplete() {
    if (!this.mapsReady) return;
    const host = this.placeAutocompleteHost?.nativeElement;
    if (!host) return;

    await mountPlaceAutocomplete(host, (place) => {
      this.companyModel.latitude = place.lat;
      this.companyModel.longitude = place.lng;
      if (place.address) {
        this.companyModel.address = place.address;
      }
      this.center = { lat: place.lat, lng: place.lng };
    });
  }

  uploadConfig() {
    this.uploaderProfile = new FileUploader({
      url: environment.baseUrl + '/api/upload-image',
      isHTML5: true,
      authToken: this.tokenService.getToken()!,
    });

    this.uploaderProfile.onAfterAddingFile = (fileItem: FileItem) => {
      fileItem.withCredentials = false;
      this.uploadErrorMsg = '';

      while (this.uploaderProfile!.queue.length > 1) {
        this.uploaderProfile!.queue[0].remove();
      }

      if (fileItem.file.size > 5000000) {
        this.uploadErrorMsg = 'maximum file size 5mb.';
        swal('ไฟล์ใหญ่เกินไป', 'ขนาดสูงสุด 5MB', 'info');
        fileItem.isCancel = true;
        return;
      }

      if (fileItem.file.type!.indexOf('image') === -1) {
        this.uploadErrorMsg = 'please upload image only.';
        swal('ไฟล์ไม่ถูกต้อง', 'กรุณาอัปโหลดรูปภาพเท่านั้น', 'info');
        fileItem.isCancel = true;
        return;
      }

      fileItem.upload();
    };

    this.uploaderProfile.onCompleteItem = (
      item: FileItem,
      response: string,
      _status: number,
      _headers: ParsedResponseHeaders
    ) => {
      if (item.isSuccess) {
        const res = JSON.parse(response);
        this.companyModel.picture = res.filename;
        swal('สำเร็จ', res.message || 'อัปโหลดรูปแล้ว', 'success');
      } else {
        this.uploadErrorMsg = 'cannot upload file.';
        swal('อัปโหลดไม่สำเร็จ', 'ไม่สามารถอัปโหลดได้', 'error');
      }
    };
  }

  changeMarker() {
    this.companyModel.latitude = this.toCoord(
      this.companyModel.latitude,
      13.7563
    );
    this.companyModel.longitude = this.toCoord(
      this.companyModel.longitude,
      100.5018
    );
    this.center = this.mapCenter;
  }

  addMarker(event: google.maps.MapMouseEvent) {
    if (!event.latLng) return;
    const lat = event.latLng.toJSON().lat;
    const lng = event.latLng.toJSON().lng;
    this.companyModel.latitude = lat;
    this.companyModel.longitude = lng;
    this.center = { lat, lng };
  }

  getCompanyInfo() {
    if (!this.companyId) return;
    this.loading = true;
    this.comService.getById(this.companyId).subscribe({
      next: (result) => {
        this.companyModel = new CompanyModel(result);
        this.tokenService.saveSelectCompany(result);
        this.center = this.mapCenter;
        this.loadRegionalPrefs();
        this.loading = false;
        setTimeout(() => void this.initPlaceAutocomplete(), 150);
      },
      error: () => {
        this.loading = false;
        swal('Error', 'โหลดข้อมูลบริษัทไม่สำเร็จ', 'error');
      },
    });
  }

  reset() {
    swal({
      title: 'ยกเลิกการแก้ไข?',
      text: 'ข้อมูลที่ยังไม่บันทึกจะหายไป',
      icon: 'warning',
      buttons: ['อยู่ต่อ', 'รีเซ็ต'],
    }).then((ok: unknown) => {
      if (ok) this.getCompanyInfo();
    });
  }

  save() {
    const name = (this.companyModel.companyName || '').trim();
    if (!name) {
      swal('ข้อมูลไม่ครบ', 'กรุณากรอกชื่อบริษัท', 'warning');
      return;
    }

    swal({
      title: 'บันทึกข้อมูลบริษัท?',
      text: name,
      icon: 'warning',
      buttons: ['ยกเลิก', 'บันทึก'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.saving = true;
      this.comService.update(this.companyModel).subscribe({
        next: () => {
          this.saveRegionalPrefs();
          this.saving = false;
          swal('สำเร็จ', 'บันทึกข้อมูลบริษัทแล้ว', 'success');
          this.getCompanyInfo();
        },
        error: (err) => {
          this.saving = false;
          const detail = err?.error?.detail;
          swal(
            'บันทึกไม่สำเร็จ',
            typeof detail === 'string' ? detail : 'อัปเดตข้อมูลไม่สำเร็จ',
            'error'
          );
        },
      });
    });
  }

  private loadRegionalPrefs(): void {
    try {
      const raw = localStorage.getItem(`sv_company_prefs_${this.companyId}`);
      if (raw) {
        this.regionalPrefs = { ...this.regionalPrefs, ...JSON.parse(raw) };
      }
    } catch {
      // ignore storage errors
    }
  }

  private saveRegionalPrefs(): void {
    try {
      const cutoff = Math.min(31, Math.max(1, Number(this.regionalPrefs.payrollCutoffDay) || 25));
      this.regionalPrefs.payrollCutoffDay = cutoff;
      localStorage.setItem(`sv_company_prefs_${this.companyId}`, JSON.stringify(this.regionalPrefs));
    } catch {
      // ignore storage errors
    }
  }

  private toCoord(value: unknown, fallback: number): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
}
