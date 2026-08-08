# แผน: รีสไตล์ Angular + Profile + Timestamp approval

อัปเดตตามคำตอบล่าสุด:
- **คง Angular** (ไม่เปลี่ยนเป็น Next.js)
- **เปลี่ยนสไตล์ / รูปแบบเทมเพลต** (ทิ้ง ThemeForest look, ดีไซน์ใหม่บนโค้ดผลิตภัณฑ์)
- **ทำคู่กัน:** โปรไฟล์พนักงานละเอียด + อนุมัติ/หมายเหตุลงเวลา
- **ตัด Webview-Mobile** — ไม่ใช้แล้ว; check-in ใช้ admin kiosk อย่างเดียว

## สถานะงาน (อัปเดต)

- **P0** เสร็จ: ตัด demo routes/โฟลเดอร์ Admin, ย้าย reset-password Cover, เก็บเฉพาะ product routes
- **P1** เสร็จ (Admin): design tokens (`dpu-theme.css`), shared list UI kit, shell header/sidebar/content-layout, kiosk fullscreen (`dpu-kiosk-mode`), company/admin homes + dashboard
- **P2** เริ่มแล้ว / บางส่วนเสร็จ: API profile + approval fields, Admin คิวอนุมัติ (`warning-timestamp-log`)
- **Mobile app:** ลบออกจาก repo / compose / nginx แล้ว

## แนวทาง

ไม่ rewrite ทั้งแอปจากศูนย์แบบ stack ใหม่ — แต่:

1. **ตัด ThemeForest demo** ออกให้เหลือเฉพาะหน้า DPU / company
2. **ใส่ design system ใหม่** (CSS variables, layout shell, typography) ทับ shell เดิม
3. **ขยาย API + หน้า** สำหรับ profile และ timestamp approval

```
Web-Manage (Angular 17)     — รีสไตล์ + admin + face kiosk
API-Fast                    — ขยาย schema
```

## เฟสงาน

### P0 — คลีน template
**Done:** build ผ่าน; เมนูผลิตภัณฑ์ใช้ได้

### P1 — สไตล์ / เทมเพลตใหม่ (Admin)

**Done (Admin):**
- Tokens teal/slate ใน `dpu-theme.css` (`--dpu-brand`, glass header, sidebar gradient)
- Shared kit: `page-toolbar`, `pill-search`, `stat-chip`, `simple-pager`, `empty-state`, `location-map`, `dpu-list-page.css`
- List/CRUD มาตรฐาน: emp, timestamp-log, warning queue, location, company-info, department, position, member/company/admin-manage
- Shell: declutter header, slim company card sidebar, content padding; menus include dashboard + kiosk
- Special: kiosk fullscreen chrome; face-management dialog; company hub (`home-installer`); admin home; dashboard shortcuts/KPI
- Maps: OSM fallback เมื่อ Google Maps ถูกบล็อกบน localhost
- Global TTS speech templates: `/admin/system-setting`

### P2 — Feature คู่กัน (API + UI)

**2A Profile** — กำลัง/บางส่วน
- ฟิลด์โปรไฟล์พนักงาน (admin)

**2B Timestamp approval** — กำลัง/บางส่วน
- Admin คิวอนุมัติ (`/company/warning-timestamp-log`) รีดีไซน์แล้ว
- นอกพื้นที่ → PENDING + note

### P3 — Docs + commit
- อัปเดต `docs/API.md`, `ARCHITECTURE.md`, `CURSOR-AGENT.md`, rules/skills
- Commit ตามช่วงงาน

## ลำดับทำ (ปัจจุบัน)

```
1. P0 cleanup — done
2. P1 Admin design tokens + list UI + shell + kiosk chrome — done
3. Remove Webview-Mobile — done
4. P2 ปิดช่องว่าง profile + approval
5. Docs/rules sync เมื่อ convention เปลี่ยน
```

## นอกขอบเขตรอบนี้
- เปลี่ยนเป็น Next.js / Vite
- Leave/OT, e-document จริง, audit/CSV (ยังอยู่ใน BACKLOG)
- Auto-redirect company home → dashboard (hub ตั้งใจไว้)
- แอป mobile แยก (เลิกใช้แล้ว)
