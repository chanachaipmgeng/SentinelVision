import { Component, Input, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { environment } from '../../../../../environments/environment';
import swal from 'sweetalert';

// Define an interface for the encoding object for better type safety
interface FaceEncoding {
  faceEncodingId: string;
  memberId: string;
  createdAt: string;
  imageUrl: string;
}

@Component({
  selector: 'app-face-management',
  standalone: true,
  imports: [CommonModule], // CommonModule is needed for *ngIf, *ngFor etc.
  templateUrl: './face-management.component.html',
  styleUrls: ['./face-management.component.css']
})
export class FaceManagementComponent implements OnInit {

  @Input() memberId!: string;
  
  encodings: FaceEncoding[] = [];
  isLoading = true;
  error: string | null = null;

  constructor(private http: HttpClient) { }

  ngOnInit(): void {
    if (this.memberId) {
      this.loadEncodings();
    } else {
      this.error = "Member ID is missing.";
      this.isLoading = false;
    }
  }

  loadEncodings(): void {
    this.isLoading = true;
    this.error = null;
    this.http.get<FaceEncoding[]>(`${environment.baseUrl}/face/members/${this.memberId}/encodings`).subscribe({
      next: (data) => {
        this.encodings = data;
        this.isLoading = false;
      },
      error: (err) => {
        this.error = "Failed to load face encodings. Please try again later.";
        console.error(err);
        this.isLoading = false;
      }
    });
  }

  deleteEncoding(encodingId: string): void {
    swal({
      title: "Are you sure?",
      text: "Once deleted, you will not be able to recover this enrolled face!",
      icon: "warning",
      buttons: ['Cancel', 'Delete'],
      dangerMode: true,
    })
    .then((willDelete) => {
      if (willDelete) {
        this.http.delete(`${environment.baseUrl}/face/encodings/${encodingId}`).subscribe({
          next: () => {
            swal("Poof! The enrolled face has been deleted!", {
              icon: "success",
            });
            // Refresh the list
            this.loadEncodings();
          },
          error: (err) => {
            swal("Oops!", "Failed to delete the face. Please try again.", "error");
            console.error(err);
          }
        });
      }
    });
  }

  getFullImageUrl(relativeUrl: string): string {
    return `${environment.baseUrl}${relativeUrl}`;
  }
}
