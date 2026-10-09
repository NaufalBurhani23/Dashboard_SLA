# Bugfix — Unit Filter Direct Switch

## Problem
Pada `Capaian SLA per Unit`, ketika unit yang sedang dipilih (misalnya `Kantor Pusat`) ingin diganti langsung ke `UID Jabar`, dropdown hanya berisi unit yang sedang aktif. User harus memilih `Semua Unit` terlebih dahulu.

## Root Cause
Frontend mengirim `tableUnit` ke endpoint dashboard. Backend kemudian mengembalikan `unit_table` yang sudah terfilter ke unit aktif. Komponen `UnitTable` membangun daftar opsi dropdown dari `rows`, sehingga setelah filter aktif daftar opsi hanya berisi unit tersebut.

## Fix
- `tableUnit` tidak lagi dikirim ke API dashboard.
- API tetap mengembalikan seluruh statistik unit.
- Filtering `Capaian SLA per Unit` dilakukan di frontend.
- Daftar opsi dropdown selalu berasal dari seluruh unit yang tersedia.
- `tableUnit` tidak lagi menjadi dependency reload API.
- Filter trend tetap terpisah menggunakan `trendUnit`.

## Expected Behavior
Dari unit mana pun:

`Kantor Pusat` → `UID Jabar`

atau

`UID Jabar` → `UID SBU`

dapat dilakukan langsung tanpa kembali ke `Semua Unit`.

Perhitungan SLA 1, SLA 2, dan SLA 4 tidak diubah.
