/**
 * Account Page
 * Cyberpunk Terminal Aesthetic
 */

import type { Profile } from '@/shared/types';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { normalizeProfile } from '@/shared/api/focusAdapter';
import { apiClient } from '@/shared/api/serverClient';
import { useAuth } from '@/shared/context/AuthContext';
import {
  Calendar,
  GitBranch,
  KeyRound,
  LogOut,
  Mail,
  Phone,
  Save,
  Shield,
  Terminal,
  User,
  UserPlus,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

export default function Account() {
  const { logout } = useAuth();
  const [profile, setProfile] = useState<null | Profile>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);
  const [form, setForm] = useState({
    full_name: '',
    phone: '',
    github_username: '',
    gitlab_username: '',
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/users/me');
      const normalized = normalizeProfile(res.data) as Profile;
      setProfile(normalized);
      setForm({
        full_name: normalized.full_name || '',
        phone: normalized.phone || '',
        github_username: normalized.github_username || '',
        gitlab_username: normalized.gitlab_username || '',
      });
    } catch (error) {
      console.error('Failed to load profile:', error);
      toast.error('加载账号信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const res = await apiClient.put('/users/me', {
        name: form.full_name,
        mobile: form.phone,
      });
      setProfile(normalizeProfile(res.data) as Profile);
      toast.success('账号信息已更新');
    } catch (error) {
      console.error('Failed to update profile:', error);
      toast.error('更新失败');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (!passwordForm.new_password || !passwordForm.confirm_password) {
      toast.error('请填写新密码');
      return;
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error('两次输入的密码不一致');
      return;
    }
    if (passwordForm.new_password.length < 6) {
      toast.error('密码长度至少6位');
      return;
    }

    try {
      setChangingPassword(true);
      await apiClient.post('/user/change-password', {
        old_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      toast.success('密码已更新');
      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });
    } catch (error) {
      console.error('Failed to change password:', error);
      toast.error('密码更新失败');
    } finally {
      setChangingPassword(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getInitials = (name?: string, email?: string) => {
    if (name) return name.charAt(0).toUpperCase();
    if (email) return email.charAt(0).toUpperCase();
    return 'U';
  };

  const handleLogout = () => {
    logout();
    toast.success('已退出登录');
  };

  const handleSwitchAccount = () => {
    logout();
  };

  if (loading) {
    return (
      <div className="cyber-bg-elevated flex min-h-screen items-center justify-center">
        <div className="space-y-4 text-center">
          <div className="loading-spinner mx-auto" />
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
            加载中...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="cyber-bg-elevated relative min-h-screen space-y-6 p-6 font-mono">
      {/* Grid background */}
      <div className="cyber-grid-subtle pointer-events-none absolute inset-0" />

      <div className="relative z-10 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Profile Card */}
        <div className="cyber-card p-0">
          <div className="cyber-card-header">
            <User className="text-primary h-5 w-5" />
            <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
              用户信息
            </h3>
          </div>
          <div className="p-6 text-center">
            <div className="relative mb-4 inline-block">
              <Avatar className="border-primary/30 h-24 w-24 border-2">
                <AvatarImage src={profile?.avatar_url} />
                <AvatarFallback className="bg-primary/20 text-primary text-2xl font-bold">
                  {getInitials(profile?.full_name, profile?.email)}
                </AvatarFallback>
              </Avatar>
              <div className="border-background absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full border-2 bg-emerald-500">
                <div className="bg-foreground h-2 w-2 animate-pulse rounded-full" />
              </div>
            </div>
            <h4 className="text-foreground mb-1 text-lg font-bold uppercase">
              {profile?.full_name || '未设置姓名'}
            </h4>
            <p className="text-muted-foreground text-sm">{profile?.email}</p>

            <div className="border-border mt-6 space-y-3 border-t pt-6 text-left">
              <div className="flex items-center gap-3 text-sm">
                <Shield className="h-4 w-4 text-violet-400" />
                <span className="text-muted-foreground">角色:</span>
                <span className="font-bold uppercase text-violet-400">
                  {profile?.role === 'admin' ? '管理员' : '成员'}
                </span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Calendar className="h-4 w-4 text-sky-400" />
                <span className="text-muted-foreground">注册时间:</span>
                <span className="text-foreground font-mono">
                  {formatDate(profile?.created_at)}
                </span>
              </div>
            </div>

            <div className="border-border mt-6 space-y-2 border-t pt-6">
              <Button
                className="cyber-btn-outline h-10 w-full"
                onClick={handleSwitchAccount}
                variant="outline"
              >
                <UserPlus className="mr-2 h-4 w-4" />
                切换账号
              </Button>
              <Button
                className="h-10 w-full border border-rose-500/30 bg-rose-500/20 text-rose-400 hover:bg-rose-500/30"
                onClick={() => setShowLogoutDialog(true)}
                variant="destructive"
              >
                <LogOut className="mr-2 h-4 w-4" />
                退出登录
              </Button>
            </div>
          </div>
        </div>

        {/* Edit Form */}
        <div className="cyber-card p-0 lg:col-span-2">
          <div className="cyber-card-header">
            <Terminal className="text-primary h-5 w-5" />
            <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
              基本信息
            </h3>
          </div>
          <div className="space-y-6 p-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label
                  className="text-muted-foreground flex items-center gap-2 text-xs font-bold uppercase"
                  htmlFor="email"
                >
                  <Mail className="h-3 w-3" /> 邮箱
                </Label>
                <Input
                  className="cyber-input bg-muted text-muted-foreground cursor-not-allowed"
                  disabled
                  id="email"
                  value={profile?.email || ''}
                />
                <p className="text-muted-foreground text-xs">邮箱不可修改</p>
              </div>
              <div className="space-y-2">
                <Label
                  className="text-muted-foreground flex items-center gap-2 text-xs font-bold uppercase"
                  htmlFor="full_name"
                >
                  <User className="h-3 w-3" /> 姓名
                </Label>
                <Input
                  className="cyber-input"
                  id="full_name"
                  onChange={(e) =>
                    setForm({ ...form, full_name: e.target.value })
                  }
                  placeholder="请输入姓名"
                  value={form.full_name}
                />
              </div>
              <div className="space-y-2">
                <Label
                  className="text-muted-foreground flex items-center gap-2 text-xs font-bold uppercase"
                  htmlFor="phone"
                >
                  <Phone className="h-3 w-3" /> 手机号
                </Label>
                <Input
                  className="cyber-input"
                  id="phone"
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  placeholder="请输入手机号"
                  value={form.phone}
                />
              </div>
            </div>

            <div className="border-border border-t pt-6">
              <h3 className="section-title mb-4 flex items-center gap-2 text-sm">
                <GitBranch className="h-4 w-4" />
                代码托管账号
              </h3>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label
                    className="text-muted-foreground flex items-center gap-2 text-xs font-bold uppercase"
                    htmlFor="github"
                  >
                    <GitBranch className="h-3 w-3" /> CodeHub 用户名
                  </Label>
                  <Input
                    className="cyber-input"
                    id="github"
                    onChange={(e) =>
                      setForm({ ...form, github_username: e.target.value })
                    }
                    placeholder="your-codehub-username"
                    value={form.github_username}
                  />
                </div>
                <div className="space-y-2">
                  <Label
                    className="text-muted-foreground flex items-center gap-2 text-xs font-bold uppercase"
                    htmlFor="gitlab"
                  >
                    <GitBranch className="h-3 w-3" /> 内网 Git 备用用户名
                  </Label>
                  <Input
                    className="cyber-input"
                    id="gitlab"
                    onChange={(e) =>
                      setForm({ ...form, gitlab_username: e.target.value })
                    }
                    placeholder="optional-git-username"
                    value={form.gitlab_username}
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <Button
                className="cyber-btn-primary h-10"
                disabled={saving}
                onClick={handleSave}
              >
                {saving ? (
                  <>
                    <div className="loading-spinner mr-2 h-4 w-4" />
                    保存中...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    保存修改
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Password Change */}
        <div className="cyber-card p-0 lg:col-span-3">
          <div className="cyber-card-header">
            <KeyRound className="h-5 w-5 text-amber-400" />
            <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
              修改密码
            </h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label
                  className="text-muted-foreground text-xs font-bold uppercase"
                  htmlFor="new_password"
                >
                  新密码
                </Label>
                <Input
                  className="cyber-input"
                  id="new_password"
                  onChange={(e) =>
                    setPasswordForm({
                      ...passwordForm,
                      new_password: e.target.value,
                    })
                  }
                  placeholder="输入新密码"
                  type="password"
                  value={passwordForm.new_password}
                />
              </div>
              <div className="space-y-2">
                <Label
                  className="text-muted-foreground text-xs font-bold uppercase"
                  htmlFor="confirm_password"
                >
                  确认密码
                </Label>
                <Input
                  className="cyber-input"
                  id="confirm_password"
                  onChange={(e) =>
                    setPasswordForm({
                      ...passwordForm,
                      confirm_password: e.target.value,
                    })
                  }
                  placeholder="再次输入新密码"
                  type="password"
                  value={passwordForm.confirm_password}
                />
              </div>
              <div className="flex items-end">
                <Button
                  className="cyber-btn-outline h-10"
                  disabled={changingPassword}
                  onClick={handleChangePassword}
                >
                  {changingPassword ? (
                    <>
                      <div className="loading-spinner mr-2 h-4 w-4" />
                      更新中...
                    </>
                  ) : (
                    <>
                      <KeyRound className="mr-2 h-4 w-4" />
                      更新密码
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Logout Confirmation Dialog */}
      <AlertDialog onOpenChange={setShowLogoutDialog} open={showLogoutDialog}>
        <AlertDialogContent className="cyber-card cyber-dialog border-rose-500/30">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-foreground flex items-center gap-2 text-lg font-bold uppercase">
              <LogOut className="h-5 w-5 text-rose-400" />
              确认退出登录？
            </AlertDialogTitle>
            <AlertDialogDescription className="text-muted-foreground">
              退出后需要重新登录才能访问系统。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="cyber-btn-outline">
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              className="border border-rose-500/30 bg-rose-500/20 text-rose-400 hover:bg-rose-500/30"
              onClick={handleLogout}
            >
              确认退出
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
