import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const DESCRIPTION =
  "Axiom scores COD/RTO risk, explains it, investigates borderline cases against policy, " +
  "and drives bounded, auditable action. Risk decisions you can prove.";

export const metadata: Metadata = {
  title: "Axiom — AI Risk Manager",
  description: DESCRIPTION,
  applicationName: "Axiom",
  // The submission gets shared as a link; an unfurl with no title reads as unfinished.
  openGraph: {
    title: "Axiom — AI Risk Manager for COD / RTO fraud",
    description: DESCRIPTION,
    type: "website",
    siteName: "Axiom",
  },
  twitter: { card: "summary_large_image", title: "Axiom — AI Risk Manager", description: DESCRIPTION },
};

// Drives the browser UI (address bar, form controls) and matches the light-first default.
export const viewport = { colorScheme: "light dark" as const, themeColor: "#0a0e16" };

// Light is the default. Dark is applied only when the visitor has explicitly chosen it,
// so a first-time viewer (a judge opening the link) always lands on the light console
// rather than inheriting whatever their OS happens to be set to. Runs before paint, so
// there is no flash of the wrong theme on a return visit.
const themeScript = `try{if(localStorage.getItem('axiom-theme')==='dark'){document.documentElement.classList.add('dark')}}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full bg-app text-ink">{children}</body>
    </html>
  );
}
