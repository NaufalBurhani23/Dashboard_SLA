# Dashboard Monitoring SLA — SLA 1 + SLA 2

Versi ini mempertahankan perhitungan **SLA 1** dan menambahkan engine **SLA 2A + SLA 2B** berdasarkan rumus Excel vendor dan pola manual yang sudah di-ACC.

## Stack
- Backend: Python 3.14 + FastAPI + SQLAlchemy + SQLite + pandas/openpyxl
- Frontend: React + TypeScript + Vite + Tailwind CSS

Backend:
```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:
```powershell
cd frontend
npm install
npm run dev
```

## Prinsip Perhitungan SLA 2

```text
RAW EXCEL
  ↓
Header Mapping berdasarkan NAMA HEADER (bukan posisi kolom)
  ↓
SLA 2A — formula Excel vendor
  ↓
SLA 2B — formula Excel vendor (tetap dihitung paralel)
  ↓
Manual Override SLA 2 — hanya pola yang sudah di-ACC
  ↓
SLA 2 Final
```

**SLA 2 Final = Yes apabila SLA 2A = Yes ATAU SLA 2B = Yes.**
Jika tidak ada Yes, maka Final = No bila salah satu formula = No; selain itu Final = N/A.

### SLA 2A
- Hanya **Format Arsip = Fisik** pada jalur formula vendor.
- Document Type: `Inaktif`, atau `Aktif` dengan Tanggal/Jam Penjadwalan Arsip Inaktif terisi.
- Period gate mengikuti formula vendor Agustus.
- START = Tanggal Verifikasi UU jika tersedia; jika tidak, Tanggal Verifikasi UF; jika tidak, Tanggal Registrasi.
- END = Tanggal Penjadwalan Arsip Inaktif.
- `NETWORKDAYS(START, X, holiday) - 1 <= 2` → Yes; selain itu No.

### SLA 2B
Urutan jalur formula mengikuti Excel:

1. `Tanggal Registrasi 2` → `Tanggal Penjadwalan Arsip Inaktif 2`
2. `Tanggal Gagal Penjemputan` → `Tanggal Penjadwalan Arsip Inaktif 2`
3. `Tanggal Penolakan Jadwal Penjemputan` → `Tanggal Penjadwalan Arsip Inaktif 2`

Setiap jalur menghitung `NETWORKDAYS(START, AJ, holiday) - 1`. Nilai `< 2` = Yes; nilai `= 2` hanya Yes bila jam AK <= cutoff 10:00; selain itu No.

## Manual Override SLA 2 yang sudah di-ACC

### SLA 2A
- ELARCH + Ready To Pick Up + `-` + Runner + Fisik + Inaktif.
- ELARCH + Scheduled + `-` + MSB / Unit Fungsi + Fisik + Inaktif.
- ELARCH + Diarsipkan + `-` + Record Center + Digital + Inaktif, **hanya** jika Tanggal/Jam Penjadwalan Arsip Inaktif terisi.

### SLA 2B
- ELARCH + Pickup Failed + `-` + blank + Fisik + Inaktif.
- ELARCH + Diarsipkan + `-` + Record Center + Fisik + Inaktif.
- ELARCH + Ready To Pick Up + `-` + Runner + Fisik + Inaktif.
- ELARCH + Scheduled + Diverifikasi Unit Umum + MSB / Unit Fungsi + Fisik + Aktif.
- ELARCH + Scheduled + `-` + MSB / Unit Fungsi + Fisik + Inaktif.
- ELARCH + On Location + `-` + Runner + Fisik + Inaktif.
- ELARCH + Diarsipkan + Diverifikasi Unit Umum + Record Center + Fisik + Inaktif.
- ELARCH + Ready To Pick Up + Diverifikasi Unit Umum + Runner + Fisik + Aktif.
- ELARCH + On Location + Diverifikasi Unit Umum + Runner + Fisik + Aktif.

Semua pola manual SLA 2 wajib menghormati **period gate**. Pola khusus record yang masih menunggu validasi mentor **tidak dibuat sebagai rule**.

## Raw Excel dan Header Mapping
Parser memetakan berdasarkan nama header, bukan huruf Excel. Field SLA 2 yang dibaca antara lain:
- Tanggal/Jam Registrasi
- Tanggal/Jam Verifikasi UF dan UU
- Tanggal/Jam Penjadwalan Arsip Inaktif
- Tanggal/Jam Registrasi 2
- Tanggal/Jam Gagal Penjemputan
- Tanggal/Jam Penolakan Jadwal Penjemputan
- Tanggal/Jam Penjadwalan Arsip Inaktif 2

Kolom hasil vendor seperti **AW/AY** atau kolom hasil setelah AS tidak menjadi source of truth produksi.

## Holiday Calendar
Menu **Kalender Hari Libur** tetap menjadi sumber hari kerja manual yang dikontrol pengguna. Tidak ada auto-fetch internet. Holiday Calendar Version disimpan bersama hasil kalkulasi.

## Database
Database SQLite di paket adalah database development yang dapat dibuat ulang. Pada import, dataset pada `reporting_period` yang sama diganti agar tidak terjadi duplikasi.

## API SLA 2
- `GET /api/monitoring/sla2/summary`
- `GET /api/monitoring/sla2/traceability`

Endpoint import tetap menghitung SLA 1 dan SLA 2 sekaligus.

## Validasi
Unit test SLA 2 tersedia di `backend/tests/test_sla2_flow.py`. Test mencakup formula 2A/2B, period gate, manual override yang di-ACC, cutoff 10:00, final OR, dan memastikan pola pending `Ditolak Command Center` tidak dibuat sebagai manual rule.

## Dashboard SLA 1 & SLA 2 (6 Oktober 2026)
Mode `Semua SLA` hanya menampilkan akumulasi SLA 1/SLA 2 dan tabel Capaian SLA per Unit. Status Sinkronisasi, chart, ranking, dan tren harian hanya tampil ketika `SLA 1` atau `SLA 2` dipilih.

SLA 1 memakai implementasi baseline 1 Oktober yang sudah direvalidasi. SLA 2 memakai rumus SLA 2A/SLA 2B + 3 pola manual SLA 2A dan 9 pola manual SLA 2B yang telah di-ACC. Rule baru untuk kasus pending mentor tidak digeneralisasi.
