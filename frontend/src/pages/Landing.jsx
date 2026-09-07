import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'

export default function Landing() {
  return (
    <div className="landing-page">
      <div className="watermark" />

      <nav className="landing-nav">
        <div className="landing-nav-logo">
          <img src="/scanx-logo.png" alt="Scan-X" style={{ height: 28, objectFit: 'contain' }} />
        </div>
        <div className="landing-nav-links">
          <Link to="/app" className="btn btn-primary" style={{ textDecoration: 'none' }}>
            Open Dashboard <ArrowRight size={14} />
          </Link>
        </div>
      </nav>

      <div className="landing-hero">
        <div className="landing-hero-left">
          <div className="landing-eyebrow">Penetration Testing Platform</div>
          <h1>Security Assessment<br />Platform</h1>
          <p>
            Discover endpoints, analyze source code, and correlate
            vulnerabilities — all in one place.
          </p>
          <div className="landing-actions">
            <Link to="/app" className="btn btn-primary" style={{ textDecoration: 'none' }}>
              Get Started <ArrowRight size={14} />
            </Link>
            <a href="/api/docs" className="btn btn-ghost" target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
              API Docs
            </a>
          </div>
        </div>

        <div className="landing-hero-right">
          <div className="mock-card">
            <div className="mock-header">
              <div className="mock-dot r" />
              <div className="mock-dot y" />
              <div className="mock-dot g" />
              <span className="mock-title">scan-x — assessment</span>
            </div>

            <div className="mock-row">
              <span className="mock-label">Status</span>
              <span className="mock-value green">Completed</span>
            </div>
            <div className="mock-row">
              <span className="mock-label">Target</span>
              <span className="mock-value blue">example.com</span>
            </div>
            <div className="mock-row">
              <span className="mock-label">Endpoints</span>
              <span className="mock-value">24 discovered</span>
            </div>
            <div className="mock-row">
              <span className="mock-label">Findings</span>
              <span className="mock-value yellow">17 issues</span>
            </div>
            <div className="mock-row">
              <span className="mock-label">Risk Score</span>
              <span className="mock-value red">68 / 100</span>
              <div className="mock-bar-wrap">
                <div className="mock-bar" style={{ width: '68%' }} />
              </div>
            </div>

            <div className="mock-kpi-row">
              <div className="mock-kpi">
                <div className="mock-kpi-num green">3</div>
                <div className="mock-kpi-label">Critical</div>
              </div>
              <div className="mock-kpi">
                <div className="mock-kpi-num purple">7</div>
                <div className="mock-kpi-label">High</div>
              </div>
              <div className="mock-kpi">
                <div className="mock-kpi-num blue">7</div>
                <div className="mock-kpi-label">Medium</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="landing-features">
        <div className="landing-feature">
          <div className="landing-feature-dot green" />
          <span>Web Reconnaissance</span>
        </div>
        <div className="landing-feature">
          <div className="landing-feature-dot purple" />
          <span>Repository Analysis</span>
        </div>
        <div className="landing-feature">
          <div className="landing-feature-dot blue" />
          <span>Correlation Engine</span>
        </div>
      </div>

      <div className="landing-footer">
        Scan-X — B.Tech Final Year Project 2026
      </div>
    </div>
  )
}
