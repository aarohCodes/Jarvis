import type { Metadata } from "next";
import { Orbitron, Rajdhani, Share_Tech_Mono } from "next/font/google";
import "./globals.css";
import NavShell from "@/components/NavShell";

const orbitron = Orbitron({ subsets: ["latin"], weight: ["500", "700", "900"], variable: "--font-display" });
const rajdhani = Rajdhani({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-body" });
const shareTechMono = Share_Tech_Mono({ subsets: ["latin"], weight: "400", variable: "--font-mono" });

export const metadata: Metadata = {
  title: "J.A.R.V.I.S.",
  description: "Personal assistant interface",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${orbitron.variable} ${rajdhani.variable} ${shareTechMono.variable}`}>
      <body>
        <div className="hud-grid" aria-hidden="true" />
        <div className="hud-scanline" aria-hidden="true" />
        <div className="hud-vignette" aria-hidden="true" />
        <NavShell>{children}</NavShell>
      </body>
    </html>
  );
}
