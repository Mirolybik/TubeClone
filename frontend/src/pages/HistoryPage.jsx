import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { channelName, formatDate, formatDuration, formatViews } from '../utils';
import { ClockIcon, HistoryIcon, TrashIcon } from '../icons';
import { useToast } from '../components/Toast';

export default function HistoryPage() {
  const { push } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get('/history');
      setItems(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const remove = async (videoId) => {
    try {
      await api.delete(`/history/${videoId}`);
      setItems((current) => current.filter((item) => item.video.id !== videoId));
      push('Запись удалена из истории');
    } catch (requestError) {
      push(requestError.message, 'error');
    }
  };

  const clear = async () => {
    if (!window.confirm('Очистить всю историю просмотров?')) return;
    try {
      await api.delete('/history');
      setItems([]);
      push('История очищена');
    } catch (requestError) {
      push(requestError.message, 'error');
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>История просмотров</h1>
          <p className="page-subtitle">Последние просмотренные видео</p>
        </div>
        {items.length ? (
          <button type="button" className="btn btn-ghost btn-sm danger" onClick={clear}>
            <TrashIcon size={16} /> Очистить
          </button>
        ) : null}
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading ? <div className="page-loader"><span className="spinner" /> Загрузка истории…</div> : null}

      {!loading && !items.length ? (
        <div className="empty-state">
          <HistoryIcon size={48} />
          <h2>История пуста</h2>
          <p>Посмотрите какое-нибудь видео — оно появится здесь.</p>
          <Link className="btn btn-primary" to="/">
            На главную
          </Link>
        </div>
      ) : null}

      {items.length ? (
        <div className="history-list">
          {items.map((item) => (
            <div className="history-row" key={item.video.id}>
              <Link className="history-thumb" to={`/watch/${item.video.id}`}>
                <img src={item.video.thumbnail_url} alt={item.video.title} loading="lazy" />
                {item.video.duration_seconds ? (
                  <span className="duration-badge">{formatDuration(item.video.duration_seconds)}</span>
                ) : null}
              </Link>
              <div className="history-info">
                <Link to={`/watch/${item.video.id}`}>{item.video.title}</Link>
                <Link to={`/channel/${item.video.owner.username}`} className="muted">
                  {channelName(item.video.owner)}
                </Link>
                <span className="muted">
                  {formatViews(item.video.views_count)} · просмотрено {formatDate(item.watched_at)}
                </span>
                {item.position_seconds ? (
                  <span className="history-position">
                    <ClockIcon size={13} /> остановились на {formatDuration(item.position_seconds)}
                  </span>
                ) : null}
              </div>
              <button
                type="button"
                className="icon-button danger"
                onClick={() => remove(item.video.id)}
                title="Удалить из истории"
              >
                <TrashIcon size={18} />
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
