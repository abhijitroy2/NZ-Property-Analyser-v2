import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/shared/nav";

export const metadata: Metadata = {
  title: "NZ Property Finder",
  description: "NZ Property Investment Evaluation System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <Nav />
        <main className="pt-24 pb-8 px-4 sm:px-6 max-w-screen-2xl mx-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
