// Minimal global toast: a module store + <Toaster/> mounted once in App.
// Call toast("Copied") from anywhere — no context plumbing required.

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

type Msg = { id: number; text: string };
let listeners: ((m: Msg) => void)[] = [];
let counter = 0;

export function toast(text: string) {
  const m = { id: ++counter, text };
  listeners.forEach((l) => l(m));
}

export function Toaster() {
  const [items, setItems] = useState<Msg[]>([]);

  useEffect(() => {
    const onMsg = (m: Msg) => {
      setItems((xs) => [...xs, m]);
      setTimeout(
        () => setItems((xs) => xs.filter((x) => x.id !== m.id)),
        1800,
      );
    };
    listeners.push(onMsg);
    return () => {
      listeners = listeners.filter((l) => l !== onMsg);
    };
  }, []);

  return (
    <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 space-y-2">
      <AnimatePresence>
        {items.map((m) => (
          <motion.div
            key={m.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            className="rounded-md bg-ink px-4 py-2.5 font-mono text-xs
              text-paper"
          >
            {m.text}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
