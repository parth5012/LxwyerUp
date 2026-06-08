'use client';

import { useState, useEffect, useRef, use } from 'react';

export default function ArbitrationWorkspace({ params: paramsPromise }) {
  const params = use(paramsPromise);
  const caseId = params.id;
  const [caseObj, setCaseObj] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  
  const chatEndRef = useRef(null);

  useEffect(() => {
    // Fetch Case detail
    fetch(`http://localhost:8000/api/cases/${caseId}`)
      .then((res) => res.json())
      .then((data) => setCaseObj(data));

    // Fetch Chat history
    fetch(`http://localhost:8000/api/cases/${caseId}/chat`)
      .then((res) => res.json())
      .then((data) => setMessages(data));
  }, [caseId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || sending) return;

    setSending(true);
    // Optimistic user insert
    const userMsg = { sender: 'user', message: inputValue, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    const originalInput = inputValue;
    setInputValue('');

    try {
      const formData = new FormData();
      formData.append('message', originalInput);

      const res = await fetch(`http://localhost:8000/api/cases/${caseId}/chat`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Failed to get bot reply');
      const data = await res.json();
      
      setMessages((prev) => [...prev.filter(m => m.timestamp !== userMsg.timestamp), userMsg, data]);
    } catch (err) {
      console.error(err);
      alert('Error communicating with AI Supervisor. Check backend connection.');
    } finally {
      setSending(false);
    }
  };

  if (!caseObj) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
        Loading Arbitration Workspace...
      </div>
    );
  }

  return (
    <div className="animated-fadeIn" style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '30px', height: 'calc(100vh - 80px)' }}>
      {/* Chat Column */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '15px', marginBottom: '20px' }}>
          <span className="badge badge-blue" style={{ marginBottom: '8px' }}>Agent 1: Arbitration Engine</span>
          <h1 style={{ fontSize: '24px' }}>{caseObj.title}</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Discuss dispute claims, legal jurisdiction, and applicable regulations.</p>
        </div>

        {/* Chat Messages */}
        <div className="card" style={{ flex: 1, overflowY: 'auto', marginBottom: '20px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '15px', background: '#0e0e12' }}>
          {messages.length === 0 ? (
            <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)', maxWidth: '400px' }}>
              <p style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>Start legal analysis</p>
              <p style={{ fontSize: '13px' }}>Ask the co-pilot questions like: "What is the jurisdiction of this clause?" or "Does Rule 4 apply to my breach claim?"</p>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '75%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: m.sender === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  {m.sender === 'user' ? 'You' : '⚖️ Arbitration Agent'}
                </span>
                <div
                  style={{
                    background: m.sender === 'user' ? 'var(--color-primary)' : 'rgba(255, 255, 255, 0.04)',
                    color: '#fff',
                    padding: '12px 16px',
                    borderRadius: '12px',
                    border: m.sender === 'user' ? 'none' : '1px solid var(--border-color)',
                    fontSize: '14px',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {m.message}
                </div>
              </div>
            ))
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Chat Input */}
        <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            className="text-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Query case details or ask about arbitration rules..."
            disabled={sending}
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary" disabled={sending || !inputValue.trim()}>
            {sending ? 'Analyzing...' : 'Send'}
          </button>
        </form>
      </div>

      {/* Case Details Sidebar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
        <div className="card">
          <h3 style={{ fontSize: '16px', marginBottom: '12px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            Case Summary
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '15px' }}>{caseObj.description}</p>
          <div style={{ fontSize: '13px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Claimant:</span>
              <span style={{ fontWeight: 600 }}>{caseObj.claimant_name}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Respondent:</span>
              <span style={{ fontWeight: 600 }}>{caseObj.respondent_name}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Dispute Value:</span>
              <span style={{ fontWeight: 600, color: 'var(--color-warning)' }}>${caseObj.dispute_amount.toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 style={{ fontSize: '16px', marginBottom: '12px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            Evidence Files ({caseObj.evidence_files?.length || 0})
          </h3>
          {(!caseObj.evidence_files || caseObj.evidence_files.length === 0) ? (
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No file evidence uploaded yet.</p>
          ) : (
            <ul style={{ paddingLeft: '15px', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {caseObj.evidence_files.map((file) => (
                <li key={file.id} style={{ wordBreak: 'break-all' }}>
                  📄 {file.filename}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: 'auto' }}>
          <a href={`/cases/${caseId}/drafting`} className="btn btn-primary" style={{ width: '100%' }}>
            📝 Move to Drafting Agent
          </a>
          <a href="/" className="btn btn-secondary" style={{ width: '100%' }}>
            Back to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
