import { useState } from 'react';
import { addMember } from '../api/groups';
import toast from 'react-hot-toast';

const SEED_MEMBERS = [
  { display_name: 'Aisha', member_type: 'flatmate', joined_on: '2026-02-01', aliases: [] },
  { display_name: 'Rohan', member_type: 'flatmate', joined_on: '2026-02-01', aliases: ['rohan'] },
  { display_name: 'Priya', member_type: 'flatmate', joined_on: '2026-02-01', aliases: ['priya', 'Priya S'] },
  { display_name: 'Meera', member_type: 'flatmate', joined_on: '2026-02-01', left_on: '2026-03-31', aliases: [] },
  { display_name: 'Sam', member_type: 'flatmate', joined_on: '2026-04-08', aliases: [] },
];

export default function MembersPanel({ groupId, members, onRefresh }) {
  const [name, setName] = useState('');
  const [type, setType] = useState('flatmate');
  const [joinedOn, setJoinedOn] = useState('2026-02-01');
  const [leftOn, setLeftOn] = useState('');
  const [aliases, setAliases] = useState('');
  const [adding, setAdding] = useState(false);
  const [seeding, setSeeding] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAdding(true);
    try {
      const payload = {
        display_name: name,
        member_type: type,
        joined_on: joinedOn,
        aliases: aliases.split(',').map(s => s.trim()).filter(Boolean),
      };
      if (leftOn) payload.left_on = leftOn;
      await addMember(groupId, payload);
      toast.success('Member added');
      setName(''); setAliases(''); setLeftOn('');
      onRefresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    try {
      let added = 0;
      for (const member of SEED_MEMBERS) {
        if (members.some(m => m.display_name === member.display_name)) continue;
        await addMember(groupId, member);
        added++;
      }
      toast.success(added ? `Added ${added} flatmates` : 'Flatmates already exist');
      onRefresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="glass-card animate-fade-in" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <span className="eyebrow">Members</span>
          <h2>Membership Windows</h2>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={handleSeed} disabled={seeding}>
          {seeding ? '...' : '⚡ Seed Flatmates'}
        </button>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px', marginBottom: '16px' }}>
        <label className="form-label">
          Name
          <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="Aisha" required />
        </label>
        <label className="form-label">
          Type
          <select className="input select-input" value={type} onChange={e => setType(e.target.value)}>
            <option value="flatmate">Flatmate</option>
            <option value="guest">Guest</option>
          </select>
        </label>
        <label className="form-label">
          Joined
          <input className="input" type="date" value={joinedOn} onChange={e => setJoinedOn(e.target.value)} required />
        </label>
        <label className="form-label">
          Left
          <input className="input" type="date" value={leftOn} onChange={e => setLeftOn(e.target.value)} />
        </label>
        <label className="form-label" style={{ gridColumn: '1 / -1' }}>
          Aliases (comma-separated)
          <input className="input" value={aliases} onChange={e => setAliases(e.target.value)} placeholder="priya, Priya S" />
        </label>
        <button className="btn btn-primary" type="submit" disabled={adding} style={{ gridColumn: '1 / -1' }}>
          {adding ? 'Adding...' : 'Add Member'}
        </button>
      </form>

      {members.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '16px' }}>No members yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Member</th>
                <th>Active Window</th>
                <th>Aliases</th>
              </tr>
            </thead>
            <tbody>
              {members.map(member => (
                <tr key={member.id}>
                  <td>
                    <strong>{member.display_name}</strong>
                    <br />
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{member.member_type}</span>
                  </td>
                  <td>
                    {member.memberships?.map((m, i) => (
                      <div key={i} style={{ fontSize: '0.85rem' }}>
                        {m.joined_on} → {m.left_on || 'present'}
                      </div>
                    ))}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    {member.aliases?.map(a => a.raw_name).join(', ') || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
