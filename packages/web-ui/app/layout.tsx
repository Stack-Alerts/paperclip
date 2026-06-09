import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AppSidebar } from "@/components/AppSidebar";
import { ThemeProvider } from "@/components/ThemeProvider";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { StatusBarProvider } from "@/contexts/StatusContext";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "BTC Trade Engine",
  description: "Institutional-grade BTC algorithmic trading platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="h-full flex" style={{ background: 'var(--app-bg)', color: 'var(--text-primary)' }}>
        <ThemeProvider>
          <StatusBarProvider>
            <SidebarProvider>
              <AppSidebar />
              <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
                {children}
              </main>
            </SidebarProvider>
          </StatusBarProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
