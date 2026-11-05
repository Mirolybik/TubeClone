import { useState } from 'react';
import { api, uploadThumbnail } from '../api';
import { visibilityLabel } from '../utils';
import Modal from './Modal';
import { useToast } from './Toast';

export default function EditVideoModal({ video, onClose, onSaved }) {
  const { push } = useToast();
  const [title, setTitle] = useState(video.title);
  const [description, setDescription] = useState(video.description || '');
  const [visibility, setVisibility] = useState(video.visibility);
  const [thumbnail, setThumbnail] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      let updated = await api.patch(`/videos/${video.id}`, {
        title: title.trim(),
        description,
        visibility,
      });
      if (thumbnail) {
        updated = await uploadThumbnail(video.id, thumbnail);
      }
      push('Видео обновлено');
      onSaved?.(updated);
      onClose();
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Редактировать видео"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Отмена
          </button>
          <button type="submit" form="edit-video-form" className="btn btn-primary" disabled={busy || !title.trim()}>
            {busy ? 'Сохранение…' : 'Сохранить'}
          </button>
        </>
      }
    >
      <form id="edit-video-form" className="form" onSubmit={submit}>
        <label className="field">
          <span>Название</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required />
        </label>
        <label className="field">
          <span>Описание</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={5}
            maxLength={10000}
          />
        </label>
        <label className="field">
          <span>Доступ</span>
          <select value={visibility} onChange={(event) => setVisibility(event.target.value)}>
            {['public', 'unlisted', 'private'].map((value) => (
              <option key={value} value={value}>
                {visibilityLabel(value)}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Новое превью (необязательно)</span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(event) => setThumbnail(event.target.files?.[0] || null)}
          />
        </label>
      </form>
    </Modal>
  );
}
