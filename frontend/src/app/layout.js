import './globals.css';

export const metadata = {
  title: 'LxwyerUp - AI Legal Co-pilot',
  description: 'Automated legal arbitration, drafting complaints, and e-filing automation platform.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="layout-container">
          <aside className="sidebar">
            <div className="logo">
              Lxwyer<span>Up</span>
            </div>
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '15px', flex: 1 }}>
              <a href="/" style={{ fontSize: '15px', fontWeight: 600, padding: '10px 15px', borderRadius: '6px', background: 'rgba(255,255,255,0.03)', color: '#fff' }}>
                📂 Case Dashboard
              </a>
              <a href="/cases/new" style={{ fontSize: '15px', fontWeight: 600, padding: '10px 15px', borderRadius: '6px', color: '#a5a5b2' }}>
                ➕ Initiate Claim
              </a>
            </nav>
            <div style={{ fontSize: '12px', color: '#6e6e80', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '20px' }}>
              LxwyerUp Multi-Agent System v1.0
            </div>
          </aside>
          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
