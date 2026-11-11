import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';

import { HomeCommonComponent } from './home-common.component';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';

describe('HomeCommonComponent', () => {
  let fixture: ComponentFixture<HomeCommonComponent>;

  beforeEach(async () => {
    window.localStorage.clear();
    await TestBed.configureTestingModule({
    imports: [HomeCommonComponent, RouterTestingModule, TranslateModule.forRoot()],
    providers: [provideHttpClient(withInterceptorsFromDi()), provideHttpClientTesting()]
}).compileComponents();
    fixture = TestBed.createComponent(HomeCommonComponent);
    fixture.detectChanges();
  });

  it('creates and renders its admin links', () => {
    expect(fixture.componentInstance).toBeTruthy();
    expect(fixture.componentInstance.links.length).toBeGreaterThan(0);
  });
});
