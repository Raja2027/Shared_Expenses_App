export default function EmptyState({ icon = '📋', title, message }) {
  return (
    <div className="animate-fade-in" style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '12px',
      padding: '48px 24px',
      textAlign: 'center',
    }}>
      <span style={{ fontSize: '2.5rem' }}>{icon}</span>
      <h3 style={{ color: 'var(--text-primary)' }}>{title}</h3>
      {message && <p style={{ color: 'var(--text-muted)', maxWidth: '320px' }}>{message}</p>}
    </div>
  );
}
