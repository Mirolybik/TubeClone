import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { canModerate, isAdmin, useAuth } from '../auth';
import { channelName, classNames } from '../utils';
import Avatar from './Avatar';
import {
  ChartIcon,
  CloseIcon,
  HistoryIcon,
  HomeIcon,
  ListIcon,
  LogoutIcon,
  MenuIcon,
  PlayIcon,
  SearchIcon,
  SettingsIcon,
  ShieldIcon,
  SubscriptionsIcon,
  UploadIcon,
  UserIcon,
} from '../icons';

const baseNav = [
  { to: '/', label: 'Главная', icon: HomeIcon, end: true },
  { to: '/subscriptions', label: 'Подписки', icon: SubscriptionsIcon, auth: true },
  { to: '/history', label: 'История', icon: HistoryIcon, auth: true },
  { to: '/upload', label: 'Загрузить видео', icon: UploadIcon, auth: true },
];

function mobileNavFor(user) {
  if (!user) {
    return [
      { to: '/', label: 'Главная', icon: HomeIcon, end: true },
      { to: '/subscriptions', label: 'Подписки', icon: SubscriptionsIcon },
      { to: '/upload', label: 'Создать', icon: UploadIcon, primary: true },
      { to: '/login', label: 'Войти', icon: UserIcon },
    ];
  }
  return [
    { to: '/', label: 'Главная', icon: HomeIcon, end: true },
    { to: '/subscriptions', label: 'Подписки', icon: SubscriptionsIcon },
    { to: '/upload', label: 'Создать', icon: UploadIcon, primary: true },
    { to: '/history', label: 'История', icon: HistoryIcon },
    { to: `/channel/${user.username}`, label: 'Канал', icon: UserIcon },
  ];
}

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(
    () => !window.matchMedia('(max-width: 1050px)').matches
  );
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState('');
  const menuRef = useRef(null);

  useEffect(() => {
    // На мобильных меню закрывается после перехода, на десктопе остаётся открытым.
    if (window.matchMedia('(max-width: 1050px)').matches) {
      setSidebarOpen(false);
    }
    setMenuOpen(false);
    if (location.pathname === '/search') {
      setQuery(new URLSearchParams(location.search).get('q') || '');
    }
  }, [location.pathname, location.search]);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 1050px)');
    const onChange = (event) => setSidebarOpen(!event.matches);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    const onClick = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const submitSearch = (event) => {
    event.preventDefault();
    const value = query.trim();
    if (value) navigate(`/search?q=${encodeURIComponent(value)}`);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-left">
          <button
            type="button"
            className="icon-button mobile-menu-button"
            onClick={() => setSidebarOpen((value) => !value)}
            aria-label={sidebarOpen ? 'Скрыть меню' : 'Открыть меню'}
            aria-expanded={sidebarOpen}
            aria-controls="app-sidebar"
          >
            <MenuIcon />
          </button>
          <Link className="logo" to="/" aria-label="TubeClone — на главную">
            <span className="logo-mark">
              <PlayIcon size={18} />
            </span>
            <span className="logo-text">
              Tube<span>Clone</span>
            </span>
          </Link>
        </div>

        <form className="topbar-search" onSubmit={submitSearch} role="search">
          <SearchIcon size={19} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Поиск по названию"
            aria-label="Поиск по названию"
          />
          {query ? (
            <button type="button" className="icon-button small" onClick={() => setQuery('')} aria-label="Очистить">
              <CloseIcon size={15} />
            </button>
          ) : null}
        </form>

        <div className="topbar-actions">
          {user ? (
            <>
              <Link className="upload-button" to="/upload">
                <UploadIcon size={18} />
                <span>Загрузить</span>
              </Link>
              <div className="user-menu-wrap" ref={menuRef}>
                <button
                  type="button"
                  className="avatar-button"
                  onClick={() => setMenuOpen((value) => !value)}
                  aria-label="Меню пользователя"
                >
                  <Avatar user={user} size={34} />
                </button>
                {menuOpen ? (
                  <div className="dropdown user-dropdown">
                    <div className="dropdown-head">
                      <Avatar user={user} size={42} />
                      <div>
                        <strong>{channelName(user)}</strong>
                        <span>@{user.username}</span>
                      </div>
                    </div>
                    <Link to={`/channel/${user.username}`}>
                      <UserIcon size={18} /> Мой канал
                    </Link>
                    <Link to="/subscriptions">
                      <SubscriptionsIcon size={18} /> Подписки
                    </Link>
                    <Link to="/history">
                      <HistoryIcon size={18} /> История
                    </Link>
                    <Link to="/upload">
                      <UploadIcon size={18} /> Загрузить видео
                    </Link>
                    {canModerate(user) ? (
                      <Link to="/moderation">
                        <ShieldIcon size={18} /> Модерация
                      </Link>
                    ) : null}
                    {isAdmin(user) ? (
                      <Link to="/admin">
                        <ChartIcon size={18} /> Админ-панель
                      </Link>
                    ) : null}
                    <div className="dropdown-divider" />
                    <a href="/docs" target="_blank" rel="noreferrer">
                      <ListIcon size={18} /> API / Swagger
                    </a>
                    <button type="button" onClick={handleLogout}>
                      <LogoutIcon size={18} /> Выйти
                    </button>
                  </div>
                ) : null}
              </div>
            </>
          ) : (
            <div className="auth-actions">
              <Link className="btn btn-ghost btn-sm" to="/register">
                Регистрация
              </Link>
              <Link className="btn btn-primary btn-sm" to="/login">
                Войти
              </Link>
            </div>
          )}
        </div>
      </header>

      <div className="app-body">
        {sidebarOpen ? <button type="button" className="sidebar-scrim" onClick={() => setSidebarOpen(false)} /> : null}
        <aside
          id="app-sidebar"
          className={classNames('sidebar', sidebarOpen && 'open', !sidebarOpen && 'sidebar-collapsed')}
        >
          <nav className="sidebar-nav">
            {baseNav
              .filter((item) => !item.auth || user)
              .map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => classNames('nav-item', isActive && 'active')}
                >
                  <item.icon size={21} />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            {user ? (
              <NavLink
                to={`/channel/${user.username}`}
                className={({ isActive }) => classNames('nav-item', isActive && 'active')}
              >
                <UserIcon size={21} />
                <span>Мой канал</span>
              </NavLink>
            ) : null}
          </nav>

          {canModerate(user) ? (
            <div className="sidebar-section">
              <span className="sidebar-title">Управление</span>
              <NavLink
                to="/moderation"
                className={({ isActive }) => classNames('nav-item', isActive && 'active')}
              >
                <ShieldIcon size={21} />
                <span>Модерация</span>
              </NavLink>
              {isAdmin(user) ? (
                <NavLink to="/admin" className={({ isActive }) => classNames('nav-item', isActive && 'active')}>
                  <ChartIcon size={21} />
                  <span>Админ-панель</span>
                </NavLink>
              ) : null}
            </div>
          ) : null}

          <div className="sidebar-section">
            <span className="sidebar-title">Сервис</span>
            <a className="nav-item" href="/docs" target="_blank" rel="noreferrer">
              <SettingsIcon size={21} />
              <span>Swagger API</span>
            </a>
          </div>

          <div className="sidebar-footer">
            <p>Демо-аккаунты</p>
            <code>user / User123!</code>
            <code>moderator / Moder123!</code>
            <code>admin / Admin123!</code>
          </div>
        </aside>

        <main className="main-content">
          <Outlet />
        </main>
      </div>

      <nav className="mobile-bottom-nav" aria-label="Мобильная навигация">
        {mobileNavFor(user).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              classNames('bottom-nav-item', item.primary && 'primary', isActive && 'active')
            }
          >
            <span className="bottom-nav-icon">
              <item.icon size={22} />
            </span>
            <span className="bottom-nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
