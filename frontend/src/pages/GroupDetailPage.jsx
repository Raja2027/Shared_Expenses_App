import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchGroupDetail, fetchMembers } from '../api/groups';
import { fetchImports, fetchImportReport } from '../api/imports';
import Navbar from '../components/Navbar';
import MembersPanel from '../components/MembersPanel';
import ImportPanel from '../components/ImportPanel';
import AnomalyList from '../components/AnomalyList';
import BalancesPanel from '../components/BalancesPanel';
import LoadingSpinner from '../components/LoadingSpinner';
import toast from 'react-hot-toast';
import './GroupDetailPage.css';

export default function GroupDetailPage() {
  const { groupId } = useParams();
  const [group, setGroup] = useState(null);
  const [members, setMembers] = useState([]);
  const [imports, setImports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [activeTab, setActiveTab] = useState('members');
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [groupData, membersData, importsData] = await Promise.all([
        fetchGroupDetail(groupId),
        fetchMembers(groupId),
        fetchImports(groupId),
      ]);
      setGroup(groupData);
      setMembers(membersData);
      const batches = importsData.batches || [];
      setImports(batches);

      if (batches.length > 0 && !selectedReport) {
        const report = await fetchImportReport(groupId, batches[0].id);
        setSelectedReport(report);
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => {
    setLoading(true);
    setSelectedReport(null);
    loadData();
  }, [groupId, loadData]);

  const refreshMembers = async () => {
    const data = await fetchMembers(groupId);
    setMembers(data);
  };

  const refreshImports = async () => {
    const data = await fetchImports(groupId);
    setImports(data.batches || []);
  };

  if (loading) {
    return (
      <div className="group-layout">
        <Navbar />
        <main className="group-main">
          <LoadingSpinner text="Loading group..." />
        </main>
      </div>
    );
  }

  const tabs = [
    { key: 'members', label: 'Members', count: members.length },
    { key: 'imports', label: 'Imports', count: imports.length },
    { key: 'balances', label: 'Balances' },
  ];

  return (
    <div className="group-layout">
      <Navbar />
      <main className="group-main">
        <div className="group-header animate-fade-in">
          <div>
            <Link to="/" className="group-back">← Dashboard</Link>
            <h1>{group?.name || `Group ${groupId}`}</h1>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={loadData}>↻ Refresh</button>
        </div>

        {/* Tab Navigation */}
        <div className="group-tabs animate-fade-in">
          {tabs.map(tab => (
            <button
              key={tab.key}
              className={`group-tab ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
              {tab.count != null && <span className="tab-count">{tab.count}</span>}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="group-content">
          {activeTab === 'members' && (
            <MembersPanel groupId={groupId} members={members} onRefresh={refreshMembers} />
          )}

          {activeTab === 'imports' && (
            <div style={{ display: 'grid', gap: '16px' }}>
              <ImportPanel
                groupId={groupId}
                imports={imports}
                selectedReport={selectedReport}
                onReportSelect={setSelectedReport}
                onRefresh={refreshImports}
              />
              {selectedReport && (
                <AnomalyList
                  groupId={groupId}
                  batchId={selectedReport.batch.id}
                  anomalies={selectedReport.anomalies || []}
                  onReportUpdate={setSelectedReport}
                />
              )}
            </div>
          )}

          {activeTab === 'balances' && (
            <BalancesPanel
              groupId={groupId}
              batchId={selectedReport?.batch?.id}
            />
          )}
        </div>
      </main>
    </div>
  );
}
