import { Routes, Route } from "react-router-dom";
import "./theme.css";
import NavBar from "./components/NavBar";
import HomePage from "./pages/HomePage";
import MarketDetailPage from "./pages/MarketDetailPage";
import SnapshotPage from "./pages/SnapshotPage";
import LibraryPage from "./pages/LibraryPage";
import AdminPage from "./pages/AdminPage";
import AboutPage from "./pages/AboutPage";

export default function App() {
  return (
    <div className="app">
      <NavBar />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/market" element={<MarketDetailPage />} />
          <Route path="/snapshot/:id" element={<SnapshotPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="*" element={<p className="error">Page not found.</p>} />
        </Routes>
      </main>
    </div>
  );
}
