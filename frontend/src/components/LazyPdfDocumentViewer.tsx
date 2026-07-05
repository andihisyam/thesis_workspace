import { lazy, Suspense } from "react";

const PdfDocumentViewer = lazy(() => import("./PdfDocumentViewer"));

type LazyPdfDocumentViewerProps = {
  title: string;
  pdfUrl: string;
};

export default function LazyPdfDocumentViewer(props: LazyPdfDocumentViewerProps) {
  return (
    <Suspense fallback={<div className="pdf-placeholder">Menyiapkan viewer dokumen...</div>}>
      <PdfDocumentViewer {...props} />
    </Suspense>
  );
}
