import { useState } from 'react';
import { api } from '../api';
import { reportCategoryLabel } from '../utils';
import Modal from './Modal';
import { useToast } from './Toast';

const CATEGORIES = ['spam', 'inappropriate', 'copyright', 'other'];

export default function ReportModal({ video, onClose }) {
  const { push } = useToast();
  const [category, setCategory] = useState('inappropriate');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      await api.post(`/videos/${video.id}/report`, { category, reason: reason.trim() || null });
      push('Жалоба отправлена модераторам');
      onClose();
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Пожаловаться на видео"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Отмена
          </button>
          <button type="submit" form="report-form" className="btn btn-danger" disabled={busy}>
            {busy ? 'Отправка…' : 'Отправить жалобу'}
          </button>
        </>
      }
    >
      <form id="report-form" className="form" onSubmit={submit}>
        <p className="muted">
          Жалоба попадёт в очередь модераторов. Видео: <strong>{video.title}</strong>
        </p>
        <label className="field">
          <span>Причина</span>
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            {CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {reportCategoryLabel(value)}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Комментарий (необязательно)</span>
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={4}
            maxLength={2000}
            placeholder="Опишите проблему"
          />
        </label>
      </form>
    </Modal>
  );
}
