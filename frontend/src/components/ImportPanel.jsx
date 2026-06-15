import { useRef, useState } from 'react';
import { uploadCsv, fetchImportReport } from '../api/imports';
import KpiCard from './KpiCard';
import toast from 'react-hot-toast';

export default function ImportPanel({ groupId, imports, selectedReport, onReportSelect, onRefresh }) {
  const fileRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    const file = fileRef.current?.files[0];
    if (!file) { toast.error('Choose a CSV file first'); return; }
    setUploading(true);
    try {
      const report = await uploadCsv(groupId, file);
      toast.success('CSV imported — review anomalies');
      onReportSelect(report);
      onRefresh();
      fileRef.current.value = '';
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleBatchClick = async (batchId) => {
    try {
      const report = await fetchImportReport(groupId, batchId);
      onReportSelect(report);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const summary = selectedReport?.summary || {};
  const rowStatus = summary.row_status_counts || summary.status_counts || {};

  return (
    <div className="glass-card animate-fade-in" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <span className="eyebrow">CSV</span>
          <h2>Import Report</h2>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input ref={fileRef} type="file" accept=".csv,text/csv" className="input" style={{ width: 'auto', maxWidth: '200px', fontSize: '0.8rem' }} />
          <button className="btn btn-primary btn-sm" onClick={handleUpload} disabled={uploading}>
            {uploading ? 'Uploading...' : '↑ Upload'}
          </button>
        </div>
      </div>

      {/* Batch List */}
      {imports.length > 0 && (
        <div style={{ display: 'grid', gap: '8px', marginBottom: '16px', maxHeight: '160px', overflowY: 'auto' }}>
          {imports.map(batch => (
            <button
              key={batch.id}
              onClick={() => handleBatchClick(batch.id)}
              className="btn btn-secondary btn-sm"
              style={{
                justifyContent: 'space-between',
                width: '100%',
                textAlign: 'left',
                borderColor: selectedReport?.batch?.id === batch.id ? 'var(--accent)' : undefined,
                background: selectedReport?.batch?.id === batch.id ? 'var(--accent-muted)' : undefined,
              }}
            >
              <strong>{batch.filename}</strong>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                {batch.status} · {batch.summary?.total_rows || 0} rows
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Summary KPIs */}
      {selectedReport && (
        <div className="kpi-grid">
          <KpiCard label="Rows" value={summary.total_rows || selectedReport.rows?.length || 0} />
          <KpiCard label="Anomalies" value={selectedReport.anomalies?.length || 0} />
          <KpiCard label="Open" value={summary.open_required_anomalies ?? '—'} />
          <KpiCard label="Ready" value={rowStatus.ready_to_import || 0} />
        </div>
      )}

      {!selectedReport && imports.length === 0 && (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '16px' }}>
          No imports yet. Upload a CSV to get started.
        </p>
      )}
    </div>
  );
}
