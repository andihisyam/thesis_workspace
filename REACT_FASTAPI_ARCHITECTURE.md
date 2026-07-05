# React + FastAPI System Design

## Tujuan

Migrasi bertahap dari prototipe `Streamlit` ke:

- `frontend/` untuk React + Vite + TypeScript
- `backend/` untuk FastAPI

## Visual Direction

Palette utama:

- `#99ff99`
- `#6bb36b`
- `#99ffff`
- `#d6ff99`
- `#96b36b`

Peran warna:

- `#6bb36b`: tombol utama, aksen heading
- `#99ff99`: badge sukses, selected state
- `#99ffff`: info panel dan compare accents
- `#d6ff99`: latar panel lembut
- `#96b36b`: sidebar dan border aksen

## Frontend Pages

- `Dashboard`
- `Review Draft`
- `Draft Manager`
- `Compile & Compare`

## Backend Endpoints

- `GET /api/health`
- `GET /api/documents`
- `GET /api/documents/{file_name}/structure`
- `POST /api/review`
- `POST /api/revision-draft`
- `GET /api/revision-drafts`
- `POST /api/revision-drafts/save`
- `POST /api/compile/original`
- `POST /api/compile/compare`

## Migration Notes

- Logic Python lama tetap dipakai lewat import dari root `app/services`.
- Streamlit lama belum dihapus agar migrasi tetap aman.
- Frontend React saat ini masih scaffold visual dan belum dihubungkan penuh ke API.
