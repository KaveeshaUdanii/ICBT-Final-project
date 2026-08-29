import { useState } from "react";
import type { AxiosResponse } from "axios";
import toast from "react-hot-toast";
import { CheckCircle2, Download, Upload, XCircle } from "lucide-react";
import { apiErrorMessage } from "../api/client";
import type { CsvImportResult } from "../types";
import { Modal } from "./ui/Modal";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";

function downloadTemplate(filename: string, columns: string[], exampleRow: (string | number)[]) {
  const csv = `${columns.join(",")}\n${exampleRow.join(",")}\n`;
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function CsvImportModal({
  open,
  onClose,
  title,
  description,
  templateFilename,
  templateColumns,
  templateExampleRow,
  importFn,
  onImported,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description: string;
  templateFilename: string;
  templateColumns: string[];
  templateExampleRow: (string | number)[];
  importFn: (file: File) => Promise<AxiosResponse<CsvImportResult>>;
  onImported: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<CsvImportResult | null>(null);

  function handleClose() {
    setFile(null);
    setResult(null);
    onClose();
  }

  async function handleImport() {
    if (!file) return;
    setImporting(true);
    try {
      const res = await importFn(file);
      setResult(res.data);
      if (res.data.imported > 0) {
        toast.success(`Imported ${res.data.imported} row(s).`);
        onImported();
      }
      if (res.data.failed > 0) {
        toast.error(`${res.data.failed} row(s) failed -- see details below.`);
      }
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setImporting(false);
    }
  }

  return (
    <Modal open={open} onClose={handleClose} title={title} width="max-w-xl">
      <p className="text-sm text-[var(--text-secondary)] mb-4">{description}</p>

      <button
        type="button"
        onClick={() => downloadTemplate(templateFilename, templateColumns, templateExampleRow)}
        className="flex items-center gap-1.5 text-xs text-indigo-500 hover:text-indigo-400 font-medium mb-4"
      >
        <Download className="h-3.5 w-3.5" /> Download a sample CSV template
      </button>

      <label className="glass-panel flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-white/15 px-4 py-8 cursor-pointer hover:border-indigo-400/40 transition">
        <Upload className="h-6 w-6 text-[var(--text-muted)]" />
        <span className="text-sm text-[var(--text-secondary)]">
          {file ? file.name : "Click to choose a .csv file"}
        </span>
        <input
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            setResult(null);
            setFile(e.target.files?.[0] ?? null);
          }}
        />
      </label>

      {result && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center gap-3">
            <Badge tone="success">
              <CheckCircle2 className="h-3.5 w-3.5" /> {result.imported} imported
            </Badge>
            {result.failed > 0 && (
              <Badge tone="danger">
                <XCircle className="h-3.5 w-3.5" /> {result.failed} failed
              </Badge>
            )}
          </div>
          {result.errors.length > 0 && (
            <div className="max-h-48 overflow-y-auto scrollbar-thin space-y-1.5 pr-1">
              {result.errors.map((e, i) => (
                <div key={i} className="glass-panel rounded-lg px-3 py-2 text-xs text-[var(--text-secondary)]">
                  <span className="font-semibold text-rose-400">Row {e.row}:</span> {e.error}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex justify-end gap-2 mt-6">
        <Button variant="secondary" onClick={handleClose}>
          {result ? "Close" : "Cancel"}
        </Button>
        <Button onClick={handleImport} loading={importing} disabled={!file}>
          <Upload className="h-4 w-4" /> Import
        </Button>
      </div>
    </Modal>
  );
}
