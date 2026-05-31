// Proper 404 page. Replaces the inline "Page not found" text the catch-all
// route used to render. Gives a stranded visitor three real next steps —
// home, library, about — rather than a dead-end.

import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { fadeUp, stagger } from "../lib/motion";
import PageShell from "../ui/PageShell";

export default function NotFoundPage() {
  return (
    <PageShell>
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="mx-auto max-w-prose py-24 text-center"
      >
        <motion.div
          variants={fadeUp}
          className="numeral text-[clamp(5rem,18vw,11rem)] leading-none
            text-brand-600/30"
        >
          404
        </motion.div>
        <motion.h1
          variants={fadeUp}
          className="mt-2 font-sans text-2xl font-extrabold tracking-tight
            text-ink"
        >
          That page doesn't exist
        </motion.h1>
        <motion.p
          variants={fadeUp}
          className="mt-3 text-ink/65"
        >
          Either the link is wrong or the snapshot it pointed at has been
          re-rendered against a different URL. The home page, library, and
          about page all still work.
        </motion.p>

        <motion.div
          variants={fadeUp}
          className="mt-8 flex flex-wrap justify-center gap-3"
        >
          <Link to="/" className="btn-primary">
            Go to home
          </Link>
          <Link
            to="/library"
            className="btn-ghost border border-line px-5 py-2.5"
          >
            Browse the library
          </Link>
          <Link
            to="/about"
            className="btn-ghost border border-line px-5 py-2.5"
          >
            About
          </Link>
        </motion.div>
      </motion.div>
    </PageShell>
  );
}
