import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';

export default function CategoriesView() {
  const { apiFetch, features, toggleFeature, currentUser } = useApp();
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Form states
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState(null);
  const [formData, setFormData] = useState({ name: '', description: '', is_active: true });

  const fetchCategories = async () => {
    try {
      setIsLoading(true);
      const res = await apiFetch('http://localhost:8000/v1/config/categories');
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
    fetchCategories();
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
    if (!formData.name.trim()) return alert('نام دسته‌بندی الزامی است.');

    try {
      const url = editId 
        ? `http://localhost:8000/v1/config/categories/${editId}`
        : 'http://localhost:8000/v1/config/categories';
      const method = editId ? 'PUT' : 'POST';

      const res = await apiFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (res.ok) {
        await fetchCategories();
        handleCloseModal();
      } else {
        const errData = await res.json();
        alert(errData.detail || 'خطا در ذخیره دسته‌بندی');
      }
    } catch (err) {
      console.error(err);
      alert('خطا در ارتباط با سرور');
    }
  };

  const handleDelete = async (id, name) => {
    if (!confirm(`آیا از حذف دسته‌بندی "${name}" اطمینان دارید؟`)) return;
    try {
      const res = await apiFetch(`http://localhost:8000/v1/config/categories/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setCategories(prev => prev.filter(c => c.id !== id));
      } else {
        const errData = await res.json();
        alert(errData.detail || 'خطا در حذف دسته‌بندی');
      }
    } catch (err) {
      console.error(err);
      alert('خطا در ارتباط با سرور');
    }
  };

  return (
    <div className="screen fade-in">
      <div className="admin-grid">
        <div 
          className="admin-card" 
          style={{ 
            border: '1px solid rgba(43, 61, 80, 0.08)', 
            boxShadow: '0 8px 24px rgba(43, 61, 80, 0.04)', 
            borderRadius: '12px',
            background: 'linear-gradient(to bottom right, #ffffff, #fdfdfd)',
            padding: '24px',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          {/* Decorative subtle accent line */}
          <div style={{ position: 'absolute', top: 0, right: 0, left: 0, height: '4px', background: 'linear-gradient(90deg, var(--navy), var(--copper))' }}></div>
          
          <div className="admin-card-title" style={{ fontSize: '17px', color: 'var(--navy)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '20px' }}>🗂️</span> مدیریت عامل دسته‌بندی <span style={{ color: 'var(--copper)', fontSize: '14px', opacity: 0.9 }}>(Categorical Agent)</span>
          </div>
          <div style={{fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.8', paddingRight: '4px'}}>
            عامل دسته‌بندی به هوش مصنوعی اجازه می‌دهد تا اسناد و منابع را بر اساس فیلدهای خاص فیلتر کند و نتایج جستجوی بسیار دقیق‌تری برای پرسمان‌های مرتبط ارائه دهد.
          </div>
          <div 
            className="toggle-row" 
            style={{ 
              background: 'var(--gray-50)', 
              padding: '12px 16px', 
              borderRadius: '8px', 
              border: '1px solid var(--gray-100)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              cursor: 'pointer'
            }}
            onClick={() => toggleFeature('checkCategories')}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span className="toggle-label" style={{ fontWeight: '600', color: 'var(--navy)', fontSize: '13px' }}>فعال‌سازی عامل دسته‌بندی در جریان RAG</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>با فعال‌سازی این گزینه، هوش مصنوعی موضوع سوال را تشخیص می‌دهد.</span>
            </div>
            <div 
              className={`toggle ${features.checkCategories ? 'toggle-on' : 'toggle-off'}`} 
            />
          </div>
        </div>

        <div className="card" style={{ gridColumn: '1 / -1', border: '1px solid var(--gray-100)', boxShadow: '0 4px 15px rgba(0,0,0,0.03)' }}>
          <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '15px', borderBottom: '1px solid var(--gray-50)', marginBottom: '15px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px' }}>📋</span>
              <span style={{ fontSize: '15px', fontWeight: 'bold' }}>لیست دسته‌بندی‌های سیستم</span>
            </div>
            {currentUser?.role === 'Admin' && (
              <button 
                className="topbar-btn btn-primary" 
                onClick={() => handleOpenModal()}
                style={{ padding: '6px 14px', fontSize: '12.5px', borderRadius: '8px' }}
              >
                + افزودن دسته‌بندی جدید
              </button>
            )}
          </div>
          
          <div className="files-table" style={{ background: '#fff', borderRadius: '8px' }}>
            <div className="ft-header" style={{
              gridTemplateColumns: '80px 2fr 3fr 100px 100px', 
              background: 'var(--gray-50)', 
              color: 'var(--text-secondary)',
              borderBottom: '1px solid var(--gray-100)',
              padding: '12px 16px',
              fontSize: '12px',
              fontWeight: '600'
            }}>
              <div>شناسه</div>
              <div>نام دسته‌بندی</div>
              <div>توضیحات</div>
              <div style={{textAlign: 'center'}}>وضعیت</div>
              <div style={{textAlign: 'center'}}>عملیات</div>
            </div>
            
            {isLoading ? (
              <div style={{padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px'}}>در حال بارگذاری...</div>
            ) : categories.length === 0 ? (
              <div style={{padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px', background: 'var(--gray-50)', borderRadius: '8px', marginTop: '10px'}}>
                هیچ دسته‌بندی ثبت نشده است.
              </div>
            ) : (
              categories.map(cat => (
                <div key={cat.id} className="ft-row" style={{
                  gridTemplateColumns: '80px 2fr 3fr 100px 100px',
                  padding: '16px',
                  borderBottom: '1px solid var(--gray-50)',
                  alignItems: 'center',
                  transition: 'background 0.2s',
                  cursor: 'default'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--gray-50)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <div style={{color: 'var(--text-muted)', fontWeight: 'bold', fontSize: '13px'}}>#{cat.id}</div>
                  <div style={{fontWeight: '600', color: 'var(--navy)', fontSize: '13.5px'}}>{cat.name}</div>
                  <div style={{color: 'var(--text-secondary)', fontSize: '12.5px', lineHeight: '1.6'}}>{cat.description || '-'}</div>
                  <div style={{textAlign: 'center'}}>
                    <span className={`perm-badge ${cat.is_active ? 'p-admin' : 'p-analyst'}`} style={{
                      background: cat.is_active ? 'rgba(46, 125, 50, 0.1)' : 'var(--gray-100)', 
                      color: cat.is_active ? '#2e7d32' : 'var(--text-muted)',
                      border: cat.is_active ? '1px solid rgba(46, 125, 50, 0.2)' : '1px solid var(--gray-200)',
                      padding: '4px 10px',
                      borderRadius: '20px',
                      fontSize: '11px'
                    }}>
                      {cat.is_active ? 'فعال' : 'غیرفعال'}
                    </span>
                  </div>
                  <div style={{display: 'flex', gap: '8px', justifyContent: 'center'}}>
                    {currentUser?.role === 'Admin' && (
                      <>
                        <button
                          onClick={() => handleOpenModal(cat)}
                          style={{background: 'var(--gray-50)', border: '1px solid var(--gray-200)', borderRadius: '6px', padding: '6px', color: 'var(--copper)', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center'}}
                          title="ویرایش"
                          onMouseEnter={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.borderColor = 'var(--copper)'}}
                          onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--gray-50)'; e.currentTarget.style.borderColor = 'var(--gray-200)'}}
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDelete(cat.id, cat.name)}
                          style={{background: 'var(--gray-50)', border: '1px solid var(--gray-200)', borderRadius: '6px', padding: '6px', color: '#c62828', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center'}}
                          title="حذف"
                          onMouseEnter={(e) => { e.currentTarget.style.background = '#ffebee'; e.currentTarget.style.borderColor = '#ef9a9a'}}
                          onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--gray-50)'; e.currentTarget.style.borderColor = 'var(--gray-200)'}}
                        >
                          🗑️
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {showModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(0, 0, 0, 0.4)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999
        }}>
          <div className="fade-in" style={{
            background: 'white', maxWidth: '450px', width: '90%', 
            padding: '24px', borderRadius: '12px', position: 'relative',
            boxShadow: '0 10px 30px rgba(0,0,0,0.1)'
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
              marginBottom: '20px', paddingBottom: '15px', borderBottom: '1px solid var(--gray-100)'
            }}>
              <h3 style={{margin: 0, fontSize: '17px', color: 'var(--navy)'}}>{editId ? 'ویرایش دسته‌بندی' : 'افزودن دسته‌بندی جدید'}</h3>
              <button 
                onClick={handleCloseModal} 
                style={{
                  background: 'none', border: 'none', fontSize: '22px', 
                  cursor: 'pointer', color: 'var(--text-muted)', lineHeight: 1
                }}
              >×</button>
            </div>
            <form onSubmit={handleSave} style={{padding: '20px', display: 'flex', flexDirection: 'column', gap: '15px'}}>
              <div>
                <label style={{display: 'block', marginBottom: '8px', fontSize: '13px', fontWeight: 'bold', color: 'var(--navy)'}}>نام دسته‌بندی</label>
                <input 
                  type="text"
                  className="chat-input-box"
                  style={{width: '100%', fontSize: '13px', borderRadius: '6px'}}
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="مثال: رسید بانکی"
                  required
                />
              </div>
              <div>
                <label style={{display: 'block', marginBottom: '8px', fontSize: '13px', fontWeight: 'bold', color: 'var(--navy)'}}>توضیحات (اختیاری)</label>
                <textarea 
                  className="chat-input-box"
                  style={{width: '100%', fontSize: '13px', borderRadius: '6px', minHeight: '80px'}}
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  placeholder="توضیحات مربوط به این دسته..."
                />
              </div>
              <div style={{display: 'flex', alignItems: 'center', gap: '10px', marginTop: '5px'}}>
                <input 
                  type="checkbox" 
                  id="cat-active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                />
                <label htmlFor="cat-active" style={{fontSize: '13px', color: 'var(--text-primary)', cursor: 'pointer'}}>دسته‌بندی فعال باشد</label>
              </div>
              
              <div style={{display: 'flex', gap: '10px', marginTop: '20px'}}>
                <button type="submit" className="topbar-btn btn-primary" style={{flex: 1, justifyContent: 'center'}}>
                  {editId ? 'ذخیره تغییرات' : 'ایجاد دسته‌بندی'}
                </button>
                <button type="button" className="topbar-btn btn-ghost" style={{flex: 1, justifyContent: 'center'}} onClick={handleCloseModal}>
                  انصراف
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
