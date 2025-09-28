import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
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
  title: "AgentL2 - Legal AI Assistant",
  description: "Ontology DB-based Legal Agent",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased bg-background text-foreground`}
      >
        <div className="min-h-screen bg-background text-foreground">
          {/* Header */}
          <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-16 items-center">
              <div className="flex items-center space-x-8">
                <Link href="/" className="text-2xl font-bold tracking-tight">
                  AgentL2
                </Link>
                <nav className="hidden md:flex items-center space-x-6">
                  <Link
                    href="/"
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Home
                  </Link>
                  <Link
                    href="/chat"
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Chat
                  </Link>
                  <div className="relative group">
                    <button className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                      Admin
                    </button>
                    <div className="absolute top-full left-0 mt-2 w-48 rounded-lg border bg-popover p-2 shadow-lg opacity-0 group-hover:opacity-100 transition-opacity">
                      <Link
                        href="/admin/ontology"
                        className="block px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground rounded-md transition-colors"
                      >
                        Ontology DB
                      </Link>
                      <Link
                        href="/admin/system"
                        className="block px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground rounded-md transition-colors"
                      >
                        System Monitor
                      </Link>
                      <Link
                        href="/admin/llm"
                        className="block px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground rounded-md transition-colors"
                      >
                        LLM Monitor
                      </Link>
                    </div>
                  </div>
                </nav>
              </div>
            </div>
          </header>

          {/* Main Content */}
          <main className="container mx-auto px-4 py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}