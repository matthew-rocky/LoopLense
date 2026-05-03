import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { AnimatedBackdrop } from "@/components/layout/animated-backdrop";
import { Sidebar } from "@/components/layout/sidebar";
import { ThemeProvider } from "@/components/layout/theme-provider";

export const metadata: Metadata = {
  title: "LoopLens",
  description: "AI Review of Circular Charity Funding"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <AnimatedBackdrop />
          <div className="min-h-screen">
            <Sidebar />
            <main className="relative min-h-screen w-full px-3 py-4 md:pl-72 md:pr-5 lg:px-6 lg:pl-72">
              {children}
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
