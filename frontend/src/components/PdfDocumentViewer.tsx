import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

const MIN_ZOOM = 0.75;
const MAX_ZOOM = 1.25;
const ZOOM_STEP = 0.125;
const MAX_BASE_PAGE_WIDTH = 720;

type PdfDocumentViewerProps = {
  title: string;
  pdfUrl: string;
};

export default function PdfDocumentViewer({ title, pdfUrl }: PdfDocumentViewerProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [numPages, setNumPages] = useState(0);
  const [pageWidth, setPageWidth] = useState(560);
  const [zoom, setZoom] = useState(1);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    const updateWidth = () => {
      const availableWidth = Math.floor(viewport.clientWidth - 32);
      setPageWidth(Math.max(280, Math.min(MAX_BASE_PAGE_WIDTH, availableWidth)));
    };
    updateWidth();

    const observer = new ResizeObserver(updateWidth);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setNumPages(0);
    setZoom(1);
    setLoadError("");
  }, [pdfUrl]);

  if (!pdfUrl) {
    return <div className="pdf-placeholder">{title} belum tersedia.</div>;
  }

  return (
    <section className="web-pdf-viewer" aria-label={title}>
      <div className="web-pdf-toolbar">
        <span>
          {numPages ? numPages + " halaman" : "Memuat dokumen..."}
        </span>
        <div className="web-pdf-zoom">
          <button
            type="button"
            aria-label="Perkecil tampilan"
            onClick={() => setZoom((value) => Math.max(MIN_ZOOM, value - ZOOM_STEP))}
            disabled={zoom <= MIN_ZOOM}
          >
            -
          </button>
          <span>{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            aria-label="Perbesar tampilan"
            onClick={() => setZoom((value) => Math.min(MAX_ZOOM, value + ZOOM_STEP))}
            disabled={zoom >= MAX_ZOOM}
          >
            +
          </button>
        </div>
      </div>

      <div ref={viewportRef} className="web-pdf-viewport">
        {loadError ? (
          <div className="pdf-placeholder">Preview gagal dimuat. Silakan compile kembali.</div>
        ) : (
          <Document
            file={pdfUrl}
            loading={<div className="pdf-placeholder">Memuat hasil compile...</div>}
            onLoadSuccess={({ numPages: loadedPages }) => setNumPages(loadedPages)}
            onLoadError={() => setLoadError("PDF gagal dimuat.")}
          >
            <div className="web-pdf-pages">
              {Array.from({ length: numPages }, (_, index) => {
                const pageNumber = index + 1;
                return (
                  <div className="web-pdf-page" key={pageNumber}>
                    <Page
                      pageNumber={pageNumber}
                      width={pageWidth * zoom}
                      renderAnnotationLayer={false}
                      renderTextLayer
                      loading={<div className="web-pdf-page-loading">Memuat halaman {pageNumber}...</div>}
                    />
                    <span className="web-pdf-page-number">Halaman {pageNumber}</span>
                  </div>
                );
              })}
            </div>
          </Document>
        )}
      </div>
    </section>
  );
}
