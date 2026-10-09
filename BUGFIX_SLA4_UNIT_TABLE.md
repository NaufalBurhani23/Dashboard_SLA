# Bugfix SLA 4 - Capaian SLA per Unit

## Bug
Saat dropdown `Pilih SLA` memilih `SLA 4`, tabel **Capaian SLA per Unit** menampilkan semua unit tetapi nilainya `0% (0/0)`, walaupun summary SLA 4 sudah menunjukkan 6.684 On Time.

## Penyebab
`DashboardPage.tsx` mengubah data `SLA4UnitSummary` menjadi bentuk generik `DashboardUnitRow` yang berisi `total`, `denominator`, `on_time`, `out_of_date`, `incomplete`, dan `percentage` langsung.

Komponen `UnitTable` sebelumnya hanya membaca `row.sla4` ketika kode yang dipilih adalah `SLA 4`. Akibatnya data SLA 4 yang sudah benar tidak terbaca dan fallback menjadi `0`.

## Perbaikan
`UnitTable` sekarang mendukung dua bentuk data:
- `row.sla4` untuk unified table.
- field statistik langsung (`total`, `denominator`, `on_time`, `out_of_date`, `incomplete`, `percentage`) untuk dedicated SLA 4 table.

Logika perhitungan SLA 4A/SLA 4B tidak diubah.

## KPI denominator fix — 8 October 2026

- Dashboard KPI denominator is now the **entire record population**, including N/A, matching the SLA 1/SLA 2 convention.
- SLA 4 summary percentage is now `Yes / Total Records`, not `Yes / (Yes + No)`.
- SLA 4 per-unit percentage is also `Yes / Total Records for that unit`.
- The shared `Capaian SLA per Unit` table now supports the flat backend shape returned when SLA 1 or SLA 2 is selected, so SLA 1/SLA 2 no longer display `0% (0/0)` when real unit statistics exist.
- Example: a unit with `2,161 Yes` out of `3,176` total records will display approximately `68.04%`, not `100%`.
