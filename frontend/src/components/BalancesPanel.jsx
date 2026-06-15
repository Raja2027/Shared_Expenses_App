import { useState } from 'react';
import { fetchBalances } from '../api/imports';
import KpiCard from './KpiCard';
import LoadingSpinner from './LoadingSpinner';
import toast from 'react-hot-toast';

function money(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(value || 0));
}

export default function BalancesPanel({ groupId, batchId }) {
  const [balances, setBalances] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCalculate = async () => {
    if (!batchId) { toast.error('Select an import first'); return; }
    setLoading(true);
    try {
      const data = await fetchBalances(groupId, batchId);
      setBalances(data);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const maxAbs = balances
    ? Math.max(1, ...balances.balances.map(b => Math.abs(Number(b.net_balance_inr || 0))))
    : 1;

  return (
    <div className="glass-card animate-fade-in" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <span className="eyebrow">Balances</span>
          <h2>Traceable Preview</h2>
        </div>
        <button className="btn btn-primary btn-sm" onClick={handleCalculate} disabled={loading || !batchId}>
          {loading ? 'Calculating...' : '⚡ Calculate'}
        </button>
      </div>

      {loading && <LoadingSpinner text="Calculating balances..." />}

      {!loading && !balances && (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px' }}>
          Click Calculate to generate balance preview.
        </p>
      )}

      {balances && !loading && (
        <>
          <div className="kpi-grid" style={{ marginBottom: '16px' }}>
            <KpiCard label="Included" value={balances.included_row_count} />
            <KpiCard label="Excluded" value={balances.excluded_row_count} />
            <KpiCard label="Skipped" value={balances.skipped_row_count} />
            <KpiCard label="Traces" value={balances.traces.length} />
          </div>

          <div className="table-wrap" style={{ marginBottom: '20px' }}>
            <table>
              <thead>
                <tr>
                  <th>Person</th>
                  <th>Paid</th>
                  <th>Owed</th>
                  <th>Net</th>
                  <th>Balance</th>
                </tr>
              </thead>
              <tbody>
                {balances.balances.map(item => {
                  const net = Number(item.net_balance_inr || 0);
                  const width = Math.max(4, Math.round((Math.abs(net) / maxAbs) * 100));
                  return (
                    <tr key={item.person}>
                      <td><strong>{item.person}</strong></td>
                      <td>{money(item.paid_inr)}</td>
                      <td>{money(item.owed_inr)}</td>
                      <td className={net >= 0 ? 'text-positive' : 'text-negative'}>
                        <strong>{money(item.net_balance_inr)}</strong>
                      </td>
                      <td style={{ minWidth: '120px' }}>
                        <div className="balance-bar-track">
                          <div className={`balance-bar-fill ${net >= 0 ? 'positive' : 'negative'}`} style={{ width: `${width}%` }} />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {balances.traces.length > 0 && (
            <>
              <span className="eyebrow" style={{ marginBottom: '8px' }}>Trace Detail</span>
              <div className="table-wrap" style={{ maxHeight: '360px', overflowY: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>Description</th>
                      <th>Paid By</th>
                      <th>Participant</th>
                      <th>Share</th>
                      <th>Split</th>
                    </tr>
                  </thead>
                  <tbody>
                    {balances.traces.slice(0, 80).map((trace, i) => (
                      <tr key={i}>
                        <td>{trace.raw_row_number}</td>
                        <td>{trace.description}</td>
                        <td>{trace.paid_by}</td>
                        <td>{trace.participant}</td>
                        <td>{money(trace.share_amount_inr)}</td>
                        <td><span className="badge badge-neutral">{trace.split_type}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
