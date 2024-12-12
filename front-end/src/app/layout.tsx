import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { cn } from "@/lib/utils";
import { Toaster } from 'sonner';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "OPCUA Manager",
    description: "OPCUA服务器和节点管理系统",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="zh-CN" suppressHydrationWarning>
            <body className={cn(inter.className, "min-h-screen bg-background antialiased")} suppressHydrationWarning>
                <div className="relative flex min-h-screen">
                    <Sidebar />
                    <main className="flex-1 overflow-auto bg-muted/10" role="main">
                        <div className="container mx-auto p-8">
                            {children}
                        </div>
                    </main>
                </div>
                <Toaster />
            </body>
        </html>
    );
}
