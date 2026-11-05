import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import { channelName, formatDate, roleLabel } from '../utils';
import { CloseIcon, LockIcon, PlusIcon } from '../icons';
import Avatar from './Avatar';
import Modal from './Modal';
import { useToast } from './Toast';

export default function AccessManager({ video, onClose, onChanged }) {
  const { push } = useToast();
  const [users, setUsers] = useState([]);
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get(`/videos/${video.id}/access`);
      setUsers(data.users);
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [video.id, push]);

  useEffect(() => {
    load();
  }, [load]);

  const add = async (event) => {
    event.preventDefault();
    if (!username.trim()) return;
    setBusy(true);
    try {
      const data = await api.post(`/videos/${video.id}/access`, { username: username.trim() });
      setUsers(data.users);
      setUsername('');
      onChanged?.(data.users.length);
      push('Доступ выдан');
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (user) => {
    try {
      const data = await api.delete(`/videos/${video.id}/access/${user.id}`);
      setUsers(data.users);
      onChanged?.(data.users.length);
      push('Доступ отозван');
    } catch (error) {
      push(error.message, 'error');
    }
  };

  return (
    <Modal
      title="Доступ к приватному видео"
      onClose={onClose}
      footer={
        <button type="button" className="btn btn-primary" onClick={onClose}>
          Готово
        </button>
      }
    >
      <div className="access-note">
        <LockIcon size={18} />
        <p>
          Видео видят владелец, администраторы и модераторы, а также пользователи из списка ниже. Добавляйте
          зрителей по username.
        </p>
      </div>

      <form className="inline-form" onSubmit={add}>
        <input
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          placeholder="username пользователя"
          maxLength={50}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !username.trim()}>
          <PlusIcon size={16} /> Разрешить
        </button>
      </form>

      {loading ? <p className="muted">Загрузка…</p> : null}
      {!loading && !users.length ? <p className="muted">Список доступа пуст.</p> : null}

      <div className="access-list">
        {users.map((user) => (
          <div className="access-row" key={user.id}>
            <Avatar user={user} size={38} />
            <div className="access-row-info">
              <strong>{channelName(user)}</strong>
              <span>
                @{user.username} · {roleLabel(user.role)} · с {formatDate(user.created_at)}
              </span>
            </div>
            <button type="button" className="icon-button danger" onClick={() => remove(user)} title="Отозвать доступ">
              <CloseIcon size={18} />
            </button>
          </div>
        ))}
      </div>
    </Modal>
  );
}
