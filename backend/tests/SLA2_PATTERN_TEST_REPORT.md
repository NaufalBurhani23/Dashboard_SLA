# SLA 2 Manual Pattern Test Report

Automated coverage for the currently approved SLA 2 manual override rules.

## SLA 2A

- A1 Ready To Pick Up + `-` + Runner + Fisik + Inaktif
- A1B Ready To Pick Up + Diverifikasi Unit Umum + Runner + Fisik + Inaktif
- A2 Scheduled + `-` + MSB / Unit Fungsi + Fisik + Inaktif
- A3 Diarsipkan + `-` + Record Center + Fisik + Inaktif
- A4 Pickup Failed + `-` + Posisi Data kosong + Fisik + Inaktif
- A5 On Location + `-` + Runner + Fisik + Inaktif
- A6 Registrasi Masuk + `-` + Command Center + Fisik + Inaktif
- A7 Status Registrasi prefix `Ditolak Command Center` + `-` + Posisi Data kosong + Fisik + Inaktif
- A8 Registrasi Masuk Lanjutan + Diverifikasi Unit Umum + Command Center + Fisik + Inaktif
- A9 Diarsipkan + Diverifikasi Unit Umum + Record Center + Fisik + Inaktif
- A10 Diarsipkan + `-` + Record Center + Digital + Inaktif + Tanggal/Jam Penjadwalan Arsip Inaktif + Tanggal/Jam Jadwal Penjemputan terisi

## SLA 2B

- B1–B9 previously approved patterns
- B10 VIP + Diarsipkan + Diverifikasi Unit Umum + Record Center + Fisik + Inaktif

## Pending

The special SLA 2B `Ditolak Command Center` exception and records outside the SLA 2B Period Gate remain intentionally unimplemented pending mentor validation.
