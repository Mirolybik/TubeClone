import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { channelName, formatDate } from '../utils';
import { CloseIcon, TrashIcon } from '../icons';
import Avatar from './Avatar';
import { useToast } from './Toast';

function CommentNode({ comment, repliesByParent, onReply, onDelete, depth = 0 }) {
  const replies = repliesByParent.get(comment.id) || [];
  return (
    <div className="comment-node" style={{ marginLeft: depth ? Math.min(depth, 2) * 34 : 0 }}>
      <div className="comment-avatar">
        <Avatar user={comment.user} size={38} />
      </div>
      <div className="comment-content">
        <div className="comment-head">
          <Link to={`/channel/${comment.user.username}`} className="comment-author">
            {channelName(comment.user)}
          </Link>
          <span className="comment-date">{formatDate(comment.created_at)}</span>
        </div>
        <p className="comment-text">{comment.text}</p>
        <div className="comment-actions">
          <button type="button" className="text-button" onClick={() => onReply(comment)}>
            Ответить
          </button>
          {comment.can_delete ? (
            <button type="button" className="text-button danger" onClick={() => onDelete(comment)}>
              <TrashIcon size={14} /> Удалить
            </button>
          ) : null}
        </div>
        {replies.length ? (
          <div className="comment-replies">
            {replies.map((reply) => (
              <CommentNode
                key={reply.id}
                comment={reply}
                repliesByParent={repliesByParent}
                onReply={onReply}
                onDelete={onDelete}
                depth={depth + 1}
              />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function Comments({ videoId }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { push } = useToast();
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [text, setText] = useState('');
  const [replyTo, setReplyTo] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get(`/videos/${videoId}/comments`);
      setComments(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    load();
  }, [load]);

  const repliesByParent = useMemo(() => {
    const map = new Map();
    comments.forEach((comment) => {
      if (comment.parent_id) {
        if (!map.has(comment.parent_id)) map.set(comment.parent_id, []);
        map.get(comment.parent_id).push(comment);
      }
    });
    return map;
  }, [comments]);

  const roots = useMemo(() => comments.filter((comment) => !comment.parent_id), [comments]);

  const submit = async (event) => {
    event.preventDefault();
    if (!text.trim()) return;
    if (!user) {
      navigate('/login', { state: { from: `${location.pathname}${location.search}` } });
      return;
    }
    setBusy(true);
    try {
      await api.post(`/videos/${videoId}/comments`, {
        text: text.trim(),
        parent_id: replyTo?.id || null,
      });
      setText('');
      setReplyTo(null);
      push('Комментарий добавлен');
      await load();
    } catch (requestError) {
      push(requestError.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (comment) => {
    if (!window.confirm('Удалить комментарий?')) return;
    try {
      await api.delete(`/comments/${comment.id}`);
      push('Комментарий удалён');
      await load();
    } catch (requestError) {
      push(requestError.message, 'error');
    }
  };

  return (
    <section className="comments-section">
      <div className="section-heading">
        <h2>Комментарии</h2>
        <span className="muted">{comments.length}</span>
      </div>

      {user ? (
        <form className="comment-form" onSubmit={submit}>
          <Avatar user={user} size={40} />
          <div className="comment-form-body">
            {replyTo ? (
              <div className="replying-to">
                Ответ на комментарий {channelName(replyTo.user)}
                <button type="button" className="icon-button small" onClick={() => setReplyTo(null)}>
                  <CloseIcon size={14} />
                </button>
              </div>
            ) : null}
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Напишите комментарий…"
              rows={3}
              maxLength={3000}
            />
            <div className="comment-form-actions">
              <span className="muted small-text">{text.length}/3000</span>
              <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !text.trim()}>
                {busy ? 'Отправка…' : 'Отправить'}
              </button>
            </div>
          </div>
        </form>
      ) : (
        <div className="comments-login">
          <p>Войдите, чтобы оставить комментарий.</p>
          <Link
            className="btn btn-primary btn-sm"
            to="/login"
            state={{ from: `${location.pathname}${location.search}` }}
          >
            Войти
          </Link>
        </div>
      )}

      {loading ? <div className="page-loader small"><span className="spinner" /> Загрузка комментариев…</div> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {!loading && !error && !roots.length ? <p className="muted">Комментариев пока нет.</p> : null}

      <div className="comments-list">
        {roots.map((comment) => (
          <CommentNode
            key={comment.id}
            comment={comment}
            repliesByParent={repliesByParent}
            onReply={(target) => {
              setReplyTo(target);
              document.querySelector('.comment-form textarea')?.focus();
            }}
            onDelete={remove}
          />
        ))}
      </div>
    </section>
  );
}
