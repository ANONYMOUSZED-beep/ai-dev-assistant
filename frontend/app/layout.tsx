import type { Metadata, Viewport } from "next";
import "./globals.css";

const APP_NAME = "AI Developer Assistant";
const APP_DESCRIPTION =
  "Chat with your documents and code, search codebases, debug errors, and " +
  "pair-program — every answer grounded in cited sources.";

export const metadata: Metadata = {
  title: {
    default: APP_NAME,
    template: `%s · ${APP_NAME}`,
  },
  description: APP_DESCRIPTION,
  applicationName: APP_NAME,
  keywords: [
    "AI developer assistant",
    "documentation chat",
    "code search",
    "RAG",
    "debug",
    "pair programming",
  ],
  authors: [{ name: "AI Developer Assistant" }],
  openGraph: {
    type: "website",
    title: APP_NAME,
    description: APP_DESCRIPTION,
    siteName: APP_NAME,
  },
  twitter: {
    card: "summary",
    title: APP_NAME,
    description: APP_DESCRIPTION,
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#f0f0f0",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="h-full bg-ide-bg font-sans text-ide-text">
        {children}
      </body>
    </html>
  );
}
