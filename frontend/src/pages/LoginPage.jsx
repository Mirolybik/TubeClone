import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { PlayIcon } from '../icons';

const DEMO_ACCOUNTS = [
  { login: 'user', password: 'User123!', label: 'Пользователь', note: 'смотрит, лайкает, комментирует' },
  { login: 'moderator', password: 'Moder123!', label: 'Модератор', note: 'жалобы и скрытие видео' },
  { login: 'admin', password: 'Admin123!', label: 'Администратор', note: 'роли и управление сервисом' },
  { login: 'creator', password: 'Creator123!', label: 'Автор', note: 'свои видео и приватный доступ' },
];

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [loginValue, setLoginValue] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const from = location.state?.from && location.state.from !== '/login' ? location.state.from : '/';

  useEffect(() => {
    if (user) navigate(from, { replace: true });
  }, [user, from, navigate]);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(loginValue.trim(), password);
      navigate(from, { replace: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <Link className="auth-logo" to="/">
          <span className="logo-mark"><PlayIcon size={18} /></span>
          <span className="logo-text">Tube<span>Clone</span></span>
        </Link>
        <h1>Вход в аккаунт</h1>
        <p className="muted">Смотрите, загружайте и модерируйте видео.</p>

        <form className="form" onSubmit={submit}>
          <label className="field">
            <span>Email или username</span>
            <input
              value={loginValue}
              onChange={(event) => setLoginValue(event.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="field">
            <span>Пароль</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error ? <div className="alert alert-error">{error}</div> : null}
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? 'Вход…' : 'Войти'}
          </button>
        </form>

        <p className="auth-switch">
          Нет аккаунта? <Link to="/register" state={{ from }}>Зарегистрироваться</Link>
        </p>

        <div className="demo-accounts">
          <span className="sidebar-title">Демо-аккаунты — нажмите, чтобы заполнить</span>
          {DEMO_ACCOUNTS.map((account) => (
            <button
              key={account.login}
              type="button"
              className="demo-account"
              onClick={() => {
                setLoginValue(account.login);
                setPassword(account.password);
              }}
            >
              <span>
                <strong>{account.label}</strong>
                <small>{account.note}</small>
              </span>
              <code>{account.login} / {account.password}</code>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
