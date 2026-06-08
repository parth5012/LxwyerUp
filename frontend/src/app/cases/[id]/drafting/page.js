'use client';

import { useState, useEffect, use } from 'react';

export default function DraftingWorkspace({ params: paramsPromise }) {
  const params = use(paramsPromise);
  const caseId = params.id;
  const [caseObj, setCaseObj] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [compiling, setCompiling] = useState(false);

  useEffect(() => {
    // Fetch Case details
    fetch(`http://localhost:8000/api/cases/${caseId}`)
      .then((res) => res.json())
      .then((data) => setCaseObj(data));

    // Fetch compiled drafts
    fetch(`http://localhost:8000/api/cases/${caseId}/drafts`)
      .then((res) => res.json())
      .then((data) => setDrafts(data));
  }, [caseId]);

  const handleCompileDraft = async () => {
    setCompiling(true);
    try {
      const res = await fetch(`http://localhost:8000/api/cases/${caseId}/drafts`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Compilation request failed');
      const newDraft = await res.json();
      setDrafts((prev) => [newDraft, ...prev]);
    } catch (err) {
      console.error(err);
      alert('Error triggering legal document compiler. Confirm backend connection.');
    } finally {
      setCompiling(false);
    }
  };

  const getDownloadUrl = (path) => {
    if (!path) return '#';
    // Static files are mapped to /static-files/ in the FastAPI backend
    const filename = path.split(/[\\/]/).pop();
    return `http://localhost:8000/static-files/drafts/${filename}`;
  };

  const getDocxDownloadUrl = (path) => {
    if (!path) return '#';
    const filename = path.split(/[\\/]/).pop().replace('.pdf', '.docx');
    return `http://localhost:8000/static-files/drafts/${filename}`;
  };

  if (!caseObj) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
        Loading Drafting Workspace...
      </div>
    );
  }

  const latestDraft = drafts[0];

  return (
    <div className="animated-fadeIn" style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '30px', height: 'calc(100vh - 80px)' }}>
      {/* Draft editor / preview */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '15px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span className="badge badge-yellow" style={{ marginBottom: '8px' }}>Agent 2: Drafting Engine</span>
            <h1 style={{ fontSize: '24px' }}>Draft Legal Documents</h1>
          </div>
          <button onClick={handleCompileDraft} className="btn btn-primary" disabled={compiling}>
            {compiling ? 'Compiling Legal Draft...' : '📝 Compile Legal Draft'}
          </button>
        </div>

        {/* Document Editor Sandbox */}
        <div className="card" style={{ flex: 1, overflowY: 'auto', background: '#0e0e12', padding: '30px', fontFamily: 'var(--font-inter)', color: '#fff', fontSize: '15px' }}>
          {!latestDraft ? (
            <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)', padding: '50px 0', maxWidth: '400px' }}>
              <p style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>No drafted files compiled</p>
              <p style={{ fontSize: '13px' }}>Click the "Compile Legal Draft" button to merge case facts with LxwyerUp standard Complaint statements.</p>
            </div>
          ) : (
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8' }}>
              <h2 style={{ fontSize: '20px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '10px', marginBottom: '20px' }}>
                {latestDraft.title}
              </h2>
              {latestDraft.content_markdown}
            </div>
          )}
        </div>
      </div>

      {/* Artifact Downloads & Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
        <div className="card">
          <h3 style={{ fontSize: '16px', marginBottom: '15px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            Compiled Documents
          </h3>
          {!latestDraft ? (
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Generate a draft to download PDF and DOCX files.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <a href={getDownloadUrl(latestDraft.file_path)} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={{ display: 'flex', justifyContent: 'flex-start' }}>
                📥 Download PDF Version
              </a>
              <a href={getDocxDownloadUrl(latestDraft.file_path)} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={{ display: 'flex', justifyContent: 'flex-start' }}>
                📥 Download Word (DOCX)
              </a>
            </div>
          )}
        </div>

        <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '15px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            Drafting History ({drafts.length})
          </h3>
          <div style={{ overflowY: 'auto', flex: 1, maxHeight: '250px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {drafts.map((d, index) => (
              <div key={d.id} style={{ padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', fontSize: '13px', cursor: 'pointer' }} onClick={() => setDrafts([d, ...drafts.filter(x => x.id !== d.id)])}>
                <div style={{ fontWeight: 600, color: index === 0 ? 'var(--color-primary)' : '#fff' }}>{d.title}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '4px' }}>
                  {new Date(d.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: 'auto' }}>
          <a href={`/cases/${caseId}/efiling`} className="btn btn-primary" style={{ width: '100%' }}>
            🚀 Move to E-Filing Agent
          </a>
          <a href={`/cases/${caseId}/arbitration`} className="btn btn-secondary" style={{ width: '100%' }}>
            Back to Case Analysis
          </a>
        </div>
      </div>
    </div>
  );
}
