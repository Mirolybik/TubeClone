import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { PlayIcon } from '../icons';

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const from = location.state?.from && location.state.from !== '/register' ? location.state.from : '/';

  useEffect(() => {
    if (user) navigate(from, { replace: true });
  }, [user, from, navigate]);

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('Пароли не совпадают');
      return;
    }
    if (password.length < 6) {
      setError('Пароль должен быть не короче 6 символов');
      return;
    }
    setBusy(true);
    try {
      await register({
        email: email.trim(),
        username: username.trim(),
        display_name: displayName.trim() || null,
        password,
      });
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
        <h1>Создать аккаунт</h1>
        <p className="muted">Первый зарегистрированный пользователь становится администратором.</p>

        <form className="form" onSubmit={submit}>
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label className="field">
            <span>Username</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              pattern="[A-Za-z0-9_]+"
              minLength={3}
              maxLength={30}
              placeholder="latin_letters_and_digits"
              required
            />
            <span className="hint">Латиница, цифры и _, от 3 до 30 символов. Используется в адресе канала.</span>
          </label>
          <label className="field">
            <span>Отображаемое имя (необязательно)</span>
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={80} />
          </label>
          <div className="form-row">
            <label className="field">
              <span>Пароль</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={6}
                maxLength={72}
                autoComplete="new-password"
                required
              />
            </label>
            <label className="field">
              <span>Повторите пароль</span>
              <input
                type="password"
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
                minLength={6}
                maxLength={72}
                autoComplete="new-password"
                required
              />
            </label>
          </div>
          {error ? <div className="alert alert-error">{error}</div> : null}
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? 'Создание…' : 'Зарегистрироваться'}
          </button>
        </form>

        <p className="auth-switch">
          Уже есть аккаунт? <Link to="/login" state={{ from }}>Войти</Link>
        </p>
      </div>
    </div>
  );
}
