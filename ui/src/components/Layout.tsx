import { Link, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="brand">
            <span className="brand-name">Duta</span>
            <span className="brand-sep" aria-hidden="true">
              —
            </span>
            <span className="brand-sub">Meridian triage pilot</span>
          </Link>
          <span className="engagement-tag">staged engagement</span>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="footer">All data synthetic — staged FDE engagement</footer>
    </div>
  );
}
