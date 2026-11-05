import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { channelName, qs } from '../utils';
import Pager from '../components/Pager';
import VideoCard from '../components/VideoCard';
import Avatar from '../components/Avatar';
import { SubscriptionsIcon } from '../icons';

export default function SubscriptionsPage() {
  const [data, setData] = useState(null);
  const [channels, setChannels] = useState([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/me/subscriptions').then(setChannels).catch(() => setChannels([]));
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api
      .get(`/feed/subscriptions${qs({ page, page_size: 24 })}`)
      .then((result) => active && setData(result))
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [page]);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Подписки</h1>
          <p className="page-subtitle">Новые видео каналов, на которые вы подписаны</p>
        </div>
      </div>

      {channels.length ? (
        <div className="channel-strip">
          {channels.map((channel) => (
            <Link className="channel-chip" to={`/channel/${channel.username}`} key={channel.id}>
              <Avatar user={channel} size={42} />
              <span>
                <strong>{channelName(channel)}</strong>
                <small>{channel.subscribers_count} подписчиков</small>
              </span>
            </Link>
          ))}
        </div>
      ) : null}

      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading && !data ? <div className="page-loader"><span className="spinner" /> Загрузка ленты…</div> : null}

      {!loading && data && !data.items.length ? (
        <div className="empty-state">
          <SubscriptionsIcon size={48} />
          <h2>Пока пусто</h2>
          <p>Подпишитесь на каналы, чтобы видеть их новые видео здесь.</p>
          <Link className="btn btn-primary" to="/">
            Найти каналы
          </Link>
        </div>
      ) : null}

      {data && data.items.length ? (
        <>
          <div className="video-grid">
            {data.items.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
          <Pager page={data.page} pages={data.pages} onChange={setPage} />
        </>
      ) : null}
    </div>
  );
}
