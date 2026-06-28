import React from 'react';
import './App.css';
import { AppProvider, useApp } from './context/AppContext';
import Sidebar from './components/Layout/Sidebar';
import Topbar from './components/Layout/Topbar';
import InviteModal from './components/Modals/InviteModal';
import LoginView from './views/Auth/LoginView';
import DashboardView from './views/Dashboard/DashboardView';
import ChatView from './views/Chat/ChatView';
import KnowledgeView from './views/Knowledge/KnowledgeView';
import UploadView from './views/Upload/UploadView';
import CrawlerView from './views/Crawler/CrawlerView';
import AdminView from './views/Admin/AdminView';
import IntegrationsView from './views/Integrations/IntegrationsView';
import CategoriesView from './views/Categories/CategoriesView';

function DashboardLayout() {
  const { currentUser, activeScreen } = useApp();

  if (!currentUser) {
    return <LoginView />;
  }

  return (
    <div className="device-frame fade-in">
      <Sidebar />
      <div className="main">
        <Topbar />
        
        {activeScreen === 'dashboard' && <DashboardView />}
        {activeScreen === 'chat' && <ChatView />}
        {activeScreen === 'knowledge' && <KnowledgeView />}
        {activeScreen === 'upload' && <UploadView />}
        {activeScreen === 'crawler' && <CrawlerView />}
        {activeScreen === 'admin' && <AdminView />}
        {activeScreen === 'integrations' && <IntegrationsView />}
        {activeScreen === 'categories' && <CategoriesView />}
        
        <div className="wf-tag">ArioNex Commercial AI — v1.0.0</div>
      </div>
      <InviteModal />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <DashboardLayout />
    </AppProvider>
  );
}
