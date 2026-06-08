'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function NewCase() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [claimantName, setClaimantName] = useState('');
  const [respondentName, setRespondentName] = useState('');
  const [disputeAmount, setDisputeAmount] = useState('0');
  const [files, setFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      // 1. Submit Case metadata
      const formData = new FormData();
      formData.append('title', title);
      formData.append('description', description);
      formData.append('claimant_name', claimantName);
      formData.append('respondent_name', respondentName);
      formData.append('dispute_amount', parseFloat(disputeAmount) || 0);

      const caseRes = await fetch('http://localhost:8000/api/cases', {
        method: 'POST',
        body: formData,
      });

      if (!caseRes.ok) throw new Error('Filing case details failed.');
      const caseData = await caseRes.json();

      // 2. Upload any evidence files
      if (files.length > 0) {
        for (const file of files) {
          const fileData = new FormData();
          fileData.append('file', file);
          await fetch(`http://localhost:8000/api/cases/${caseData.id}/evidence`, {
            method: 'POST',
            body: fileData,
          });
        }
      }

      router.push(`/cases/${caseData.id}/arbitration`);
    } catch (err) {
      console.error(err);
      alert('Error initiating dispute claim. Please check backend connection.');
      setSubmitting(false);
    }
  };

  return (
    <div className="animated-fadeIn" style={{ maxWidth: '650px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>Initiate Arbitration Claim</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '30px' }}>
        Fill out dispute facts and upload evidence contracts to start the LangGraph copilot sequence.
      </p>

      <form onSubmit={handleSubmit} className="card">
        <div className="input-group">
          <label className="input-label">Case / Dispute Title</label>
          <input
            type="text"
            className="text-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Breach of Software SLA - Acme Corp vs DevCo"
            required
          />
        </div>

        <div className="input-group">
          <label className="input-label">Detailed Description of Dispute Facts</label>
          <textarea
            className="text-input"
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the background, timeline of contract breaches, obligations failed..."
            style={{ resize: 'vertical' }}
            required
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div className="input-group">
            <label className="input-label">Claimant Name (You)</label>
            <input
              type="text"
              className="text-input"
              value={claimantName}
              onChange={(e) => setClaimantName(e.target.value)}
              placeholder="e.g. Acme Corp"
              required
            />
          </div>
          <div className="input-group">
            <label className="input-label">Respondent Name</label>
            <input
              type="text"
              className="text-input"
              value={respondentName}
              onChange={(e) => setRespondentName(e.target.value)}
              placeholder="e.g. DevCo Inc"
              required
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div className="input-group">
            <label className="input-label">Dispute Amount ($)</label>
            <input
              type="number"
              className="text-input"
              value={disputeAmount}
              onChange={(e) => setDisputeAmount(e.target.value)}
              placeholder="0.00"
              required
            />
          </div>
          <div className="input-group">
            <label className="input-label">Upload Evidence Contracts (PDF/TXT)</label>
            <input
              type="file"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files))}
              style={{ color: 'var(--text-secondary)', padding: '10px 0' }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '15px', marginTop: '20px' }}>
          <button type="submit" className="btn btn-primary" disabled={submitting} style={{ flex: 1 }}>
            {submitting ? 'Initiating Pipeline...' : '⚖️ Launch Case Analysis'}
          </button>
          <a href="/" className="btn btn-secondary">
            Cancel
          </a>
        </div>
      </form>
    </div>
  );
}
