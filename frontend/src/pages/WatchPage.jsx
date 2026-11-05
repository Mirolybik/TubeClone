import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import {
  channelName,
  formatDate,
  formatDuration,
  formatSubscribers,
  formatViews,
  statusLabel,
  visibilityLabel,
} from '../utils';
import {
  ArrowLeftIcon,
  EditIcon,
  FlagIcon,
  LinkIcon,
  ListIcon,
  LockIcon,
  PlayIcon,
  SettingsIcon,
  TrashIcon,
} from '../icons';
import AccessManager from '../components/AccessManager';
import AddToPlaylistModal from '../components/AddToPlaylistModal';
import Avatar from '../components/Avatar';
import Comments from '../components/Comments';
import EditVideoModal from '../components/EditVideoModal';
import LikeBar from '../components/LikeBar';
import ReportModal from '../components/ReportModal';
import SubscribeButton from '../components/SubscribeButton';
import { useToast } from '../components/Toast';

function RelatedItem({ video }) {
  return (
    <Link className="related-item" to={`/watch/${video.id}`}>
      <div className="related-thumb">
        <img src={video.thumbnail_url} alt={video.title} loading="lazy" />
        {video.duration_seconds ? <span className="duration-badge">{formatDuration(video.duration_seconds)}</span> : null}
      </div>
      <div className="related-info">
        <h4>{video.title}</h4>
        <p>{channelName(video.owner)}</p>
        <p>
          {formatViews(video.views_count)} · {formatDate(video.created_at)}
        </p>
      </div>
    </Link>
  );
}

