import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';

import { TimestampLogComponent } from './timestamp-log.component';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';

describe('TimestampLogComponent', () => {
  let fixture: ComponentFixture<TimestampLogComponent>;

  beforeEach(async () => {
    window.localStorage.clear();
    await TestBed.configureTestingModule({
    imports: [TimestampLogComponent, RouterTestingModule, TranslateModule.forRoot()],
    providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({}) } } },
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
    ]
}).compileComponents();
    fixture = TestBed.createComponent(TimestampLogComponent);
    fixture.detectChanges();
  });

  it('creates without a selected company and skips the timestamp query', () => {
    expect(fixture.componentInstance).toBeTruthy();
    const http = TestBed.inject(HttpTestingController);
    // only the employee list is requested; timestamps are skipped without a companyId
    const pending = http.match(() => true);
    expect(pending.every((r) => !r.request.url.includes('/timestamp'))).toBeTrue();
    pending.forEach((r) => r.flush([]));
    http.verify();
  });
});
