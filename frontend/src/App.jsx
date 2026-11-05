import { useEffect } from 'react';
import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider } from './auth';
import Layout from './components/Layout';
import { ProtectedRoute, RoleRoute } from './components/ProtectedRoute';
import { ToastProvider } from './components/Toast';
import AdminPage from './pages/AdminPage';
import ChannelPage from './pages/ChannelPage';
import HistoryPage from './pages/HistoryPage';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import ModerationPage from './pages/ModerationPage';
import NotFoundPage from './pages/NotFoundPage';
import PlaylistPage from './pages/PlaylistPage';
import RegisterPage from './pages/RegisterPage';
import SearchPage from './pages/SearchPage';
import SubscriptionsPage from './pages/SubscriptionsPage';
import UploadPage from './pages/UploadPage';
import WatchPage from './pages/WatchPage';

function ScrollToTop() {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <ScrollToTop />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route element={<Layout />}>
              <Route index element={<HomePage />} />
              <Route path="watch/:id" element={<WatchPage />} />
              <Route path="channel/:username" element={<ChannelPage />} />
              <Route path="playlist/:id" element={<PlaylistPage />} />
              <Route path="search" element={<SearchPage />} />
              <Route
                path="upload"
                element={
                  <ProtectedRoute>
                    <UploadPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="subscriptions"
                element={
                  <ProtectedRoute>
                    <SubscriptionsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="history"
                element={
                  <ProtectedRoute>
                    <HistoryPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="moderation"
                element={
                  <RoleRoute roles={['moderator', 'admin']}>
                    <ModerationPage />
                  </RoleRoute>
                }
              />
              <Route
                path="admin"
                element={
                  <RoleRoute roles={['admin']}>
                    <AdminPage />
                  </RoleRoute>
                }
              />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
