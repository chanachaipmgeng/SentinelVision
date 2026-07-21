# แผน: รีสไตล์ Angular + Profile + Timestamp approval

อัปเดตตามคำตอบล่าสุด:
- **คง Angular** (ไม่เปลี่ยนเป็น Next.js)
- **เปลี่ยนสไตล์ / รูปแบบเทมเพลต** (ทิ้ง ThemeForest look, ดีไซน์ใหม่บนโค้ดผลิตภัณฑ์)
- **ทำคู่กัน:** โปรไฟล์พนักงานละเอียด + อนุมัติ/หมายเหตุลงเวลา

## สถานะงาน (อัปเดต)

- **P0** เสร็จ: ตัด demo routes/โฟลเดอร์ Admin+Mobile, ย้าย reset-password Cover, เก็บเฉพาะ product routes
- **P1** เริ่มแล้ว: design tokens (`dpu-theme.css` / mobile `:root`) โทน teal/slate
- **P2** เริ่มแล้ว: API profile + approval fields, Admin คิวอนุมัติ, Mobile note นอกพื้นที่ + ฟิลด์โปรไฟล์

## แนวทาง

ไม่ rewrite ทั้งแอปจากศูนย์แบบ stack ใหม่ — แต่:

1. **ตัด ThemeForest demo** ออกให้เหลือเฉพาะหน้า DPU / company
2. **ใส่ design system ใหม่** (CSS variables, layout shell, typography) ทับ shell เดิม
3. **ขยาย API + หน้า** สำหรับ profile และ timestamp approval

```
Web-Manage (Angular 17)     — รีสไตล์ + ฟีเจอร์ admin
Webview-Mobile (Angular 15) — รีสไตล์ + check-in / profile
API-Fast                    — ขยาย schema
```

## เฟสงาน

### P0 — คลีน template
**Mobile**
- ลบ route `working-plan`, `doc-refer` (มาร์คยังไม่ใช้)
- ถอด `/apps/*`, `/component/*` + ลบ demo layouts
- เก็บ `/company`, `/general`, auth ที่ใช้จริง

**Admin**
- ตัด demo ออกจาก `content.routes.ts`
- ลบ `src/app/components/` (Ynex demos)
- ตัดลิงก์ demo ใน header / `prismData`

**Done:** build ผ่าน; เมนูผลิตภัณฑ์ใช้ได้

### P1 — สไตล์ / เทมเพลตใหม่
- กำหนด tokens: สี, ฟอนต์, spacing, radius ใน SCSS/CSS variables (หลีกเลี่ยงโทนม่วง/ครีม AI-slop)
- Admin: sidebar + topbar ใหม่ บางและชัด; การ์ดเฉพาะจุดที่ต้อง interact
- Mobile: shell ล่าง/บนใหม่; หน้าแรกโฟกัส check-in
- ไม่ดึง ThemeForest กลับมา; ใช้ asset เท่าที่จำเป็น

**Done:** ทั้งสองแอปดูเป็นระบบเดียวกัน ไม่เหลือหน้า demo

### P2 — Feature คู่กัน (API + UI)

**2A Profile**
- ตาราง/ฟิลด์: employeeCode, birthDate, address, emergencyContact, เอกสารแนบ
- Admin: แก้ในหน้าพนักงาน
- Mobile: ดู/แก้โปรไฟล์ตัวเองตามสิทธิ์

**2B Timestamp approval**
- ขยาย timestamp: `note`, `approvalStatus` (NONE/PENDING/APPROVED/REJECTED), `approvedBy`, `approvedAt`, `rejectReason`
- นอกพื้นที่ → PENDING + บังคับ note
- Admin: คิวอนุมัติ (แทน warning stub)
- Mobile: กรอกเหตุผล + เห็นสถานะในประวัติ

**Done:** enroll/check-in เดิมยังทำงาน; โปรไฟล์และอนุมัติครบ flow

### P3 — Docs + commit
- อัปเดต `docs/API.md`, `ARCHITECTURE.md`
- Commit ตามช่วงงาน

## ลำดับทำ

```
1. P0 cleanup (mobile แล้ว admin)
2. P1 design tokens + shells
3. P2 API migration (profile + timestamp fields)
4. P2 Admin UI (profile form + approval queue)
5. P2 Mobile UI (note on check-in + profile + history status)
```

## นอกขอบเขตรอบนี้
- เปลี่ยนเป็น Next.js / Vite
- Leave/OT, e-document จริง, audit/CSV (ยังอยู่ใน BACKLOG)
