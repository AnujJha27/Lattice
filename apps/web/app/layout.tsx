import type { Metadata } from "next";
import { Spectral, Hanken_Grotesk, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const spectral = Spectral({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-spectral",
  display: "swap",
});

const hanken = Hanken_Grotesk({
  subsets: ["latin"],
  variable: "--font-hanken",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Lattice",
  description: "A personal observatory for what you know.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`dark ${spectral.variable} ${hanken.variable} ${plexMono.variable}`}
      suppressHydrationWarning
    >
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