export default function WatchPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [channel, setChannel] = useState(null);
  const [related, setRelated] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [accessOpen, setAccessOpen] = useState(false);
  const [playlistOpen, setPlaylistOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [quality, setQuality] = useState(null);
  const [qualityOpen, setQualityOpen] = useState(false);
  const viewedRef = useRef(false);
  const videoRef = useRef(null);
  const pendingPlaybackRef = useRef(null);

  useEffect(() => {
    let active = true;
    viewedRef.current = false;
    pendingPlaybackRef.current = null;
    setLoading(true);
    setError('');
    setVideo(null);
    setChannel(null);
    setRelated([]);
    setQuality(null);
    setQualityOpen(false);
    window.scrollTo({ top: 0 });

    api
      .get(`/videos/${id}`)
      .then(async (result) => {
        if (!active) return;
        setVideo(result);
        const [channelData, relatedData] = await Promise.all([
          api.get(`/channels/${result.owner.username}`).catch(() => null),
          api.get(`/videos/${id}/related`).catch(() => []),
        ]);
        if (!active) return;
        setChannel(channelData);
        setRelated(relatedData);
      })
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    if (!video || viewedRef.current) return;
    viewedRef.current = true;
    api
      .post(`/videos/${video.id}/view`, { position_seconds: 0 })
      .then((data) => setVideo((current) => (current ? { ...current, views_count: data.views_count } : current)))
      .catch(() => {});
  }, [video?.id]);

  useEffect(() => {
    if (!qualityOpen) return undefined;
    const close = () => setQualityOpen(false);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [qualityOpen]);

  const deleteVideo = async () => {
    if (!window.confirm('Удалить видео без возможности восстановления?')) return;
    try {
      await api.delete(`/videos/${video.id}`);
      push('Видео удалено');
      navigate(`/channel/${video.owner.username}`);
    } catch (requestError) {
      push(requestError.message, 'error');
    }
  };

  if (loading) {
    return (
      <div className="watch-layout">
        <div>
          <div className="skeleton skeleton-player" />
          <div className="skeleton skeleton-line wide" style={{ marginTop: 18 }} />
          <div className="skeleton skeleton-line" />
        </div>
        <div className="watch-sidebar">
          {Array.from({ length: 4 }).map((_, index) => (
            <div className="skeleton skeleton-related" key={index} />
          ))}
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="empty-state">
        {error.includes('доступ') ? <LockIcon size={48} /> : <PlayIcon size={48} />}
        <h2>{error.includes('доступ') ? 'Видео недоступно' : 'Не удалось открыть видео'}</h2>
        <p>{error || 'Видео не найдено'}</p>
        <Link className="btn btn-primary" to="/">
          На главную
        </Link>
      </div>
    );
  }

  const ownerChannel = channel || {
    ...video.owner,
    subscribers_count: 0,
    is_subscribed: video.is_subscribed,
    is_owner: video.is_owner,
  };

  const qualities = video.qualities?.length
    ? video.qualities
    : [{ quality: 'original', label: 'Оригинал', stream_url: video.stream_url }];
  const currentQuality = qualities.find((item) => item.quality === quality) || qualities[0];
  const hasQualityChoice = qualities.length > 1;

  const changeQuality = (next) => {
    const player = videoRef.current;
    setQualityOpen(false);
    if (!player || next.quality === currentQuality.quality) return;
    pendingPlaybackRef.current = {
      time: player.currentTime,
      playing: !player.paused,
    };
    setQuality(next.quality);
  };

  const handleLoadedMetadata = () => {
    const player = videoRef.current;
    const pending = pendingPlaybackRef.current;
    if (!player || !pending) return;
    pendingPlaybackRef.current = null;
    player.currentTime = pending.time;
    if (pending.playing) {
      player.play().catch(() => {});
    }
  };

  return (
    <div className="page watch-page">
      <button type="button" className="back-link" onClick={() => navigate(-1)}>
        <ArrowLeftIcon size={16} /> Назад
      </button>

      <div className="watch-layout">
        <div className="watch-main">
          <div className="player-wrap">
            <video
              key={video.id}
              ref={videoRef}
              className="player"
              controls
              playsInline
              preload="metadata"
              poster={video.thumbnail_url}
              src={currentQuality.stream_url}
              onLoadedMetadata={handleLoadedMetadata}
            />
            {hasQualityChoice ? (
              <div className="quality-picker">
                <button
                  type="button"
                  className="quality-button"
                  aria-expanded={qualityOpen}
                  aria-label="Выбрать качество видео"
                  onClick={() => setQualityOpen((value) => !value)}
                >
                  <SettingsIcon size={15} />
                  {currentQuality.label}
                </button>
                {qualityOpen ? (
                  <div className="quality-menu">
                    <div className="quality-menu-head">Качество</div>
                    {qualities.map((item) => (
                      <button
                        key={item.quality}
                        type="button"
                        className={`quality-option ${
                          item.quality === currentQuality.quality ? 'active' : ''
                        }`}
                        onClick={() => changeQuality(item)}
                      >
                        <span>{item.label}</span>
                        {item.height ? <small>{item.width}×{item.height}</small> : null}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          {video.status === 'hidden' ? (
            <div className="alert alert-error">
              Видео скрыто модератором. Оно видно только владельцу и команде модерации.
            </div>
          ) : null}
          {video.visibility === 'private' ? (
            <div className="alert alert-warning">
              <LockIcon size={17} /> Приватное видео: доступ есть у владельца и приглашённых зрителей.
            </div>
          ) : null}
          {video.visibility === 'unlisted' ? (
            <div className="alert alert-info">
              <LinkIcon size={17} /> Видео доступно по прямой ссылке и не показывается в лентах.
            </div>
          ) : null}

          <h1 className="watch-title">{video.title}</h1>
          <div className="watch-meta">
            <span>{formatViews(video.views_count)}</span>
            <span className="dot" />
            <span>{formatDate(video.created_at)}</span>
            <span className="dot" />
            <span className={`badge badge-${video.visibility}`}>{visibilityLabel(video.visibility)}</span>
            {video.status === 'hidden' ? <span className="badge badge-danger">{statusLabel(video.status)}</span> : null}
          </div>

          <div className="watch-actions">
            <div className="watch-channel">
              <Link to={`/channel/${ownerChannel.username}`}>
                <Avatar user={ownerChannel} size={44} />
              </Link>
              <div className="watch-channel-info">
                <Link to={`/channel/${ownerChannel.username}`}>{channelName(ownerChannel)}</Link>
                <span>{formatSubscribers(ownerChannel.subscribers_count)}</span>
              </div>
              <SubscribeButton channel={ownerChannel} onChange={setChannel} />
            </div>

            <div className="action-row">
              <LikeBar video={video} onChange={(data) => setVideo((current) => ({ ...current, ...data }))} />
              {user ? (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPlaylistOpen(true)}>
                  <ListIcon size={17} /> В плейлист
                </button>
              ) : null}
              {user && !video.is_owner ? (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setReportOpen(true)}>
                  <FlagIcon size={17} /> Жалоба
                </button>
              ) : null}
              {video.can_manage ? (
                <>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditOpen(true)}>
                    <EditIcon size={17} /> Изменить
                  </button>
                  {video.visibility === 'private' ? (
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAccessOpen(true)}>
                      <LockIcon size={17} /> Доступ ({video.access_count})
                    </button>
                  ) : null}
                  <button type="button" className="btn btn-ghost btn-sm danger" onClick={deleteVideo}>
                    <TrashIcon size={17} /> Удалить
                  </button>
                </>
              ) : null}
            </div>
          </div>

          <div className={`watch-description ${descriptionOpen ? 'open' : ''}`}>
            <div className="description-meta">
              {formatViews(video.views_count)} · {formatDate(video.created_at)}
              {video.duration_seconds ? ` · ${formatDuration(video.duration_seconds)}` : ''}
            </div>
            <p>{video.description || 'Описание не добавлено.'}</p>
            {video.description && video.description.length > 180 ? (
              <button type="button" className="text-button" onClick={() => setDescriptionOpen((value) => !value)}>
                {descriptionOpen ? 'Свернуть' : 'Ещё'}
              </button>
            ) : null}
          </div>

          <Comments videoId={video.id} />
        </div>

        <aside className="watch-sidebar">
          <h2 className="sidebar-heading">Похожие видео</h2>
          {related.length ? (
            related.map((item) => <RelatedItem key={item.id} video={item} />)
          ) : (
            <p className="muted">Похожих видео пока нет.</p>
          )}
        </aside>
      </div>

      {editOpen ? (
        <EditVideoModal
          video={video}
          onClose={() => setEditOpen(false)}
          onSaved={(updated) => setVideo(updated)}
        />
      ) : null}
      {accessOpen ? (
        <AccessManager
          video={video}
          onClose={() => setAccessOpen(false)}
          onChanged={(count) => setVideo((current) => ({ ...current, access_count: count }))}
        />
      ) : null}
      {playlistOpen ? <AddToPlaylistModal videoId={video.id} onClose={() => setPlaylistOpen(false)} /> : null}
      {reportOpen ? <ReportModal video={video} onClose={() => setReportOpen(false)} /> : null}
    </div>
  );
}
