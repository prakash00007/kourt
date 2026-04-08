import type { Metadata } from "next";

import "./globals.css";
import { TopNav } from "@/components/top-nav";
import { AuthProvider } from "@/context/AuthContext";

export const metadata: Metadata = {
  title: "Kourt AI Copilot",
  description: "AI copilot for Indian lawyers: research, summarize judgments, and draft legal documents."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="font-sans text-ink">
        <AuthProvider>
          <div className="mx-auto min-h-screen max-w-7xl px-4 pb-10 pt-6 sm:px-6 lg:px-8">
            <TopNav />
            {children}
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
