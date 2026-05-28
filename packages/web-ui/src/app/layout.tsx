import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AppSidebar } from '@/components/AppSidebar';
import { ThemeProvider } from '@/components/ThemeProvider';
import { StatusBarProvider } from '@/contexts/StatusContext';
import { StatusBar } from '@/components/layout/StatusBar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'BTC Trade Engine',
  description: 'Institutional quantitative trading platform — NautilusTrader React UI',
  icons: { icon: '/favicon.ico' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <body className={inter.className}>
        <ThemeProvider>
          <StatusBarProvider>
            <div className="flex flex-col h-screen overflow-hidden" style={{ background: 'var(--app-bg)' }}>
              <div className="flex flex-1 overflow-hidden">
                <AppSidebar />
                <main className="flex-1 overflow-auto">
                  {children}
                </main>
              </div>
              <StatusBar />
            </div>
          </StatusBarProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
