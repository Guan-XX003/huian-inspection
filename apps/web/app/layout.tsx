import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "汇安检测",
  description: "汇安检测合规审核、规则配置与智能报价工具",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
