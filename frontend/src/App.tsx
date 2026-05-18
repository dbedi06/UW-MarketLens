import { lazy, Suspense } from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { pageTransition } from "./lib/motion";
import { Toaster } from "./ui/Toast";
import Footer from "./ui/Footer";
import ScrollToTop from "./ui/ScrollToTop";
import PageShell from "./ui/PageShell";
import Skeleton from "./ui/Skeleton";
import NavBar from "./components/NavBar";
import HomePage from "./pages/HomePage"; // eager: fastest first paint

// Route-level code splitting — keeps recharts/report off the initial bundle.
const MarketDetailPage = lazy(() => import("./pages/MarketDetailPage"));
const SnapshotPage = lazy(() => import("./pages/SnapshotPage"));
const LibraryPage = lazy(() => import("./pages/LibraryPage"));
const ComparePage = lazy(() => import("./pages/ComparePage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));

function RouteFallback() {
  return (
    <PageShell wide>
      <Skeleton className="h-64" />
    </PageShell>
  );
}

export default function App() {
  const location = useLocation();
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4
          focus:top-4 focus:z-50 focus:rounded-md focus:bg-ink
          focus:px-4 focus:py-2 focus:text-sm focus:text-paper"
      >
        Skip to content
      </a>
      <ScrollToTop />
      <NavBar />
      <AnimatePresence mode="wait">
        <motion.main
          id="main"
          key={location.pathname}
          {...pageTransition}
          className="flex-1"
        >
          <Suspense fallback={<RouteFallback />}>
            <Routes location={location}>
              <Route path="/" element={<HomePage />} />
              <Route path="/market" element={<MarketDetailPage />} />
              <Route path="/snapshot/:id" element={<SnapshotPage />} />
              <Route path="/library" element={<LibraryPage />} />
              <Route path="/compare" element={<ComparePage />} />
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
          </Suspense>
        </motion.main>
      </AnimatePresence>
      <Footer />
      <Toaster />
    </div>
  );
}
