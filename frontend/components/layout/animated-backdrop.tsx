"use client";

import { motion } from "framer-motion";

export function AnimatedBackdrop() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <motion.div
        className="absolute -left-24 top-10 h-72 w-72 rounded-full bg-teal-400/20 blur-3xl"
        animate={{ x: [0, 80, 20, 0], y: [0, 30, 80, 0], scale: [1, 1.15, 0.95, 1] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute right-0 top-4 h-96 w-96 rounded-full bg-sky-500/18 blur-3xl"
        animate={{ x: [0, -70, -20, 0], y: [0, 90, 30, 0], scale: [1, 0.92, 1.1, 1] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-0 left-1/2 h-80 w-80 rounded-full bg-amber-300/12 blur-3xl"
        animate={{ x: [0, -50, 50, 0], y: [0, -30, -80, 0] }}
        transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

