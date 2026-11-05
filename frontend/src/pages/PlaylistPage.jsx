import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import {
  channelName,
  formatDate,
  formatDuration,
  formatViews,
  visibilityLabel,
} from '../utils';
import { EditIcon, LinkIcon, ListIcon, LockIcon, PlayIcon, TrashIcon } from '../icons';
import Avatar from '../components/Avatar';
import Modal from '../components/Modal';
import { useToast } from '../components/Toast';

function EditPlaylistModal({ playlist, onClose, onSaved }) {
  const { push } = useToast();
  const [title, setTitle] = useState(playlist.title);
  const [description, setDescription] = useState(playlist.description || '');
  const [visibility, setVisibility] = useState(playlist.visibility);
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const updated = await api.patch(`/playlists/${playlist.id}`, { title, description, visibility });
      push('Плейлист обновлён');
      onSaved(updated);
      onClose();
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Редактировать плейлист"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Отмена
          </button>
          <button type="submit" form="edit-playlist-form" className="btn btn-primary" disabled={busy || !title.trim()}>
            {busy ? 'Сохранение…' : 'Сохранить'}
          </button>
        </>
      }
    >
      <form id="edit-playlist-form" className="form" onSubmit={submit}>
        <label className="field">
          <span>Название</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required />
        </label>
        <label className="field">
          <span>Описание</span>
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={4} />
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

export default function PlaylistPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { push } = useToast();
  const [playlist, setPlaylist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editOpen, setEditOpen] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get(`/playlists/${id}`);
      setPlaylist(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const removeItem = async (item) => {
    if (!window.confirm('Удалить видео из плейлиста?')) return;
    try {
      const data = await api.delete(`/playlists/${playlist.id}/items/${item.id}`);
      setPlaylist(data);
      push('Видео удалено из плейлиста');
    } catch (requestError) {
      push(requestError.message, 'error');
    }
  };

  const deletePlaylist = async () => {
    if (!window.confirm('Удалить плейлист? Видео останутся на канале.')) return;
    try {
      await api.delete(`/playlists/${playlist.id}`);
      push('Плейлист удалён');
      navigate(`/channel/${playlist.owner.username}`);
    } catch (requestError) {
      push(requestError.message, 'error');
    }
  };

  if (loading) {
    return <div className="page-loader"><span className="spinner" /> Загрузка плейлиста…</div>;
  }

  if (error || !playlist) {
    return (
      <div className="empty-state">
        {error.includes('приват') ? <LockIcon size={48} /> : <ListIcon size={48} />}
        <h2>Плейлист недоступен</h2>
        <p>{error || 'Плейлист не найден'}</p>
        <Link className="btn btn-primary" to="/">
          На главную
        </Link>
      </div>
    );
  }

  const totalDuration = playlist.items.reduce((sum, item) => sum + (item.video.duration_seconds || 0), 0);
  const cover = playlist.items[0]?.video.thumbnail_url || playlist.cover_url;

  return (
    <div className="page playlist-page">
      <div className="playlist-hero">
        <div className="playlist-hero-cover">
          {cover ? <img src={cover} alt={playlist.title} /> : <ListIcon size={54} />}
          <span className="playlist-count">{playlist.items_count} видео</span>
        </div>
        <div className="playlist-hero-info">
          <span className="badge">
            {playlist.visibility === 'private' ? <LockIcon size={12} /> : null}
            {visibilityLabel(playlist.visibility)}
          </span>
          <h1>{playlist.title}</h1>
          <Link className="playlist-owner" to={`/channel/${playlist.owner.username}`}>
            <Avatar user={playlist.owner} size={28} /> {channelName(playlist.owner)}
          </Link>
          <p className="muted">
            {playlist.items_count} видео · {formatDuration(totalDuration)} · обновлён {formatDate(playlist.updated_at)}
          </p>
          {playlist.description ? <p className="playlist-description">{playlist.description}</p> : null}
          <div className="playlist-actions">
            {playlist.items.length ? (
              <Link className="btn btn-primary" to={`/watch/${playlist.items[0].video.id}`}>
                <PlayIcon size={17} /> Смотреть
              </Link>
            ) : null}
            {playlist.is_owner ? (
              <>
                <button type="button" className="btn btn-ghost" onClick={() => setEditOpen(true)}>
                  <EditIcon size={17} /> Изменить
                </button>
                <button type="button" className="btn btn-ghost danger" onClick={deletePlaylist}>
                  <TrashIcon size={17} /> Удалить
                </button>
              </>
            ) : null}
          </div>
        </div>
      </div>

      {!playlist.items.length ? (
        <div className="empty-state compact">
          <ListIcon size={38} />
          <h2>Плейлист пуст</h2>
          <p>Добавляйте видео со страницы просмотра кнопкой «В плейлист».</p>
        </div>
      ) : (
        <div className="playlist-items">
          {playlist.items.map((item, index) => (
            <div className="playlist-item" key={item.id}>
              <span className="playlist-index">{index + 1}</span>
              <Link className="playlist-item-thumb" to={`/watch/${item.video.id}`}>
                <img src={item.video.thumbnail_url} alt={item.video.title} loading="lazy" />
                {item.video.duration_seconds ? (
                  <span className="duration-badge">{formatDuration(item.video.duration_seconds)}</span>
                ) : null}
              </Link>
              <div className="playlist-item-info">
                <Link to={`/watch/${item.video.id}`}>{item.video.title}</Link>
                <Link to={`/channel/${item.video.owner.username}`} className="muted">
                  {channelName(item.video.owner)}
                </Link>
                <span className="muted">{formatViews(item.video.views_count)}</span>
              </div>
              {playlist.is_owner ? (
                <button
                  type="button"
                  className="icon-button danger"
                  onClick={() => removeItem(item)}
                  title="Убрать из плейлиста"
                >
                  <TrashIcon size={18} />
                </button>
              ) : (
                <Link className="icon-button" to={`/watch/${item.video.id}`} title="Смотреть">
                  <PlayIcon size={18} />
                </Link>
              )}
            </div>
          ))}
        </div>
      )}

      {playlist.is_owner && playlist.visibility === 'unlisted' ? (
        <p className="hint">
          <LinkIcon size={14} /> Плейлист доступен по ссылке, но не отображается в публичном списке канала.
        </p>
      ) : null}

      {editOpen ? (
        <EditPlaylistModal
          playlist={playlist}
          onClose={() => setEditOpen(false)}
          onSaved={(updated) => setPlaylist((current) => ({ ...current, ...updated }))}
        />
      ) : null}
    </div>
  );
}
