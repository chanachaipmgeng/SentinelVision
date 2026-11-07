import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';

import { WarningTimetampComponent } from './warning-timetamp.component';

describe('WarningTimetampComponent', () => {
  let fixture: ComponentFixture<WarningTimetampComponent>;

  beforeEach(async () => {
    window.localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [WarningTimetampComponent, HttpClientTestingModule, RouterTestingModule, TranslateModule.forRoot()],
    }).compileComponents();
    fixture = TestBed.createComponent(WarningTimetampComponent);
    fixture.detectChanges();
  });

  it('creates without a selected company and does not hit the API', () => {
    expect(fixture.componentInstance).toBeTruthy();
    TestBed.inject(HttpTestingController).expectNone(() => true);
  });
});
