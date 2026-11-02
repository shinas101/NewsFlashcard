import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NewsFlipcard",
  description: "Read English and Malayalam headlines in a swipeable card deck.",
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
