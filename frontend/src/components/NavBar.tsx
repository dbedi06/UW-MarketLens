// Top navigation. NavLink auto-applies an "active" class to the current route.

import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/library", label: "Library" },
  { to: "/admin", label: "Admin" },
  { to: "/about", label: "About" },
];

export default function NavBar() {
  return (
    <header className="hero">
      <div className="hero-inner">
        <div>
          <h1>UW MarketLens</h1>
          <p>AI-Powered Prediction Market Reliability Platform</p>
        </div>
        <nav className="nav">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
