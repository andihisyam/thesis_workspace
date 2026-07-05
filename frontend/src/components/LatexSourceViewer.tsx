import { useRef } from "react";

type LatexSourceViewerProps = {
  title?: string;
  value: string;
  editable?: boolean;
  onChange?: (value: string) => void;
  minLines?: number;
};

export default function LatexSourceViewer({
  title,
  value,
  editable = false,
  onChange,
  minLines = 16
}: LatexSourceViewerProps) {
  const gutterRef = useRef<HTMLPreElement>(null);
  const lines = value.length ? value.split("\n") : [""];
  const lineNumbers = lines.map((_, index) => index + 1).join("\n");
  const syncLineNumbers = (scrollTop: number) => {
    if (gutterRef.current) {
      gutterRef.current.scrollTop = scrollTop;
    }
  };

  return (
    <div className="latex-source-viewer">
      {title ? <p className="field-label">{title}</p> : null}
      <div className="code-frame">
        <pre ref={gutterRef} className="code-gutter" aria-hidden="true">
          {lineNumbers}
        </pre>
        {editable ? (
          <textarea
            className="code-editor"
            value={value}
            onChange={(event) => onChange?.(event.target.value)}
            onScroll={(event) => syncLineNumbers(event.currentTarget.scrollTop)}
            spellCheck={false}
            rows={Math.max(lines.length, minLines)}
          />
        ) : (
          <pre
            className="code-content"
            onScroll={(event) => syncLineNumbers(event.currentTarget.scrollTop)}
          >
            {value}
          </pre>
        )}
      </div>
    </div>
  );
}
