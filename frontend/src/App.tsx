import { Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { pageTransition } from "./lib/motion";
import { Toaster } from "./ui/Toast";
import Footer from "./ui/Footer";
import ScrollToTop from "./ui/ScrollToTop";
import NavBar from "./components/NavBar";
import HomePage from "./pages/HomePage";
import MarketDetailPage from "./pages/MarketDetailPage";
import SnapshotPage from "./pages/SnapshotPage";
import LibraryPage from "./pages/LibraryPage";
import AdminPage from "./pages/AdminPage";
import AboutPage from "./pages/AboutPage";

export default function App() {
  const location = useLocation();
  return (
    <div className="flex min-h-screen flex-col">
      <ScrollToTop />
      <NavBar />
      <AnimatePresence mode="wait">
        <motion.main key={location.pathname} {...pageTransition} className="flex-1">
          <Routes location={location}>
            <Route path="/" element={<HomePage />} />
            <Route path="/market" element={<MarketDetailPage />} />
            <Route path="/snapshot/:id" element={<SnapshotPage />} />
            <Route path="/library" element={<LibraryPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route
              path="*"
              element={
                <p className="mx-auto max-w-prose px-5 py-24 text-center text-ink/50">
                  Page not found.
                </p>
              }
            />
          </Routes>
        </motion.main>
      </AnimatePresence>
      <Footer />
      <Toaster />
    </div>
  );
}
