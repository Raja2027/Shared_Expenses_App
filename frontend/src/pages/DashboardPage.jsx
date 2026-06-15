import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchGroups, createGroup } from '../api/groups';
import Navbar from '../components/Navbar';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import toast from 'react-hot-toast';
import './DashboardPage.css';

export default function DashboardPage() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const loadGroups = async () => {
    try {
      const data = await fetchGroups();
      setGroups(data);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadGroups(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await createGroup(name.trim());
      setName('');
      toast.success('Group created');
      loadGroups();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="dashboard-layout">
      <Navbar />
      <main className="dashboard-main">
        <div className="dashboard-header animate-fade-in">
          <div>
            <span className="eyebrow">Dashboard</span>
            <h1>Your Groups</h1>
          </div>
          <form onSubmit={handleCreate} className="dashboard-create-form">
            <input
              className="input"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="New group name..."
              required
            />
            <button className="btn btn-primary" type="submit" disabled={creating}>
              {creating ? '...' : '+ Create'}
            </button>
          </form>
        </div>

        {loading ? (
          <LoadingSpinner text="Loading groups..." />
        ) : groups.length === 0 ? (
          <EmptyState icon="🏠" title="No groups yet" message="Create your first group to start splitting expenses with flatmates." />
        ) : (
          <div className="groups-grid animate-fade-in">
            {groups.map((group, i) => (
              <button
                key={group.id}
                className="group-card glass-card"
                onClick={() => navigate(`/groups/${group.id}`)}
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <div className="group-card-icon">
                  {group.name.charAt(0).toUpperCase()}
                </div>
                <div className="group-card-body">
                  <h3>{group.name}</h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Created {new Date(group.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="group-card-arrow">→</span>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
