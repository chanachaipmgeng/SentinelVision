import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ProfileInfoEditComponent } from './profile-info-edit.component';

describe('ProfileInfoEditComponent', () => {
  let component: ProfileInfoEditComponent;
  let fixture: ComponentFixture<ProfileInfoEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ProfileInfoEditComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProfileInfoEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
