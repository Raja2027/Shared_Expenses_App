export default function LoadingSpinner({ size = 'md', text }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', padding: '32px' }}>
      <div className={`spinner ${size === 'sm' ? 'spinner-sm' : ''}`} />
      {text && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{text}</p>}
    </div>
  );
}
