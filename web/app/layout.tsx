import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Axiom — AI Risk Manager",
  description:
    "Axiom scores COD/RTO risk, explains it, investigates borderline cases against policy, and drives bounded, auditable action. Risk decisions you can prove.",
};

// Set the theme class before paint to avoid a flash of the wrong theme.
const themeScript = `try{var t=localStorage.getItem('axiom-theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}`;

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
