import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';

export function PageLoader({ label = 'Загрузка…' }) {
  return (
    <div className="page-loader">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  );
}

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <PageLoader />;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return children;
}

export function RoleRoute({ roles, children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <PageLoader />;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  if (!roles.includes(user.role)) {
    return (
      <div className="empty-state">
        <h2>Недостаточно прав</h2>
        <p>Для этого раздела нужна роль: {roles.join(' или ')}.</p>
      </div>
    );
  }
  return children;
}
