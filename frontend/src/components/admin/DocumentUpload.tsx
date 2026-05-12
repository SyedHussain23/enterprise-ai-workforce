import { useState, useRef, type DragEvent } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { uploadDocument } from '../../api/client';
import { Spinner } from '../shared/Spinner';
import clsx from 'clsx';

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

export function DocumentUpload() {
  const [state, setState] = useState<UploadState>('idle');
  const [message, setMessage] = useState('');
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function processFile(file: File) {
    if (!file.name.endsWith('.pdf')) {
      setMessage('Only PDF files are supported.');
      setState('error');
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setMessage('File must be under 20MB.');
      setState('error');
      return;
    }

    setState('uploading');
    try {
      const res = await uploadDocument(file);
      setMessage(res.message ?? `Uploaded ${res.chunks} chunks.`);
      setState('success');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Upload failed.');
      setState('error');
    }
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }

  function reset() {
    setState('idle');
    setMessage('');
    if (inputRef.current) inputRef.current.value = '';
  }

  return (
    <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-4 h-4 text-indigo-600" />
        <h3 className="text-sm font-semibold text-slate-700">Document Upload</h3>
        <span className="ml-auto text-xs text-slate-400">PDF only · max 20MB</span>
      </div>

      {state === 'idle' && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={clsx(
            'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors',
            dragging
              ? 'border-indigo-400 bg-indigo-50'
              : 'border-slate-200 hover:border-indigo-300 hover:bg-slate-50',
          )}
        >
          <Upload className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm text-slate-600 font-medium">Drop PDF here or click to browse</p>
          <p className="text-xs text-slate-400 mt-1">Knowledge base auto-updates on upload</p>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            onChange={handleChange}
            className="hidden"
          />
        </div>
      )}

      {state === 'uploading' && (
        <div className="flex flex-col items-center justify-center py-8 gap-3">
          <Spinner className="w-6 h-6 text-indigo-600" />
          <p className="text-sm text-slate-600">Processing PDF and embedding chunks…</p>
        </div>
      )}

      {state === 'success' && (
        <div className="rounded-xl bg-emerald-50 p-4 text-center">
          <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
          <p className="text-sm font-medium text-emerald-700">{message}</p>
          <button onClick={reset} className="mt-3 text-xs text-emerald-600 underline">
            Upload another
          </button>
        </div>
      )}

      {state === 'error' && (
        <div className="rounded-xl bg-red-50 p-4 text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-sm font-medium text-red-700">{message}</p>
          <button onClick={reset} className="mt-3 text-xs text-red-600 underline">
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
