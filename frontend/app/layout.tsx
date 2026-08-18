import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { SessionGuard, SessionProvider } from "@/components/session-provider";
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
  title: "PRISM | Assessment intelligence",
  description: "Evidence-backed handwritten assessment review.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <SessionProvider>
          <SessionGuard>{children}</SessionGuard>
        </SessionProvider>
      </body>
    </html>
  );
}
