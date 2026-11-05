import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { classNames } from '../utils';
import { useToast } from './Toast';

export default function SubscribeButton({ channel, onChange, className = '' }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { push } = useToast();
  const [busy, setBusy] = useState(false);

  if (!channel || channel.is_owner) return null;

  const toggle = async () => {
    if (!user) {
      navigate('/login', { state: { from: `${location.pathname}${location.search}` } });
      return;
    }
    setBusy(true);
    try {
      const data = channel.is_subscribed
        ? await api.delete(`/channels/${channel.username}/subscribe`)
        : await api.post(`/channels/${channel.username}/subscribe`);
      onChange?.(data);
      push(data.is_subscribed ? 'Вы подписались на канал' : 'Вы отписались от канала');
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      className={classNames('btn', channel.is_subscribed ? 'btn-subscribed' : 'btn-primary', className)}
      onClick={toggle}
      disabled={busy}
    >
      {busy ? '…' : channel.is_subscribed ? 'Вы подписаны' : 'Подписаться'}
    </button>
  );
}
