import { HttpClient } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { interval, Subscription } from 'rxjs';

export interface MsgModel {
  data: Data;
}

export interface Data {
  status: string;
  message: string;
}

export interface ChatMessage {
  sender: string;
  message: string;
  timestamp: Date;
}


@Component({
  selector: 'app-messages',
  templateUrl: './messages.component.html',
  styleUrls: ['./messages.component.scss'],
  encapsulation: ViewEncapsulation.None
})
export class MessagesComponent implements OnInit {
  chatMessages: ChatMessage[] = []; // ตัวแปรเก็บข้อความแชท
  loadingMsg = false
  constructor(private http: HttpClient) { }

  intervalSubscription: Subscription | undefined;

  ngOnInit(): void {
    const footerhide: any = document.getElementsByTagName('app-footerinfo')[0];
    footerhide.remove();
    this.mockChatMessages()
  }

  // ฟังก์ชันสร้าง mock ข้อมูลแชท
  mockChatMessages() {
    this.chatMessages = [
      { sender: 'ME', message: 'สวัสดีครับ!', timestamp: new Date() },
      { sender: 'AI', message: 'สวัสดีค่ะ มีอะไรให้ช่วยไหมคะ?', timestamp: new Date() },
    ];
  }

  // ฟังก์ชันสำหรับส่งข้อความใหม่
  sendMessage(newMessage: string, sender: string) {
    const newChat: ChatMessage = {
      sender: sender,
      message: newMessage,
      timestamp: new Date()
    };
    this.chatMessages.push(newChat);
  }

  sentMsg(newMessage: string) {
    this.loadingMsg = true
    let body = {
      "user_id": "10000082",
      "message": newMessage
    };
    this.sendMessage(newMessage, "ME")
    this.http.post("https://mychat.myhr.co.th/submit_message/eb2f4f30-edaf-11ee-a69a-c7680edc0e47", body)
      .subscribe(result => {
        this.pollForMessage();
      });
  }

  pollForMessage() {

    // ยิง API query_message ทุก 3 วินาที
    this.intervalSubscription = interval(4000).subscribe(() => {
      this.http.post<MsgModel>("https://mychat.myhr.co.th/query_message/eb2f4f30-edaf-11ee-a69a-c7680edc0e47", undefined)
        .subscribe(result => {
          console.log(result);

          // เช็คว่ามี message หรือไม่
          if (result.data && result.data.message) {
            console.log('Message received:', result.data.message);
            this.sendMessage(result.data.message, "AI")
            this.loadingMsg = false
            // ถ้าเจอ message ก็หยุดการยิง API
            if (this.intervalSubscription) {
              this.intervalSubscription.unsubscribe();
            }
          }
        });
    });
  }
}
