import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { channelName, formatCount, formatDate, qs, roleLabel } from '../utils';
import { ChartIcon, FilmIcon, FlagIcon, ShieldIcon, UserIcon } from '../icons';
import Avatar from '../components/Avatar';
import Pager from '../components/Pager';
import { useToast } from '../components/Toast';

function StatCard({ icon: Icon, label, value, tone = '' }) {
  return (
    <div className={`stat-card ${tone}`}>
      <span className="stat-icon"><Icon size={20} /></span>
      <div>
        <strong>{formatCount(value)}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const { user: currentUser } = useAuth();
  const { push } = useToast();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState(null);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/admin/stats').then(setStats).catch(() => setStats(null));
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api
      .get(`/admin/users${qs({ q: query, page, page_size: 20 })}`)
      .then((data) => active && setUsers(data))
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [query, page]);

  const updateUser = async (target, payload) => {
    try {
      const updated = await api.patch(`/admin/users/${target.id}`, payload);
      setUsers((current) => ({
        ...current,
        items: current.items.map((item) => (item.id === updated.id ? updated : item)),
      }));
      push('Пользователь обновлён');
    } catch (error) {
      push(error.message, 'error');
    }
  };

  const submitSearch = (event) => {
    event.preventDefault();
    setPage(1);
    setQuery(search.trim());
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Админ-панель</h1>
          <p className="page-subtitle">Пользователи, роли, блокировки и статистика сервиса</p>
        </div>
        <span className="badge badge-danger"><ShieldIcon size={14} /> Администратор</span>
      </div>

      {stats ? (
        <div className="stats-grid">
          <StatCard icon={UserIcon} label="Пользователи" value={stats.users_count} />
          <StatCard icon={FilmIcon} label="Видео" value={stats.videos_count} />
          <StatCard icon={ChartIcon} label="Просмотры" value={stats.views_total} />
          <StatCard icon={FlagIcon} label="Открытые жалобы" value={stats.reports_open} tone="warning" />
          <StatCard icon={FilmIcon} label="Публичные видео" value={stats.public_videos_count} />
          <StatCard icon={ShieldIcon} label="Скрытые видео" value={stats.hidden_videos_count} tone="danger" />
          <StatCard icon={UserIcon} label="Подписки" value={stats.subscriptions_count} />
          <StatCard icon={ChartIcon} label="Комментарии / лайки" value={stats.comments_count + stats.likes_count} />
        </div>
      ) : null}

      <div className="table-card">
        <div className="table-head">
          <h2>Пользователи</h2>
          <form className="table-search" onSubmit={submitSearch}>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Поиск по username, email или имени"
            />
            <button type="submit" className="btn btn-ghost btn-sm">Найти</button>
          </form>
        </div>

        {error ? <div className="alert alert-error">{error}</div> : null}
        {loading ? <div className="page-loader"><span className="spinner" /> Загрузка пользователей…</div> : null}

        {users ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Пользователь</th>
                  <th>Email</th>
                  <th>Роль</th>
                  <th>Видео</th>
                  <th>Подписчики</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.items.map((item) => {
                  const isSelf = item.id === currentUser.id;
                  return (
                    <tr key={item.id}>
                      <td>
                        <Link className="table-user" to={`/channel/${item.username}`}>
                          <Avatar user={item} size={34} />
                          <span>
                            <strong>{channelName(item)}</strong>
                            <small>@{item.username} · с {formatDate(item.created_at)}</small>
                          </span>
                        </Link>
                      </td>
                      <td className="muted">{item.email}</td>
                      <td>
                        <select
                          value={item.role}
                          disabled={isSelf}
                          onChange={(event) => updateUser(item, { role: event.target.value })}
                        >
                          {['user', 'moderator', 'admin'].map((role) => (
                            <option key={role} value={role}>
                              {roleLabel(role)}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>{item.videos_count}</td>
                      <td>{item.subscribers_count}</td>
                      <td>
                        <span className={`badge ${item.is_active ? 'badge-success' : 'badge-danger'}`}>
                          {item.is_active ? 'Активен' : 'Заблокирован'}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          disabled={isSelf}
                          onClick={() => updateUser(item, { is_active: !item.is_active })}
                        >
                          {item.is_active ? 'Заблокировать' : 'Разблокировать'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {!users.items.length ? <p className="muted" style={{ padding: 18 }}>Пользователи не найдены.</p> : null}
          </div>
        ) : null}

        {users ? <Pager page={users.page} pages={users.pages} onChange={setPage} /> : null}
      </div>
    </div>
  );
}
