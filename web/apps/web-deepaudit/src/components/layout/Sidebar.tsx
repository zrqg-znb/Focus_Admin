/**
 * Sidebar Component
 * Premium Terminal Aesthetic with Enhanced Visual Design
 */

import routes from '@/app/routes';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { useAuth } from '@/shared/context/AuthContext';
import {
  Bot,
  ChevronLeft,
  ChevronRight,
  FolderGit2,
  Github,
  LayoutDashboard,
  Layers3,
  ListTodo,
  Menu,
  MessageSquare,
  Settings,
  Shield,
  Trash2,
  UserCircle,
  X,
  Zap,
} from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { version } from '../../../package.json';

// Icon mapping for routes with consistent sizing
const routeIcons: Record<string, React.ReactNode> = {
  '/': <Bot className="h-[18px] w-[18px]" />,
  '/dashboard': <LayoutDashboard className="h-[18px] w-[18px]" />,
  '/projects': <FolderGit2 className="h-[18px] w-[18px]" />,
  '/instant-analysis': <Zap className="h-[18px] w-[18px]" />,
  '/audit-tasks': <ListTodo className="h-[18px] w-[18px]" />,
  '/audit-rules': <Shield className="h-[18px] w-[18px]" />,
  '/prompts': <MessageSquare className="h-[18px] w-[18px]" />,
  '/scenarios': <Layers3 className="h-[18px] w-[18px]" />,
  '/admin': <Settings className="h-[18px] w-[18px]" />,
  '/recycle-bin': <Trash2 className="h-[18px] w-[18px]" />,
};

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

