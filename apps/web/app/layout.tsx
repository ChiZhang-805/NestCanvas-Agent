import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NestCanvas Agent（栖画）",
  description: "AI home design canvas MVP"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
