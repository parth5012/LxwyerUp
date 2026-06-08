'use client';

import { useState, useEffect, useRef, use } from 'react';

export default function EFilingWorkspace({ params: paramsPromise }) {
  const params = use(paramsPromise);
  const caseId = params.id;
  const [caseObj, setCaseObj] = useState(null);
  const [filingTasks, setFilingTasks] = useState([]);
  const [activeTask, setActiveTask] = useState(null);
  const [terminalLogs, setTerminalLogs] = useState('');
  const [screenshotUrl, setScreenshotUrl] = useState(null);
  const [taskStatus, setTaskStatus] = useState(null);
  const [filing, setFiling] = useState(false);

  const logsEndRef = useRef(null);
  const socketRef = useRef(null);

  useEffect(() => {
    // Fetch Case details
    fetch(`http://localhost:8000/api/cases/${caseId}`)
      .then((res) => res.json())
      .then((data) => setCaseObj(data));

    // Fetch filing tasks
    fetch(`http://localhost:8000/api/cases/${caseId}/filing`)
      .then((res) => res.json())
      .then((data) => {
        setFilingTasks(data);
        if (data.length > 0) {
          // Select latest task
          const latest = data[0];
          setActiveTask(latest);
          setTerminalLogs(latest.logs);
          setTaskStatus(latest.status);
          if (latest.screenshot_path) {
            const filename = latest.screenshot_path.split(/[\\/]/).pop();
            setScreenshotUrl(`http://localhost:8000/static-files/screenshots/${filename}`);
          }
        }
      });
  }, [caseId]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [terminalLogs]);

  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, []);

  const startWebSocketStream = (taskId) => {
    if (socketRef.current) socketRef.current.close();

    setTerminalLogs('');
    setScreenshotUrl(null);

    const wsUrl = `ws://localhost:8000/api/filing/stream/${taskId}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        setTerminalLogs((prev) => prev + `[ERROR] ${data.error}\n`);
        return;
      }

      if (data.logs) {
        setTerminalLogs((prev) => prev + data.logs);
      }
      if (data.status) {
        setTaskStatus(data.status);
      }
      if (data.screenshot_url) {
        setScreenshotUrl(`http://localhost:8000${data.screenshot_url}`);
      }

      if (data.status === 'SUCCESS' || data.status === 'FAILURE') {
        ws.close();
        setFiling(false);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setFiling(false);
    };

    ws.onclose = () => {
      setFiling(false);
    };
  };

  const handleStartFiling = async () => {
    setFiling(true);
    setTaskStatus('PENDING');
    try {
      const res = await fetch(`http://localhost:8000/api/cases/${caseId}/filing`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Filing request failed');
      const task = await res.json();
      
      setFilingTasks((prev) => [task, ...prev]);
      setActiveTask(task);
      startWebSocketStream(task.task_id);
    } catch (err) {
      console.error(err);
      alert('Error triggering filing worker. Verify Celery and Redis broker configurations.');
      setFiling(false);
    }
  };

  if (!caseObj) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
        Loading E-Filing Workspace...
      </div>
    );
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'SUCCESS':
        return '#00875a';
      case 'FAILURE':
        return '#de350b';
      case 'PROGRESS':
        return '#2962ff';
      default:
        return '#ffab00';
    }
  };

  return (
    <div className="animated-fadeIn" style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '30px', height: 'calc(100vh - 80px)' }}>
      {/* Console and screenshot panel */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '25px' }}>
        <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '15px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span className="badge badge-blue" style={{ marginBottom: '8px' }}>Agent 3: E-Filing Engine</span>
            <h1 style={{ fontSize: '24px' }}>Court Portal E-Filing Console</h1>
          </div>
          <button onClick={handleStartFiling} className="btn btn-primary" disabled={filing}>
            {filing ? 'Running E-Filing Automation...' : '🚀 Submit Case E-Filing'}
          </button>
        </div>

        {/* Real-time terminal logs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Live Automation Logs</span>
            {taskStatus && (
              <span style={{ fontSize: '13px', fontWeight: 'bold', color: getStatusColor(taskStatus) }}>
                Status: {taskStatus}
              </span>
            )}
          </div>
          <div className="terminal" style={{ flex: 1 }}>
            {terminalLogs ? (
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{terminalLogs}</pre>
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>Console idle. Ready for court filing submit.</div>
            )}
            <div ref={logsEndRef} />
          </div>
        </div>

        {/* Live screenshot preview */}
        {screenshotUrl && (
          <div className="card" style={{ padding: '15px' }}>
            <h4 style={{ fontSize: '14px', marginBottom: '10px', color: 'var(--text-secondary)' }}>Live Browser Capture</h4>
            <div style={{ width: '100%', maxHeight: '250px', overflow: 'hidden', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <img src={screenshotUrl} alt="Court Portal Screenshot" style={{ width: '100%', height: 'auto', display: 'block' }} />
            </div>
          </div>
        )}
      </div>

      {/* Case Details and Filing history */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
        <div className="card">
          <h3 style={{ fontSize: '16px', marginBottom: '15px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            Filing Credentials
          </h3>
          <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span>Mock Portal:</span>
              <a href="http://localhost:8000/mock-court" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline' }}>
                Open Portal
              </a>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span>Filing User:</span>
              <span style={{ fontFamily: 'monospace' }}>admin</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Filing Pass:</span>
              <span style={{ fontFamily: 'monospace' }}>password123</span>
            </div>
          </div>
        </div>

        <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '15px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            Filing Log History
          </h3>
          <div style={{ overflowY: 'auto', flex: 1, maxHeight: '250px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {filingTasks.map((t) => (
              <div
                key={t.id}
                style={{ padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', fontSize: '13px', cursor: 'pointer', borderLeft: `3px solid ${getStatusColor(t.status)}` }}
                onClick={() => {
                  setActiveTask(t);
                  setTaskStatus(t.status);
                  setTerminalLogs(t.logs);
                  if (t.screenshot_path) {
                    const fn = t.screenshot_path.split(/[\\/]/).pop();
                    setScreenshotUrl(`http://localhost:8000/static-files/screenshots/${fn}`);
                  } else {
                    setScreenshotUrl(null);
                  }
                }}
              >
                <div style={{ fontWeight: 600 }}>Task: {t.task_id.slice(0, 8)}...</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  <span>{new Date(t.updated_at).toLocaleTimeString()}</span>
                  <span style={{ color: getStatusColor(t.status), fontWeight: 'bold' }}>{t.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: 'auto' }}>
          <a href={`/cases/${caseId}/drafting`} className="btn btn-secondary" style={{ width: '100%' }}>
            📝 Back to Case Drafts
          </a>
          <a href="/" className="btn btn-secondary" style={{ width: '100%' }}>
            Back to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
