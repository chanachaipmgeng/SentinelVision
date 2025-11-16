import { Component } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import flatpickr from 'flatpickr';
import { MaterialModuleModule } from '../../../../../app/material-module/material-module.module';
import { SharedModule } from '../../../../../app/shared/shared.module';
import {CdkDragDrop, moveItemInArray, transferArrayItem} from '@angular/cdk/drag-drop';
import { NgFor } from '@angular/common';
import { DragDropModule } from '@angular/cdk/drag-drop';
@Component({
  selector: 'app-deals',
  standalone: true,
  imports: [SharedModule,DragDropModule,NgFor,MaterialModuleModule,FormsModule,ReactiveFormsModule, MatDatepickerModule, FlatpickrModule],
  providers: [FlatpickrDefaults],
  templateUrl: './deals.component.html',
  styleUrls: ['./deals.component.scss']
})
export class DealsComponent {
  todo = [
    `  <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/12.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Service Upgrade</div>
            </div>
            <div>$5000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Spruko Technologies</a>
            </div>
            <div class="text-muted text-xs">24,Jun 2023 - 12:45PM</div>
        </div>
    </div>
</div>`,
    `       <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/5.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Product Demo</div>
            </div>
            <div>$50,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Acme Corporation LTD</a>
            </div>
            <div class="text-muted text-xs">18,Apr 2023 - 11:22AM</div>
        </div>
    </div>
</div>`,
    `    <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/15.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Website Redesign</div>
            </div>
            <div>$20,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Embark Technologies</a>
            </div>
            <div class="text-muted text-xs">12,Jul 2023 - 10:15AM</div>
        </div>
    </div>
</div>`,
    `       <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/6.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Consulting Services</div>
            </div>
            <div>$10,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Adam Johnson</a>
            </div>
            <div class="text-muted text-xs">29,Jul 2023 - 4:45PM</div>
        </div>
    </div>
</div>`,

  ];
  done = [
    `      <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/11.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Event Sponsorship</div>
            </div>
            <div>$10,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Initech Info</a>
            </div>
            <div class="text-muted text-xs">21,May 2023 - 10:25AM</div>
        </div>
    </div>
</div>`,
    `        <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/11.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Sales Training</div>
            </div>
            <div>$6,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Soylent Corp</a>
            </div>
            <div class="text-muted text-xs">10,May 2023 - 9:20AM</div>
        </div>
    </div>
</div>`,
    `    <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/14.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Content Creation</div>
            </div>
            <div>$3,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Hooli Technologies</a>
            </div>
            <div class="text-muted text-xs">25,Aug 2023 - 3:38PM</div>
        </div>
    </div>
</div>`,
     ];
     todo1 = [
      `   <div class="box custom-box">
      <div class="box-body">
          <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
              <div class="flex items-center gap-2">
                  <div class="lh-1">
                      <span class="avatar avatar-sm avatar-rounded">
                          <img src="./assets/images/faces/3.jpg" alt="">
                      </span>
                  </div>
                  <div class="text-sm">E-commerce Integration</div>
              </div>
              <div>$12,000</div>
          </div>
          <div class="deal-description">
              <div class="my-1">
                  <a href="javascript:void(0);" class="company-name">Spice Infotech</a>
              </div>
              <div class="text-muted text-xs">15,Sep 2023 - 8:32PM</div>
          </div>
      </div>
  </div>`,
      `     <div class="box custom-box">
      <div class="box-body">
          <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
              <div class="flex items-center gap-2">
                  <div class="lh-1">
                      <span class="avatar avatar-sm avatar-rounded">
                          <img src="./assets/images/faces/16.jpg" alt="">
                      </span>
                  </div>
                  <div class="text-sm">Ad Campaign</div>
              </div>
              <div>$5,500</div>
          </div>
          <div class="deal-description">
              <div class="my-1">
                  <a href="javascript:void(0);" class="company-name">Umbrella Corp</a>
              </div>
              <div class="text-muted text-xs">17,Jun 2023 - 10:54AM</div>
          </div>
      </div>
  </div>`,
      `    <div class="box custom-box">
      <div class="box-body">
          <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
              <div class="flex items-center gap-2">
                  <div class="lh-1">
                      <span class="avatar avatar-sm avatar-rounded">
                          <img src="./assets/images/faces/15.jpg" alt="">
                      </span>
                  </div>
                  <div class="text-sm">Website Redesign</div>
              </div>
              <div>$20,000</div>
          </div>
          <div class="deal-description">
              <div class="my-1">
                  <a href="javascript:void(0);" class="company-name">Embark Technologies</a>
              </div>
              <div class="text-muted text-xs">12,Jul 2023 - 10:15AM</div>
          </div>
      </div>
  </div>`,
      `       <div class="box custom-box">
      <div class="box-body">
          <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
              <div class="flex items-center gap-2">
                  <div class="lh-1">
                      <span class="avatar avatar-sm avatar-rounded">
                          <img src="./assets/images/faces/6.jpg" alt="">
                      </span>
                  </div>
                  <div class="text-sm">Consulting Services</div>
              </div>
              <div>$10,000</div>
          </div>
          <div class="deal-description">
              <div class="my-1">
                  <a href="javascript:void(0);" class="company-name">Adam Johnson</a>
              </div>
              <div class="text-muted text-xs">29,Jul 2023 - 4:45PM</div>
          </div>
      </div>
  </div>`,
  
    ];
  done1 = [
    `     <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/10.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Webinar Series</div>
            </div>
            <div>$9,500</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Massive Dynamic</a>
            </div>
            <div class="text-muted text-xs">16,May 2023 - 11:22AM</div>
        </div>
    </div>
</div>`,

    ` <div class="box custom-box box-bg-success">
    <div class="box-body">
        <div class="flex items-center w-full">
            <div class="me-2">
                <span class="avatar">
                    <img src="./assets/images/faces/5.jpg" alt="img" class="!rounded-full">
                </span>
            </div>
            <div class="">
                <div class="text-[0.9375rem] font-semibold text-white">Samantha sid</div>
                <p class="mb-0 text-white opacity-[0.7] text-[0.75rem]">In leave for 1 month</p>
            </div>
        </div>
    </div>
</div>`,
    `      <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/13.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">SEO Audit</div>
            </div>
            <div>$3,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Logitech ecostics</a>
            </div>
            <div class="text-muted text-xs">27,Apr 2023 - 5:15PM</div>
        </div>
    </div>
</div>`,
    `    <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/8.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Loyalty Program</div>
            </div>
            <div>$12,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">Globex Corp</a>
            </div>
            <div class="text-muted text-xs">26,Jul 2023 - 5:28AM</div>
        </div>
    </div>
</div>`,
`    <div class="box custom-box">
<div class="box-body">
    <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
        <div class="flex items-center gap-2">
            <div class="lh-1">
                <span class="avatar avatar-sm avatar-rounded">
                    <img src="./assets/images/faces/9.jpg" alt="">
                </span>
            </div>
            <div class="text-sm">CRM Integration</div>
        </div>
        <div>$10,000</div>
    </div>
    <div class="deal-description">
        <div class="my-1">
            <a href="javascript:void(0);" class="company-name">CrystalClear Consulting</a>
        </div>
        <div class="text-muted text-xs">14,May 2023 - 11:29PM</div>
    </div>
</div>
</div>`
 
  ];
  todo2 = [
    `      <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/16.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Media Analytics</div>
            </div>
            <div>$9,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">GlobalConnect</a>
            </div>
            <div class="text-muted text-xs">18,Mar 2023 - 2:32PM</div>
        </div>
    </div>
</div>`,

    ` <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded bg-light">
                        <img src="./assets/images/faces/21.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Lead Nurturing Strategy</div>
            </div>
            <div>$4,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">AlphaTech Solutions</a>
            </div>
            <div class="text-muted text-xs">16,Jul 2023 - 7:53AM</div>
        </div>
    </div>
</div>`,
    `    <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        PL
                    </span>
                </div>
                <div class="text-sm">Website Maintenance</div>
            </div>
            <div>$7,500</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">RedRock Industries</a>
            </div>
            <div class="text-muted text-xs">30,Jul 2023 - 6:30AM</div>
        </div>
    </div>
</div>`,
    `      <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/17.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Graphic Design</div>
            </div>
            <div>$5,000</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">TechPro Services</a>
            </div>
            <div class="text-muted text-xs">10,Jul 2023 - 10:15PM</div>
        </div>
    </div>
</div>`,
`    <div class="box custom-box">
<div class="box-body">
    <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
        <div class="flex items-center gap-2">
            <div class="lh-1">
                <span class="avatar avatar-sm avatar-rounded">
                    <img src="./assets/images/faces/9.jpg" alt="">
                </span>
            </div>
            <div class="text-sm">CRM Integration</div>
        </div>
        <div>$10,000</div>
    </div>
    <div class="deal-description">
        <div class="my-1">
            <a href="javascript:void(0);" class="company-name">CrystalClear Consulting</a>
        </div>
        <div class="text-muted text-xs">14,May 2023 - 11:29PM</div>
    </div>
</div>
</div>`
 
  ];
  done2 = [
    `        <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/1.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">CRM Training</div>
            </div>
            <div>$4,200</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">BlueSky Industries</a>
            </div>
            <div class="text-muted text-xs">15,May 2023 - 8:20AM</div>
        </div>
    </div>
</div>`,
    `      <div class="box custom-box">
    <div class="box-body">
        <div class="flex items-center font-semibold justify-between gap-1 flex-wrap">
            <div class="flex items-center gap-2">
                <div class="lh-1">
                    <span class="avatar avatar-sm avatar-rounded">
                        <img src="./assets/images/faces/10.jpg" alt="">
                    </span>
                </div>
                <div class="text-sm">Market Research</div>
            </div>
            <div>$10,500</div>
        </div>
        <div class="deal-description">
            <div class="my-1">
                <a href="javascript:void(0);" class="company-name">BrightStar Solutions</a>
            </div>
            <div class="text-muted text-xs">28,Jun 2023 - 9:27PM</div>
        </div>
    </div>
</div>`,
   
     ];
  url1:string = '';
  handleFileInput(event: any): void {
    const file = event.target.files[0];
    if (file) { 
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.url1 = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  }
  basicDemoValue = '2017-01-01';
  inlineDatePicker: Date = new Date();
  timePicker: Date | null = null;
  timePicker1: Date | null = null;
  timePicker2: Date | null = null;
  timePicker3: Date | null = null;
  timePicker4: Date | null = null;

  flatpickrOptions: any = {
    inline: true,
  };
  // flatpickrOptions: FlatpickrOptions;

  constructor() {}

  ngOnInit() {
    this.flatpickrOptions = {
      enableTime: true,
      noCalendar: true,
      dateFormat: 'H:i',
    };

    flatpickr('#inlinetime', this.flatpickrOptions);

      this.flatpickrOptions = {
        enableTime: true,
        dateFormat: 'Y-m-d H:i', // Specify the format you want
        defaultDate: '2023-11-07 14:30', // Set the default/preloaded time (adjust this to your desired time)
      };

      flatpickr('#pretime', this.flatpickrOptions);

  }
  drop(event: CdkDragDrop<string[]>) {
    if (event.previousContainer === event.container) {
      moveItemInArray(
        event.container.data,
        event.previousIndex,
        event.currentIndex
      );
    } else {
      transferArrayItem(
        event.previousContainer.data,
        event.container.data,
        event.previousIndex,
        event.currentIndex
      );
    }
  }


}
