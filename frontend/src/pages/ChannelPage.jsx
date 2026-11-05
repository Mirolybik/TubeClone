import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import { channelName, formatDate, formatSubscribers, formatViews, visibilityLabel } from '../utils';
import { FilmIcon, ListIcon, LockIcon, PlusIcon, UploadIcon } from '../icons';
import Avatar from '../components/Avatar';
import Modal from '../components/Modal';
import Pager from '../components/Pager';
import SubscribeButton from '../components/SubscribeButton';
import { useToast } from '../components/Toast';
import VideoCard from '../components/VideoCard';

function CreatePlaylistModal({ onClose, onCreated }) {
  const { push } = useToast();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState('public');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const created = await api.post('/playlists', { title: title.trim(), description, visibility });
      push('Плейлист создан');
      onCreated(created);
      onClose();
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Новый плейлист"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Отмена
          </button>
          <button type="submit" form="create-playlist-form" className="btn btn-primary" disabled={busy || !title.trim()}>
            {busy ? 'Создание…' : 'Создать'}
          </button>
        </>
      }
    >
      <form id="create-playlist-form" className="form" onSubmit={submit}>
        <label className="field">
          <span>Название</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required />
        </label>
        <label className="field">
          <span>Описание</span>
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} />
        </label>
        <label className="field">
          <span>Видимость</span>
          <select value={visibility} onChange={(event) => setVisibility(event.target.value)}>
            <option value="public">Публичный</option>
            <option value="unlisted">По ссылке</option>
            <option value="private">Приватный</option>
          </select>
        </label>
      </form>
    </Modal>
  );
}

