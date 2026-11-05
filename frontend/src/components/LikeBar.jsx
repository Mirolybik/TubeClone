import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { formatCount } from '../utils';
import { DislikeIcon, LikeIcon, ShareIcon } from '../icons';
import { useToast } from './Toast';

export default function LikeBar({ video, onChange }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { push } = useToast();
  const [reaction, setReaction] = useState(video.my_reaction || 0);
  const [likes, setLikes] = useState(video.likes_count || 0);
  const [dislikes, setDislikes] = useState(video.dislikes_count || 0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setReaction(video.my_reaction || 0);
    setLikes(video.likes_count || 0);
    setDislikes(video.dislikes_count || 0);
  }, [video.id, video.my_reaction, video.likes_count, video.dislikes_count]);

  const react = async (value) => {
    if (!user) {
      navigate('/login', { state: { from: `${location.pathname}${location.search}` } });
      return;
    }
    if (busy) return;
    setBusy(true);
    const nextValue = reaction === value ? 0 : value;
    try {
      const data = await api.post(`/videos/${video.id}/reaction`, { value: nextValue });
      setReaction(data.my_reaction || 0);
      setLikes(data.likes_count);
      setDislikes(data.dislikes_count);
      onChange?.(data);
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const share = async () => {
    const url = `${window.location.origin}/watch/${video.id}`;
    try {
      if (navigator.share) {
        await navigator.share({ title: video.title, url });
      } else {
        await navigator.clipboard.writeText(url);
        push('Ссылка скопирована');
      }
    } catch {
      push('Не удалось поделиться ссылкой', 'error');
    }
  };

  return (
    <div className="like-bar">
      <div className="like-group">
        <button
          type="button"
          className={`like-button ${reaction === 1 ? 'active' : ''}`}
          onClick={() => react(1)}
          disabled={busy}
          title="Нравится"
        >
          <LikeIcon size={20} />
          <span>{formatCount(likes)}</span>
        </button>
        <span className="like-divider" />
        <button
          type="button"
          className={`like-button ${reaction === -1 ? 'active dislike' : ''}`}
          onClick={() => react(-1)}
          disabled={busy}
          title="Не нравится"
        >
          <DislikeIcon size={20} />
          <span>{formatCount(dislikes)}</span>
        </button>
      </div>
      <button type="button" className="btn btn-ghost btn-sm" onClick={share}>
        <ShareIcon size={18} /> Поделиться
      </button>
    </div>
  );
}
