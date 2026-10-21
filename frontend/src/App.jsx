import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatShell from './components/ChatShell';
import SettingsPage from './pages/SettingsPage';
import AuthModal from './pages/AuthModal';
import ProfilePage from './pages/ProfilePage';
import ResumeReviewPage from './pages/ResumeReviewPage';
import ReadinessScorePage from './pages/ReadinessScorePage';
import MockInterviewPage from './pages/MockInterviewPage';
import JobDiscoveryPage from './pages/JobDiscoveryPage';
import ApplicationTrackerPage from './pages/ApplicationTrackerPage';
import AdminJobBoardPage from './pages/AdminJobBoardPage';
import { api, getStoredUser, clearAuth } from './api';
import { JobProvider } from './context/JobContext';


export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [currentUser, setCurrentUser] = useState(getStoredUser());
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [settings, setSettings] = useState(null);

  useEffect(() => {
    // Initial fetch of settings
    api.getSettings()
      .then((data) => setSettings(data))
      .catch((err) => console.error("Could not fetch settings:", err));

    // Refresh user if token present
    if (currentUser) {
      api.getMe()
        .then((user) => setCurrentUser(user))
        .catch(() => {
          // Token expired or invalid
          clearAuth();
          setCurrentUser(null);
        });
    }
  }, []);

  const handleLogout = () => {
    clearAuth();
    setCurrentUser(null);
    setActiveTab('chat');
  };

  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
  };

  const enableMockInterview = settings?.enable_mock_interview ?? false;

  return (
    <JobProvider>
      <div className="flex h-screen w-screen overflow-hidden bg-slate-900 text-slate-100 font-sans">
        {/* Sidebar Navigation */}
        <Sidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          currentUser={currentUser}
          onLogout={handleLogout}
          onOpenAuth={() => setIsAuthOpen(true)}
          enableMockInterview={enableMockInterview}
        />

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col h-full overflow-hidden">
          {activeTab === 'chat' && (
            <ChatShell currentUser={currentUser} settings={settings} />
          )}

          {activeTab === 'profile' && (
            <ProfilePage currentUser={currentUser} onLogout={handleLogout} />
          )}

          {activeTab === 'reviews' && (
            <ResumeReviewPage
              currentUser={currentUser}
              onNavigateToProfile={() => setActiveTab('profile')}
            />
          )}

          {activeTab === 'interview' && enableMockInterview && (
            <MockInterviewPage
              currentUser={currentUser}
              onNavigateTab={setActiveTab}
            />
          )}

          {activeTab === 'score' && (
            <ReadinessScorePage
              currentUser={currentUser}
              onNavigateTab={setActiveTab}
              enableMockInterview={enableMockInterview}
            />
          )}

          {activeTab === 'jobs' && (
            <JobDiscoveryPage
              currentUser={currentUser}
              onNavigateTab={setActiveTab}
            />
          )}

          {activeTab === 'tracker' && <ApplicationTrackerPage currentUser={currentUser} />}

          {activeTab === 'settings' && (
            <SettingsPage
              onSettingsUpdated={(updated) => setSettings(updated)}
            />
          )}

          {activeTab === 'admin' && (
            <AdminJobBoardPage currentUser={currentUser} />
          )}

        </main>

        {/* Auth Modal */}
        <AuthModal
          isOpen={isAuthOpen}
          onClose={() => setIsAuthOpen(false)}
          onAuthSuccess={handleAuthSuccess}
        />
      </div>
    </JobProvider>
  );
}
