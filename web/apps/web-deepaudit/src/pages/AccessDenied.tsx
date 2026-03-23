import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/button';

export default function AccessDenied() {
  return (
    <div className="min-h-screen cyber-bg-elevated flex items-center justify-center p-6 font-mono relative overflow-hidden">
      <div className="absolute inset-0 cyber-grid-subtle pointer-events-none" />
      <div className="cyber-card max-w-xl w-full p-10 text-center relative z-10">
        <div className="w-20 h-20 mx-auto rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mb-6">
          <ShieldAlert className="w-10 h-10 text-rose-400" />
        </div>
        <h1 className="text-2xl font-bold uppercase tracking-wider text-foreground mb-3">
          无权访问当前页面
        </h1>
        <p className="text-muted-foreground leading-7 mb-8">
          当前 Focus 账号没有分配对应的 DeepAudit 页面权限。如需访问，请联系管理员分配菜单和操作权限。
        </p>
        <Link to="/account">
          <Button className="cyber-btn-primary h-11 px-6">
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回个人页
          </Button>
        </Link>
      </div>
    </div>
  );
}
