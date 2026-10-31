import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "മലയാളം ഫ്ലാഷ് ന്യൂസ് | Malayalam Flash News Dashboard",
  description: "Swiss Style & Neo-Brutalist snap-scrolling Flash Cards summarizing Malayalam headlines.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ml" className="h-full antialiased">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=Lexend:wght@300;400;500;600;700;800&family=Syne:wght@700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full flex flex-col font-sans bg-[#0b0b0d] text-zinc-100 antialiased overflow-x-clip">
        {children}
      </body>
    </html>
  );
}
