const REPO_RELEASES_URL = "https://github.com/kiyohken2000/5ch-browser-template/releases";

export default function App() {
  return (
    <main className="page">
      <section className="hero">
        <p className="kicker">5ch Browser</p>
        <h1>Download (ZIP)</h1>
        <p className="lead">
          Windows and macOS binaries are distributed via GitHub Releases. The app checks
          <code> latest.json </code>
          from this site and opens the download page when updates are available.
        </p>
        <div className="actions">
          <a className="btn primary" href={REPO_RELEASES_URL} target="_blank" rel="noreferrer">
            Open Releases
          </a>
          <a className="btn" href="/latest.json" target="_blank" rel="noreferrer">
            View latest.json
          </a>
        </div>
      </section>

      <section className="card">
        <h2>Distribution Policy</h2>
        <ul>
          <li>Installer-free ZIP distribution</li>
          <li>Windows x64 and macOS arm64 binaries</li>
          <li>No auto-install update, only user-guided download</li>
        </ul>
      </section>
    </main>
  );
}
