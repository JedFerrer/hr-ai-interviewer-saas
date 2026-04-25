import type { Metadata } from "next";
import { ThemeProvider } from "@/components/theme-provider";
import { AuthProvider } from "@/lib/auth";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "HireAI — AI-Powered Interviews",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
        />
      </head>
      <body
        className="min-h-screen font-sans antialiased"
        style={{ fontFamily: "'Inter', sans-serif" }}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AuthProvider>
            {children}
            {/*
             * `pointer-events-auto` on the Toaster (and its inner toasts) is
             * required so action buttons (e.g. "Undo") remain clickable while
             * a Radix Dialog is open. Radix Dialog sets `pointer-events: none`
             * on <body> which, because `pointer-events` inherits, disables
             * clicks on every portalled sibling including Sonner's toasts.
             * See https://github.com/emilkowalski/sonner/issues/357
             */}
            <Toaster
              richColors
              position="top-right"
              className="pointer-events-auto"
              toastOptions={{ classNames: { toast: "pointer-events-auto" } }}
            />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
