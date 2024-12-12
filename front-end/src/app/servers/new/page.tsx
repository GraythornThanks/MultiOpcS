import { ServerForm } from '../server-form';

export default function NewServerPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">添加服务器</h1>
            <div className="max-w-2xl">
                <ServerForm />
            </div>
        </div>
    );
} 