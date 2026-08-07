import { useState, useEffect } from 'react';
import {
  FolderTree,
  ListTree,
  Plus,
  Pencil,
  Trash2,
  Sparkles,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { API_BASE } from '../../api/config';
import { useToast, useConfirm } from '../../components/ui/ToastProvider';
import Modal from '../../components/ui/Modal';
import Switch from '../../components/ui/Switch';
import Badge from '../../components/ui/Badge';
import { Input, Textarea } from '../../components/ui/Fields';
import PageHeader from '../../components/ui/PageHeader';
import EmptyState from '../../components/ui/EmptyState';

export default function CategoriesView() {
  const { apiFetch, features, toggleFeature, currentUser } = useApp();
  const toast = useToast();
  const confirmDialog = useConfirm();

  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState(null);
  const [formData, setFormData] = useState({ name: '', description: '', is_active: true });

  const fetchCategories = async () => {
    try {
      setIsLoading(true);
      const res = await apiFetch(`${API_BASE}/v1/config/categories`);
      if (res.ok) {
        const data = await res.json();
        setCategories(data.categories || []);
      }
    } catch (err) {
      console.error('Failed to fetch categories', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchCategories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleOpenModal = (cat = null) => {
    if (cat) {
      setEditId(cat.id);
      setFormData({ name: cat.name, description: cat.description || '', is_active: cat.is_active });
    } else {
      setEditId(null);
      setFormData({ name: '', description: '', is_active: true });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditId(null);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error('نام الزامی است', 'نام دسته‌بندی را وارد کنید.');
      return;
    }

    try {
      const url = editId
        ? `${API_BASE}/v1/config/categories/${editId}`
        : `${API_BASE}/v1/config/categories`;
      const method = editId ? 'PUT' : 'POST';

      const res = await apiFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        await fetchCategories();
        handleCloseModal();
        toast.success(editId ? 'دسته‌بندی ویرایش شد' : 'دسته‌بندی ایجاد شد');
      } else {
        const errData = await res.json();
        toast.error('خطا در ذخیره دسته‌بندی', errData.detail);
      }
    } catch (err) {
      console.error(err);
      toast.error('خطا در ارتباط با سرور');
    }
  };

  const handleDelete = async (id, name) => {
    const confirmed = await confirmDialog({
      title: 'حذف دسته‌بندی',
      desc: `آیا از حذف دسته‌بندی «${name}» اطمینان دارید؟`,
      confirmLabel: 'حذف',
      cancelLabel: 'انصراف',
    });
    if (!confirmed) return;
    try {
      const res = await apiFetch(`${API_BASE}/v1/config/categories/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setCategories(prev => prev.filter(c => c.id !== id));
        toast.success('دسته‌بندی حذف شد', `دسته‌بندی «${name}» حذف شد.`);
      } else {
        const errData = await res.json();
        toast.error('خطا در حذف دسته‌بندی', errData.detail);
      }
    } catch (err) {
      console.error(err);
      toast.error('خطا در ارتباط با سرور');
    }
  };

  return (
    <div className="screen fade-in">
      <PageHeader
        icon={<FolderTree size={20} style={{ color: 'var(--copper)' }} />}
        title="مدیریت دسته‌بندی‌ها"
        actions={
          currentUser?.role === 'Admin' && (
            <button className="ax-btn ax-btn--primary" onClick={() => handleOpenModal()}>
              <Plus size={16} /> افزودن دسته‌بندی
            </button>
          )
        }
      />

      <div className="admin-grid">
        <div className="admin-card">
          <div className="admin-card-title">
            <Sparkles size={17} />
            عامل دسته‌بندی (Categorical Agent)
          </div>
          <div
            style={{
              background: 'var(--gray-50)',
              padding: '14px 16px',
              borderRadius: 'var(--radius)',
              border: '1px solid var(--gray-100)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 12,
              cursor: 'pointer',
            }}
            onClick={() => toggleFeature('checkCategories')}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontWeight: 600, color: 'var(--heading)', fontSize: 13 }}>فعال‌سازی در جریان RAG</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>با فعال‌سازی، هوش مصنوعی موضوع سوال را تشخیص می‌دهد.</span>
            </div>
            <Switch checked={!!features.checkCategories} onChange={() => toggleFeature('checkCategories')} aria-label="فعال‌سازی عامل دسته‌بندی" />
          </div>
        </div>

        <div className="card" style={{ gridColumn: '1 / -1' }}>
          <div className="card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <ListTree size={17} style={{ color: 'var(--copper)' }} />
              لیست دسته‌بندی‌های سیستم
            </span>
            <span className="ax-badge ax-badge--neutral">{categories.length} دسته</span>
          </div>

          {isLoading ? (
            <div style={{ padding: 20 }}>
              {[0, 1, 2].map(i => <div key={i} className="ax-skeleton ax-skeleton--text" style={{ height: 40, marginBottom: 10 }} />)}
            </div>
          ) : categories.length === 0 ? (
            <EmptyState
              title="هیچ دسته‌بندی ثبت نشده است"
              desc="با دکمه «افزودن دسته‌بندی» اولین دسته را بسازید."
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {categories.map(cat => (
                <div
                  key={cat.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 16,
                    padding: '13px 8px',
                    borderBottom: '1px solid var(--gray-50)',
                    fontSize: 13,
                  }}
                >
                  <span style={{ color: 'var(--text-muted)', fontWeight: 'bold', fontSize: 12, minWidth: 36 }}>#{cat.id}</span>
                  <span style={{ fontWeight: 600, color: 'var(--heading)', minWidth: 160 }}>{cat.name}</span>
                  <span style={{ color: 'var(--text-secondary)', flex: 1, fontSize: 12.5, lineHeight: 1.6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {cat.description || '—'}
                  </span>
                  <Badge variant={cat.is_active ? 'success' : 'neutral'}>{cat.is_active ? 'فعال' : 'غیرفعال'}</Badge>
                  {currentUser?.role === 'Admin' && (
                    <span style={{ display: 'flex', gap: 6 }}>
                      <button className="icon-btn" onClick={() => handleOpenModal(cat)} title="ویرایش" aria-label="ویرایش">
                        <Pencil size={15} style={{ color: 'var(--copper)' }} />
                      </button>
                      <button className="icon-btn icon-btn--danger" onClick={() => handleDelete(cat.id, cat.name)} title="حذف" aria-label="حذف">
                        <Trash2 size={15} />
                      </button>
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <Modal
        open={showModal}
        onClose={handleCloseModal}
        title={editId ? 'ویرایش دسته‌بندی' : 'افزودن دسته‌بندی جدید'}
      >
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Input
            label="نام دسته‌بندی"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="مثال: رسید بانکی"
            required
          />
          <Textarea
            label="توضیحات (اختیاری)"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="توضیحات مربوط به این دسته..."
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-primary)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
            />
            دسته‌بندی فعال باشد
          </label>
          <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
            <button type="submit" className="ax-btn ax-btn--primary" style={{ flex: 1 }}>
              {editId ? 'ذخیره تغییرات' : 'ایجاد دسته‌بندی'}
            </button>
            <button type="button" className="ax-btn ax-btn--secondary" style={{ flex: 1 }} onClick={handleCloseModal}>
              انصراف
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
