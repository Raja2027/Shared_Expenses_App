import { useState } from 'react';
import { resolveAnomaly } from '../api/imports';
import toast from 'react-hot-toast';

const SEVERITY_BADGE = {
  error: 'badge-danger',
  review: 'badge-warning',
  warning: 'badge-neutral',
};

const STATUS_BADGE = {
  open: 'badge-info',
  approved: 'badge-success',
  rejected: 'badge-danger',
  ignored: 'badge-neutral',
};

export default function AnomalyList({ groupId, batchId, anomalies, onReportUpdate }) {
  const [filter, setFilter] = useState('open');
  const [resolving, setResolving] = useState(null);

  const filtered = filter === 'all'
    ? anomalies
    : anomalies.filter(a => a.resolution_status === filter);

  const handleResolve = async (anomalyId, status) => {
    setResolving(anomalyId);
    try {
      const updatedReport = await resolveAnomaly(groupId, batchId, anomalyId, status);
      toast.success(`Anomaly ${status}`);
      onReportUpdate(updatedReport);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setResolving(null);
    }
  };

  return (
    <div className="glass-card animate-fade-in" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <span className="eyebrow">Anomalies</span>
          <h2>Review Queue</h2>
        </div>
        <select className="input select-input" value={filter} onChange={e => setFilter(e.target.value)} style={{ width: 'auto', minWidth: '120px' }}>
          <option value="open">Open</option>
          <option value="all">All</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="ignored">Ignored</option>
        </select>
      </div>

      <div style={{ display: 'grid', gap: '10px', maxHeight: '520px', overflowY: 'auto', paddingRight: '4px' }}>
        {filtered.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px' }}>
            No anomalies in this view.
          </p>
        ) : (
          filtered.map(anomaly => {
            const canResolve = anomaly.requires_user_approval && anomaly.resolution_status === 'open';
            const isResolving = resolving === anomaly.id;
            return (
              <div key={anomaly.id} className="animate-fade-in" style={{
                background: 'var(--bg-glass)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '14px',
                display: 'grid',
                gap: '8px',
              }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  <span className="badge badge-accent">Row {anomaly.raw_row_number}</span>
                  <span className={`badge ${SEVERITY_BADGE[anomaly.severity] || 'badge-neutral'}`}>{anomaly.severity}</span>
                  <span className={`badge ${STATUS_BADGE[anomaly.resolution_status] || 'badge-neutral'}`}>{anomaly.resolution_status}</span>
                </div>
                <div>
                  <strong style={{ fontSize: '0.9rem' }}>{anomaly.code}</strong>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: '8px' }}>{anomaly.field_name}</span>
                </div>
                <p style={{ fontSize: '0.85rem', margin: 0 }}>{anomaly.message}</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0, fontStyle: 'italic' }}>{anomaly.suggested_action}</p>
                {canResolve && (
                  <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                    <button className="btn btn-primary btn-sm" disabled={isResolving} onClick={() => handleResolve(anomaly.id, 'approved')}>
                      ✓ Approve
                    </button>
                    <button className="btn btn-secondary btn-sm" disabled={isResolving} onClick={() => handleResolve(anomaly.id, 'ignored')}>
                      Skip
                    </button>
                    <button className="btn btn-danger btn-sm" disabled={isResolving} onClick={() => handleResolve(anomaly.id, 'rejected')}>
                      ✗ Reject
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
