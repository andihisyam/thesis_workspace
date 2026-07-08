# Collaboration Service

Service ini menyinkronkan Monaco Editor melalui protokol Yjs WebSocket.

```powershell
cd collaboration
npm install
npm run dev
```

Default URL adalah `ws://127.0.0.1:1234`. Update Yjs disimpan di folder lokal
`collaboration/data/`, sedangkan snapshot yang dianggap versi resmi tetap
disimpan melalui tombol Save ke backend V2.

Room dibatasi per file:

```text
project:{project_id}:workspace:{workspace_id}:file:{relative_path}
```

Service ini ditujukan untuk jaringan privat. Sebelum dibuka ke internet,
tambahkan validasi session pada handshake WebSocket.
