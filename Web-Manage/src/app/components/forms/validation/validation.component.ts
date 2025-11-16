import { Component } from '@angular/core';
import { FormGroup, FormBuilder, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import flatpickr from 'flatpickr';
import { SharedModule } from '../../../shared/shared.module';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';


@Component({
  selector: 'app-validation',
  standalone: true,
  imports: [SharedModule,FormsModule,ReactiveFormsModule,FlatpickrModule],
  providers:[FlatpickrDefaults],
  templateUrl: './validation.component.html',
  styleUrls: ['./validation.component.scss']
})
export class ValidationComponent {
  // datePickerConfig = {
  //   format: 'DD-MM-YY',
  // };

  // updateFormat() {
  //   this.datePickerConfig = {
  //     ...this.datePickerConfig,
  //     format: 'DD-MM-YY',
  //   };
  // }


  public customForm!: FormGroup;

  constructor(private formBuilder: FormBuilder) {}

  ngOnInit() {
    this.customForm = this.formBuilder.group({
      firstname: ['', Validators.required],
      lastname: ['', Validators.required],
      phonenumber: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      password: ['', Validators.required],
      confirmPassword: ['', Validators.required],
      date: ['', Validators.required],
      gender: ['', Validators.required],
      address: ['', Validators.required],
      city: ['', Validators.required],
      state: ['', Validators.required],
      pincode: ['', Validators.required],
      agreement: [false, Validators.required],
    });
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
  Submit() {
    if (this.customForm.valid) {
      // Form is valid, handle the form submission here
      console.log('Form submitted successfully!');
    } else {
      // Form is invalid, display error messages or handle accordingly
      console.log('Form is invalid!');
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


}
