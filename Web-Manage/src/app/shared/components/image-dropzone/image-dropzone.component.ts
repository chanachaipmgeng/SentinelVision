import {
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
  ViewChild,
  ViewEncapsulation,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-image-dropzone',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './image-dropzone.component.html',
  styleUrls: ['./image-dropzone.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class ImageDropzoneComponent implements OnDestroy {
  @ViewChild('fileInput') fileInput?: ElementRef<HTMLInputElement>;

  @Input() label = 'รูปถ่ายใบหน้า (Face Photo)';
  @Input() sublabel = 'สกัด Embedding 512-d อัตโนมัติ';
  @Input() hint = 'ลากและวางรูปภาพที่นี่ หรือคลิกเพื่อเลือกไฟล์';
  @Input() accept = 'image/png,image/jpeg,image/webp,image/jpg';
  @Input() maxSizeMb = 10;
  @Input() previewUrl: string | null = null;
  @Input() compact = false;

  @Output() fileSelected = new EventEmitter<File>();
  @Output() fileCleared = new EventEmitter<void>();

  isDragging = false;
  selectedFile: File | null = null;
  localPreview: string | null = null;
  errorMessage: string | null = null;

  ngOnDestroy(): void {
    this.revokeLocalPreview();
  }

  get currentPreview(): string | null {
    return this.localPreview || this.previewUrl || null;
  }

  get formattedFileSize(): string {
    if (!this.selectedFile) return '';
    const bytes = this.selectedFile.size;
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  onTriggerClick(): void {
    if (this.fileInput) {
      this.fileInput.nativeElement.value = '';
      this.fileInput.nativeElement.click();
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;

    if (event.dataTransfer && event.dataTransfer.files.length > 0) {
      const file = event.dataTransfer.files[0];
      this.processFile(file);
    }
  }

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.processFile(input.files[0]);
    }
  }

  clear(event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.revokeLocalPreview();
    this.selectedFile = null;
    this.errorMessage = null;
    if (this.fileInput) {
      this.fileInput.nativeElement.value = '';
    }
    this.fileCleared.emit();
  }

  private processFile(file: File): void {
    this.errorMessage = null;

    if (!file.type.startsWith('image/')) {
      this.errorMessage = 'กรุณาเลือกไฟล์รูปภาพเท่านั้น (PNG, JPG, WEBP)';
      return;
    }

    if (file.size > this.maxSizeMb * 1024 * 1024) {
      this.errorMessage = `ขนาดไฟล์เกินกำหนด (สูงสุด ${this.maxSizeMb} MB)`;
      return;
    }

    this.revokeLocalPreview();
    this.selectedFile = file;
    this.localPreview = URL.createObjectURL(file);
    this.fileSelected.emit(file);
  }

  private revokeLocalPreview(): void {
    if (this.localPreview && this.localPreview.startsWith('blob:')) {
      try {
        URL.revokeObjectURL(this.localPreview);
      } catch {
        // ignore
      }
      this.localPreview = null;
    }
  }
}
