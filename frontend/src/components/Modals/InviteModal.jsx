import { UserPlus } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import Modal from '../ui/Modal';
import { Input, Select } from '../ui/Fields';

export default function InviteModal() {
  const {
    showInviteModal,
    setShowInviteModal,
    inviteUsername,
    setInviteUsername,
    invitePassword,
    setInvitePassword,
    inviteRole,
    setInviteRole,
    inviteError,
    handleInviteUser,
  } = useApp();

  return (
    <Modal open={showInviteModal} onClose={() => setShowInviteModal(false)} title="ثبت کاربر جدید در سازمان">
      {inviteError && <div className="login-error">{inviteError}</div>}

      <form onSubmit={handleInviteUser} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Input
          label="نام کاربری"
          ltr
          value={inviteUsername}
          onChange={(e) => setInviteUsername(e.target.value)}
          placeholder="username"
          required
        />
        <Input
          label="رمز عبور"
          type="password"
          ltr
          value={invitePassword}
          onChange={(e) => setInvitePassword(e.target.value)}
          placeholder="••••••"
          required
        />
        <Select label="نقش کاربر" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
          <option value="Analyst">تحلیل‌گر (Analyst)</option>
          <option value="Admin">مدیر سیستم (Admin)</option>
        </Select>

        <button type="submit" className="ax-btn ax-btn--primary ax-btn--block" style={{ marginTop: 8 }}>
          <UserPlus size={16} /> ثبت کاربر
        </button>
      </form>
    </Modal>
  );
}
