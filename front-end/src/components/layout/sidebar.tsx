'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Server, GitBranch } from 'lucide-react';

const navigation = [
    { name: '仪表盘', href: '/', icon: LayoutDashboard },
    { name: '服务器管理', href: '/servers', icon: Server },
    { name: '节点管理', href: '/nodes', icon: GitBranch },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="flex h-full w-64 flex-col bg-background border-r">
            <div className="flex h-16 items-center border-b px-6">
                <h1 className="text-xl font-bold">OPCUA Manager</h1>
            </div>
            <nav className="flex-1 space-y-1 p-4">
                {navigation.map((item) => {
                    const isActive = pathname === item.href;
                    const Icon = item.icon;
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                                isActive
                                    ? 'bg-secondary text-secondary-foreground'
                                    : 'text-muted-foreground hover:bg-secondary/50'
                            )}
                        >
                            <Icon className="h-4 w-4" />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>
        </div>
    );
} 