export default function Sidebar({ collapsed, setCollapsed }: SidebarProps) {
  const { hasAccess } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const visibleRoutes = routes.filter(
    (route) => route.visible !== false && hasAccess(route.requiredAccess),
  );

  return (
    <>
      {/* Mobile Menu Button */}
      <Button
        className="fixed left-4 top-4 z-50 md:hidden"
        onClick={() => setMobileOpen(!mobileOpen)}
        size="sm"
        style={{
          background: 'var(--cyber-bg)',
          border: '1px solid var(--cyber-border)',
          color: 'var(--cyber-text-muted)',
        }}
        variant="ghost"
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </Button>

      {/* Overlay for mobile */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-40 h-screen transition-all duration-300 ease-in-out ${collapsed ? 'w-20' : 'w-64'} ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'} `}
        style={{
          background: 'var(--cyber-bg)',
          borderRight: '1px solid var(--cyber-border)',
        }}
      >
        <div className="relative flex h-full flex-col">
          {/* Subtle gradient background */}
          <div className="from-primary/5 pointer-events-none absolute inset-0 bg-gradient-to-b via-transparent to-transparent" />

          {/* Subtle grid background */}
          <div
            className="pointer-events-none absolute inset-0 opacity-20"
            style={{
              backgroundImage: `
                                linear-gradient(var(--cyber-border-accent) 1px, transparent 1px),
                                linear-gradient(90deg, var(--cyber-border-accent) 1px, transparent 1px)
                            `,
              backgroundSize: '32px 32px',
            }}
          />

          {/* Right edge glow */}
          <div className="from-primary/30 via-primary/10 to-primary/30 pointer-events-none absolute bottom-0 right-0 top-0 w-px bg-gradient-to-b" />

          {/* Logo Section */}
          <div
            className={`relative flex h-16 flex-shrink-0 items-center ${collapsed ? 'justify-center px-3' : 'px-5 pr-6'}`}
            style={{
              background: 'var(--cyber-bg-elevated)',
              borderBottom: '1px solid var(--cyber-border)',
            }}
          >
            {/* Bottom accent line */}
            <div className="from-primary/40 via-primary/20 absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r to-transparent" />

            <Link
              className={`group flex items-center gap-3 transition-all duration-300 ${collapsed ? 'justify-center' : 'min-w-0 flex-1'}`}
              onClick={() => setMobileOpen(false)}
              to="/"
            >
              {/* Logo Icon */}
              <div className="relative flex-shrink-0">
                <div
                  className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl transition-all duration-300 group-hover:shadow-[0_0_20px_rgba(37,99,235,0.25)]"
                  style={{
                    background:
                      'linear-gradient(135deg, hsl(var(--primary) / 0.15), hsl(var(--primary) / 0.05))',
                    border: '1px solid hsl(var(--primary) / 0.4)',
                  }}
                >
                  <Shield className="text-primary h-5 w-5 transition-transform duration-300 group-hover:scale-110" />
                </div>
                {/* Glow effect */}
                <div className="bg-primary/30 absolute inset-0 rounded-xl opacity-0 blur-xl transition-opacity duration-500 group-hover:opacity-100" />
              </div>

              {/* Logo Text */}
              <div
                className={`transition-all duration-300 ${collapsed ? 'w-0 overflow-hidden opacity-0' : 'min-w-0 flex-1 opacity-100'}`}
              >
                <div
                  className="font-display text-lg font-semibold leading-tight tracking-tight"
                  style={{ textShadow: '0 0 18px rgba(37,99,235,0.14)' }}
                >
                  <span className="text-primary">Focus</span>
                  <span style={{ color: 'var(--cyber-text)' }}>Audit</span>
                </div>
                <div className="text-muted-foreground mt-0.5 text-[11px] uppercase tracking-[0.22em]">
                  Focus Security Workspace
                </div>
              </div>
            </Link>

            {/* Collapse button */}
            <button
              className="hover:bg-primary hover:border-primary absolute -right-3 top-1/2 hidden h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md shadow-sm transition-all duration-300 hover:text-white md:flex"
              onClick={() => setCollapsed(!collapsed)}
              style={{
                background: 'var(--cyber-bg)',
                border: '1px solid var(--cyber-border)',
                color: 'var(--cyber-text-muted)',
                zIndex: 100,
              }}
            >
              {collapsed ? (
                <ChevronRight className="h-3.5 w-3.5" />
              ) : (
                <ChevronLeft className="h-3.5 w-3.5" />
              )}
            </button>
          </div>

          {/* Navigation */}
          <nav className="relative min-h-0 flex-1 px-3 py-3">
            <div className="space-y-1">
              {visibleRoutes.map((route) => {
                const isActive =
                  !!route.path &&
                  (route.path === '/'
                    ? location.pathname === '/'
                    : location.pathname === route.path);
                return (
                  <Link
                    className={`group relative flex items-center gap-3 rounded-lg px-3 py-2 transition-all duration-300 ${
                      isActive
                        ? 'bg-primary/12 border-primary/30 border shadow-[0_0_15px_rgba(37,99,235,0.12)]'
                        : 'hover:bg-card/60 hover:border-border/50 border border-transparent'
                    } `}
                    key={route.path}
                    onClick={() => setMobileOpen(false)}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.color = 'var(--cyber-text)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.color = 'var(--cyber-text-muted)';
                      }
                    }}
                    style={{
                      color: isActive
                        ? 'hsl(var(--primary))'
                        : 'var(--cyber-text-muted)',
                    }}
                    title={collapsed ? route.name : undefined}
                    to={route.path}
                  >
                    {/* Active indicator */}
                    {isActive && (
                      <div className="bg-primary absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r shadow-[0_0_8px_rgba(37,99,235,0.45)]" />
                    )}

                    {/* Icon */}
                    <span
                      className={`flex-shrink-0 rounded-md p-1.5 transition-all duration-300 ${isActive ? 'bg-primary/20' : 'group-hover:bg-muted/50'} `}
                    >
                      {routeIcons[route.path] || (
                        <LayoutDashboard className="h-[18px] w-[18px]" />
                      )}
                    </span>

                    {/* Label */}
                    {!collapsed && (
                      <span
                        className={`text-sm transition-all duration-300 ${isActive ? 'font-semibold' : 'font-medium'}`}
                      >
                        {route.name}
                      </span>
                    )}

                    {/* Hover indicator */}
                    {!isActive && !collapsed && (
                      <span className="absolute right-3 opacity-0 transition-all duration-300 group-hover:translate-x-1 group-hover:opacity-100">
                        <ChevronRight className="text-primary h-4 w-4" />
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </nav>

          {/* Footer */}
          <div
            className="relative flex-shrink-0 space-y-1 p-3"
            style={{
              background: 'var(--cyber-bg-elevated)',
              borderTop: '1px solid var(--cyber-border)',
            }}
          >
            {/* Top accent line */}
            <div className="via-primary/20 absolute left-0 right-0 top-0 h-px bg-gradient-to-r from-transparent to-transparent" />

            {/* Theme Toggle */}
            <ThemeToggle collapsed={collapsed} />

            {/* Account Link */}
            <Link
              className={`group flex items-center gap-3 rounded-lg px-3 py-2 transition-all duration-300 ${
                location.pathname === '/account'
                  ? 'bg-primary/15 border-primary/40 border'
                  : 'hover:bg-card/60 hover:border-border/50 border border-transparent'
              } `}
              onClick={() => setMobileOpen(false)}
              style={{
                color:
                  location.pathname === '/account'
                    ? 'hsl(var(--primary))'
                    : 'var(--cyber-text-muted)',
              }}
              title={collapsed ? '账号管理' : undefined}
              to="/account"
            >
              <span
                className={`rounded-md p-1.5 transition-all duration-300 ${location.pathname === '/account' ? 'bg-primary/20' : 'group-hover:bg-muted/50'}`}
              >
                <UserCircle className="h-[18px] w-[18px] flex-shrink-0" />
              </span>
              {!collapsed && (
                <span className="text-sm font-medium">账号管理</span>
              )}
            </Link>

            {/* Repository & Status Row */}
            <div
              className={`flex items-center ${collapsed ? 'flex-col gap-2' : 'justify-between'} px-3 py-2`}
            >
              <a
                className="group flex items-center gap-2 transition-all duration-300"
                href="https://github.com/lintsinghua/DeepAudit"
                rel="noopener noreferrer"
                style={{ color: 'var(--cyber-text-muted)' }}
                target="_blank"
                title="Project Repository"
              >
                <Github className="group-hover:text-primary h-[18px] w-[18px] transition-colors" />
                {!collapsed && (
                  <span className="text-muted-foreground text-xs font-medium">
                    v{version}
                  </span>
                )}
              </a>

              {!collapsed && (
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <div
                      className="h-2 w-2 rounded-full bg-emerald-400"
                      style={{ boxShadow: '0 0 8px rgba(52, 211, 153, 0.6)' }}
                    />
                    <div className="absolute inset-0 h-2 w-2 animate-ping rounded-full bg-emerald-400 opacity-50" />
                  </div>
                  <span className="text-xs font-medium text-emerald-500">
                    Online
                  </span>
                </div>
              )}

              {collapsed && (
                <div className="relative">
                  <div
                    className="h-2 w-2 rounded-full bg-emerald-400"
                    style={{ boxShadow: '0 0 8px rgba(52, 211, 153, 0.6)' }}
                  />
                  <div className="absolute inset-0 h-2 w-2 animate-ping rounded-full bg-emerald-400 opacity-50" />
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
