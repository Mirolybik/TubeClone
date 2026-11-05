import { useEffect, useState } from 'react';
import { api } from '../api';
import Modal from './Modal';
import { useToast } from './Toast';

export default function AddToPlaylistModal({ videoId, onClose }) {
  const { push } = useToast();
  const [playlists, setPlaylists] = useState([]);
  const [selected, setSelected] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .get('/me/playlists')
      .then((data) => {
        if (!active) return;
        setPlaylists(data);
        if (data.length) setSelected(String(data[0].id));
      })
      .catch((error) => push(error.message, 'error'))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [push]);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      let playlistId = selected ? Number(selected) : null;
      if (!playlistId && newTitle.trim()) {
        const created = await api.post('/playlists', {
          title: newTitle.trim(),
          description: '',
          visibility: 'private',
        });
        playlistId = created.id;
      }
      if (!playlistId) {
        push('Выберите плейлист или создайте новый', 'error');
        return;
      }
      await api.post(`/playlists/${playlistId}/items`, { video_id: videoId });
      push('Видео добавлено в плейлист');
      onClose();
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Добавить в плейлист"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Отмена
          </button>
          <button type="submit" form="playlist-picker-form" className="btn btn-primary" disabled={busy}>
            {busy ? 'Добавление…' : 'Добавить'}
          </button>
        </>
      }
    >
      <form id="playlist-picker-form" className="form" onSubmit={submit}>
        {loading ? <p className="muted">Загрузка плейлистов…</p> : null}
        {!loading && playlists.length ? (
          <label className="field">
            <span>Плейлист</span>
            <select value={selected} onChange={(event) => setSelected(event.target.value)}>
              <option value="">— не выбран —</option>
              {playlists.map((playlist) => (
                <option key={playlist.id} value={playlist.id}>
                  {playlist.title} ({playlist.items_count})
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="field">
          <span>{playlists.length ? 'Или создайте новый' : 'Новый плейлист'}</span>
          <input
            value={newTitle}
            onChange={(event) => setNewTitle(event.target.value)}
            placeholder="Название нового плейлиста"
            maxLength={200}
          />
        </label>
        <p className="hint">Новый плейлист создаётся приватным, изменить видимость можно на его странице.</p>
      </form>
    </Modal>
  );
}