export default function ChannelPage() {
  const { username } = useParams();
  const [channel, setChannel] = useState(null);
  const [videos, setVideos] = useState(null);
  const [playlists, setPlaylists] = useState([]);
  const [tab, setTab] = useState('videos');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [videosLoading, setVideosLoading] = useState(true);
  const [error, setError] = useState('');
  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setPage(1);
    Promise.all([
      api.get(`/channels/${username}`),
      api.get(`/channels/${username}/playlists?page_size=50`),
    ])
      .then(([channelData, playlistData]) => {
        if (!active) return;
        setChannel(channelData);
        setPlaylists(playlistData.items);
      })
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [username]);

  useEffect(() => {
    let active = true;
    setVideosLoading(true);
    api
      .get(`/channels/${username}/videos?page=${page}&page_size=24`)
      .then((data) => active && setVideos(data))
      .catch(() => active && setVideos({ items: [], total: 0, page: 1, pages: 1 }))
      .finally(() => active && setVideosLoading(false));
    return () => {
      active = false;
    };
  }, [username, page]);

  const addPlaylist = useCallback((playlist) => {
    setPlaylists((items) => [playlist, ...items]);
    setTab('playlists');
  }, []);

  if (loading) {
    return (
      <div className="page">
        <div className="skeleton skeleton-banner" />
        <div className="page-loader"><span className="spinner" /> Загрузка канала…</div>
      </div>
    );
  }

  if (error || !channel) {
    return (
      <div className="empty-state">
        <FilmIcon size={48} />
        <h2>Канал не найден</h2>
        <p>{error || 'Проверьте username в адресе.'}</p>
        <Link className="btn btn-primary" to="/">
          На главную
        </Link>
      </div>
    );
  }

  return (
    <div className="page channel-page">
      <div className="channel-banner" />
      <div className="channel-header">
        <Avatar user={channel} size={96} className="channel-avatar" />
        <div className="channel-info">
          <h1>{channelName(channel)}</h1>
          <p className="channel-handle">@{channel.username}</p>
          <p className="channel-stats">
            {formatSubscribers(channel.subscribers_count)} · {channel.videos_count} видео · на сайте с{' '}
            {formatDate(channel.created_at)}
          </p>
          {channel.bio ? <p className="channel-bio">{channel.bio}</p> : null}
        </div>
        <div className="channel-actions">
          <SubscribeButton channel={channel} onChange={setChannel} />
          {channel.is_owner ? (
            <>
              <Link className="btn btn-ghost" to="/upload">
                <UploadIcon size={18} /> Загрузить
              </Link>
              <button type="button" className="btn btn-ghost" onClick={() => setCreateOpen(true)}>
                <PlusIcon size={18} /> Плейлист
              </button>
            </>
          ) : null}
        </div>
      </div>

      <div className="tabs">
        <button type="button" className={tab === 'videos' ? 'active' : ''} onClick={() => setTab('videos')}>
          <FilmIcon size={18} /> Видео
        </button>
        <button type="button" className={tab === 'playlists' ? 'active' : ''} onClick={() => setTab('playlists')}>
          <ListIcon size={18} /> Плейлисты
        </button>
        <button type="button" className={tab === 'about' ? 'active' : ''} onClick={() => setTab('about')}>
          О канале
        </button>
      </div>

      {tab === 'videos' ? (
        <div className="tab-content">
          {videosLoading && !videos ? <div className="page-loader"><span className="spinner" /> Загрузка видео…</div> : null}
          {videos && !videos.items.length ? (
            <div className="empty-state compact">
              <FilmIcon size={38} />
              <h2>Видео пока нет</h2>
              <p>{channel.is_owner ? 'Загрузите первое видео на канал.' : 'Автор ещё не опубликовал видео.'}</p>
              {channel.is_owner ? (
                <Link className="btn btn-primary" to="/upload">
                  Загрузить видео
                </Link>
              ) : null}
            </div>
          ) : null}
          {videos && videos.items.length ? (
            <>
              <div className="video-grid">
                {videos.items.map((video) => (
                  <VideoCard key={video.id} video={video} />
                ))}
              </div>
              <Pager page={videos.page} pages={videos.pages} onChange={setPage} />
            </>
          ) : null}
        </div>
      ) : null}

      {tab === 'playlists' ? (
        <div className="tab-content">
          {!playlists.length ? (
            <div className="empty-state compact">
              <ListIcon size={38} />
              <h2>Плейлистов пока нет</h2>
              {channel.is_owner ? (
                <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
                  Создать плейлист
                </button>
              ) : null}
            </div>
          ) : (
            <div className="playlist-grid">
              {playlists.map((playlist) => (
                <Link className="playlist-card" to={`/playlist/${playlist.id}`} key={playlist.id}>
                  <div className="playlist-cover">
                    {playlist.cover_url ? (
                      <img src={playlist.cover_url} alt={playlist.title} loading="lazy" />
                    ) : (
                      <ListIcon size={36} />
                    )}
                    <span className="playlist-count">{playlist.items_count} видео</span>
                    {playlist.visibility !== 'public' ? (
                      <span className="badge playlist-visibility">
                        {playlist.visibility === 'private' ? <LockIcon size={12} /> : null}
                        {visibilityLabel(playlist.visibility)}
                      </span>
                    ) : null}
                  </div>
                  <h3>{playlist.title}</h3>
                  <p>{formatViews(playlist.items_count)} · обновлён {formatDate(playlist.updated_at)}</p>
                </Link>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {tab === 'about' ? (
        <div className="tab-content about-grid">
          <div className="about-card">
            <h3>Описание</h3>
            <p>{channel.bio || 'Автор пока ничего не рассказал о себе.'}</p>
          </div>
          <div className="about-card">
            <h3>Статистика</h3>
            <dl>
              <div><dt>Подписчики</dt><dd>{formatSubscribers(channel.subscribers_count)}</dd></div>
              <div><dt>Видео</dt><dd>{channel.videos_count}</dd></div>
              <div><dt>Дата регистрации</dt><dd>{formatDate(channel.created_at)}</dd></div>
            </dl>
          </div>
        </div>
      ) : null}

      {createOpen ? <CreatePlaylistModal onClose={() => setCreateOpen(false)} onCreated={addPlaylist} /> : null}
    </div>
  );
}
