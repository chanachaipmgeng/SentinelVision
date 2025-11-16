import { Component, ElementRef, HostListener, Renderer2 } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '../../../../shared/shared.module';
import { SimplebarAngularModule } from 'simplebar-angular';

@Component({
  selector: 'app-filemanager',
  standalone: true,
  imports: [SharedModule,SimplebarAngularModule,CommonModule],
  templateUrl: './filemanager.component.html',
  styleUrl: './filemanager.component.scss'
})
export class FilemanagerComponent {
files=[
  {
    name:"VID-00292312-SPK823.mp4",
    category:"Videos",
    size:"87MB",
    date:"22,Nov 2022"
},
{
  name:"IMG-09123878-SPK734.jpeg",
  category:"Images",
  size:"1.35MB",
  date:"25,Nov 2022"
},  {
  name:"AMB-2012.zip",
  category:"Archives",
  size:"422KB",
  date:"23,Nov 2022"
},  {
  name:"AUD-1002-2012.mp3",
  category:"Archives",
  size:"422KB",
  date:"23,Nov 2022"
},  {
  name:"Document-02.pdf",
  category:"Documents",
  size:"1.69MB",
  date:"2,Dec 2022"
},
]
selectedFile: any = null;
// Inside your component class
selectFile(file: any) { // Change the type according to your file structure
  this.selectedFile = file;
}
closeFileDetails() {
  this.selectedFile = null;
}

isPanelOpen = false; // Initial state
WindowPreSize: number[] = []; // Array to store window sizes
isNavigationClosed = false; // Added variable to track if navigation is closed

constructor(private renderer: Renderer2, private el: ElementRef) {}

@HostListener('window:resize', ['$event'])
onResize(event: Event): void {
  this.adjustElements();
}

private adjustElements(): void {
  const windowWidth = window.innerWidth;

  // Adjust file manager elements based on window width
  if (windowWidth < 576) {
    if (this.isPanelOpen) {
      this.renderer.addClass(this.el.nativeElement.querySelector('.file-manager-folders'), 'open');
      this.renderer.removeClass(this.el.nativeElement.querySelector('.file-manager-navigation'), 'open');
    } else {
      this.renderer.removeClass(this.el.nativeElement.querySelector('.file-manager-folders'), 'open');
      this.renderer.addClass(this.el.nativeElement.querySelector('.file-manager-navigation'), 'open');
    }

    // Toggle close class for file-manager-navigation and open class for file-manager-folders
    if (this.isNavigationClosed) {
      this.renderer.addClass(this.el.nativeElement.querySelector('.file-manager-navigation'), 'close');
      this.renderer.addClass(this.el.nativeElement.querySelector('.file-manager-folders'), 'open');
    } else {
      this.renderer.removeClass(this.el.nativeElement.querySelector('.file-manager-navigation'), 'close');
      this.renderer.removeClass(this.el.nativeElement.querySelector('.file-manager-folders'), 'open');
    }
  } else {
    this.renderer.removeClass(this.el.nativeElement.querySelector('.file-manager-folders'), 'open');
    this.renderer.removeClass(this.el.nativeElement.querySelector('.file-manager-navigation'), 'open');
    this.renderer.removeClass(this.el.nativeElement.querySelector('.file-manager-navigation'), 'close');
  }

  // Adjust selected file details based on window width
  if (windowWidth < 1201) {
    this.renderer.addClass(this.el.nativeElement.querySelector('.selected-file-details'), 'd-none');
  }
}

togglePanel(): void {
  if (window.screen.width <= 575) {
    this.isPanelOpen = !this.isPanelOpen;
    this.isNavigationClosed = false; // Update isNavigationClosed when togglePanel is called from the button click
    this.adjustElements();
  }
}

// Modify closeNavigation method to toggle the isNavigationClosed variable
closeNavigation(): void {
  if (window.screen.width <= 575) {
    this.isNavigationClosed = !this.isNavigationClosed;
    this.adjustElements();
  }
}

showDetails(): void {
  if (window.innerWidth < 1201) {
    this.renderer.addClass(this.el.nativeElement.querySelector('.selected-file-details'), 'open');
    this.renderer.removeClass(this.el.nativeElement.querySelector('.selected-file-details'), 'd-none');
  }
}

hideDetails(): void {
  if (window.innerWidth < 1201) {
    this.renderer.addClass(this.el.nativeElement.querySelector('.selected-file-details'), 'd-none');
    this.renderer.removeClass(this.el.nativeElement.querySelector('.selected-file-details'), 'open');
  }
}

fileDetailsView(): void {
  this.WindowPreSize.push(window.innerWidth);

  if (this.WindowPreSize.length > 2) {
    this.WindowPreSize.shift();
  }

  if (this.WindowPreSize.length > 1) {
    const lastWidth = this.WindowPreSize[this.WindowPreSize.length - 1];
    const prevWidth = this.WindowPreSize[this.WindowPreSize.length - 2];

    if (lastWidth < 992 && prevWidth >= 992) {
      this.renderer.addClass(this.el.nativeElement.querySelector('.selected-file-details'), 'd-none');
    }

    if (lastWidth >= 992 && prevWidth < 992) {
      this.renderer.removeClass(this.el.nativeElement.querySelector('.selected-file-details'), 'd-none');
      this.renderer.removeClass(this.el.nativeElement.querySelector('.file-manager-folders'), 'open');
      this.renderer.removeClass(this.el.nativeElement.querySelector('.file-manager-navigation'), 'close');
    }
  }
}
}