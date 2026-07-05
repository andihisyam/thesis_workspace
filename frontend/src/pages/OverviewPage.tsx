import PageHeader from "../components/PageHeader";
import PanelCard from "../components/PanelCard";

const workflow = [
  {
    number: "01",
    title: "Pilih bagian skripsi",
    detail: "Buka Review Draft, lalu pilih Bab, Sub bab, atau Sub sub bab yang ingin diperiksa."
  },
  {
    number: "02",
    title: "Review dan buat revisi",
    detail: "Jalankan review, baca ringkasan serta saran, kemudian buat draft revisi bila hasilnya sesuai."
  },
  {
    number: "03",
    title: "Kelola draft",
    detail: "Draft yang disimpan tersedia di Draft Manager dan tidak langsung mengubah source asli."
  },
  {
    number: "04",
    title: "Compile, bandingkan, dan edit",
    detail: "Bandingkan PDF bagian asli dan revisi, lalu edit LaTeX dengan preview fragmen di samping."
  }
];

export default function OverviewPage() {
  return (
    <div className="page-stack">
      <PageHeader
        badge="Overview"
        title="How It Works"
        description="Alur penggunaan sistem dari memilih bagian skripsi sampai menghasilkan PDF revisi."
      />

      <div className="workflow-grid">
        {workflow.map((step) => (
          <PanelCard key={step.number} title={step.title}>
            <div className="workflow-step">
              <span className="workflow-number">{step.number}</span>
              <p>{step.detail}</p>
            </div>
          </PanelCard>
        ))}
      </div>

      <div className="overview-note">
        <strong>Source asli tetap aman.</strong>
        <p>Perubahan disimpan sebagai draft terpisah sampai kamu memilih hasil revisi yang akan digunakan.</p>
      </div>
    </div>
  );
}
