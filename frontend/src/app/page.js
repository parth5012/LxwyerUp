'use client';

import { useState, useEffect } from 'react';

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/cases')
      .then((res) => res.json())
      .then((data) => {
        setCases(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching cases:', err);
        setLoading(false);
      });
  }, []);

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'Arbitration Analysis':
        return 'badge-blue';
      case 'Drafting Documents':
        return 'badge-yellow';
      case 'E-Filing':
        return 'badge-blue';
      case 'Completed':
        return 'badge-green';
      default:
        return 'badge-secondary';
    }
  };

  return (
    <div className="animated-fadeIn">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div>
          <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>Case Dashboard</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Monitor active dispute processes, drafts, and court filings.</p>
        </div>
        <a href="/cases/new" className="btn btn-primary">
          ➕ File New Claim
        </a>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div style={{ color: 'var(--text-secondary)' }}>Loading case profiles...</div>
        </div>
      ) : cases.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '50px 20px', borderStyle: 'dashed' }}>
          <h3 style={{ marginBottom: '10px' }}>No active cases found</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>Initiate your first claim to start the multi-agent legal pipeline.</p>
          <a href="/cases/new" className="btn btn-primary">
            Initiate Dispute Claim
          </a>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '25px' }}>
          {cases.map((c) => (
            <div key={c.id} className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' }}>
                <span className={`badge ${getStatusBadgeClass(c.status)}`}>
                  {c.status}
                </span>
                <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  ID: #{c.id}
                </span>
              </div>
              
              <h3 style={{ fontSize: '18px', marginBottom: '10px', color: '#fff' }}>{c.title}</h3>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', flex: 1, marginBottom: '20px', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {c.description}
              </p>

              <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '15px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Claimant:</span>
                  <span style={{ fontWeight: 600 }}>{c.claimant_name}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Respondent:</span>
                  <span style={{ fontWeight: 600 }}>{c.respondent_name}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Value:</span>
                  <span style={{ fontWeight: 600, color: 'var(--color-warning)' }}>${c.dispute_amount.toLocaleString()}</span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <a href={`/cases/${c.id}/arbitration`} className="btn btn-secondary" style={{ flex: 1, padding: '8px' }}>
                  ⚖️ Agent Chat
                </a>
                <a href={`/cases/${c.id}/drafting`} className="btn btn-secondary" style={{ flex: 1, padding: '8px' }}>
                  📝 Drafts
                </a>
                <a href={`/cases/${c.id}/efiling`} className="btn btn-primary" style={{ flex: 1, padding: '8px' }}>
                  🚀 File Case
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
