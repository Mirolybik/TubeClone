import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import {
  channelName,
  formatDate,
  formatViews,
  reportCategoryLabel,
  reportStatusLabel,
} from '../utils';
import { EyeOffIcon, FlagIcon, ShieldIcon } from '../icons';
import Modal from '../components/Modal';
import Pager from '../components/Pager';
import { useToast } from '../components/Toast';

function ResolveModal({ report, action, onClose, onDone }) {
  const { push } = useToast();
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      await api.post(`/moderation/reports/${report.id}/resolve`, { action, note: note.trim() || null });
      push(action === 'hide' ? 'Видео скрыто, жалоба решена' : 'Жалоба отклонена');
      onDone();
      onClose();
    } catch (error) {
      push(error.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title={action === 'hide' ? 'Скрыть видео по жалобе' : 'Отклонить жалобу'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Отмена
          </button>
          <button
            type="submit"
            form="resolve-report-form"
            className={`btn ${action === 'hide' ? 'btn-danger' : 'btn-primary'}`}
            disabled={busy}
          >
            {busy ? 'Сохранение…' : action === 'hide' ? 'Скрыть видео' : 'Отклонить'}
          </button>
        </>
      }
    >
      <form id="resolve-report-form" className="form" onSubmit={submit}>
        <p className="muted">
          Видео: <strong>{report.video.title}</strong>
        </p>
        <p className="muted">
          Жалоба от {channelName(report.reporter)}: {reportCategoryLabel(report.category)}
        </p>
        <label className="field">
          <span>Комментарий модератора (необязательно)</span>
          <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={3} maxLength={2000} />
        </label>
        {action === 'hide' ? (
          <p className="hint">Видео исчезнет из лент и станет недоступно зрителям. Владелец и модераторы его увидят.</p>
        ) : null}
      </form>
    </Modal>
  );
}

export default function ModerationPage() {
  const { push } = useToast();
  const [tab, setTab] = useState('reports');
  const [status, setStatus] = useState('open');
  const [reports, setReports] = useState(null);
  const [reportPage, setReportPage] = useState(1);
  const [hiddenVideos, setHiddenVideos] = useState(null);
  const [videoPage, setVideoPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [resolving, setResolving] = useState(null);

  const loadReports = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get(`/moderation/reports?status=${status}&page=${reportPage}&page_size=20`);
      setReports(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const loadVideos = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get(`/moderation/videos?status=hidden&page=${videoPage}&page_size=20`);
      setHiddenVideos(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tab === 'reports') loadReports();
    else loadVideos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, status, reportPage, videoPage]);

  const restore = async (video) => {
    try {
      await api.post(`/moderation/videos/${video.id}/unhide`);
      push('Видео восстановлено');
      loadVideos();
    } catch (requestError) {
      push(requestError.message, 'error');
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Модерация</h1>
          <p className="page-subtitle">Очередь жалоб и скрытые видео</p>
        </div>
        <span className="badge badge-warning"><ShieldIcon size={14} /> Панель модератора</span>
      </div>

      <div className="tabs">
        <button type="button" className={tab === 'reports' ? 'active' : ''} onClick={() => setTab('reports')}>
          <FlagIcon size={18} /> Жалобы {reports ? `(${reports.total})` : ''}
        </button>
        <button type="button" className={tab === 'videos' ? 'active' : ''} onClick={() => setTab('videos')}>
          <EyeOffIcon size={18} /> Скрытые видео {hiddenVideos ? `(${hiddenVideos.total})` : ''}
        </button>
      </div>

      {tab === 'reports' ? (
        <>
          <div className="segmented moderation-filter">
            {[
              ['open', 'Открытые'],
              ['resolved', 'Решённые'],
              ['dismissed', 'Отклонённые'],
              ['all', 'Все'],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={status === value ? 'active' : ''}
                onClick={() => {
                  setStatus(value);
                  setReportPage(1);
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {error ? <div className="alert alert-error">{error}</div> : null}
          {loading ? <div className="page-loader"><span className="spinner" /> Загрузка жалоб…</div> : null}
          {!loading && reports && !reports.items.length ? (
            <div className="empty-state compact">
              <ShieldIcon size={38} />
              <h2>Жалоб нет</h2>
              <p>Очередь пуста — отличная работа.</p>
            </div>
          ) : null}

          {reports && reports.items.length ? (
            <>
              <div className="report-list">
                {reports.items.map((report) => (
                  <article className="report-card" key={report.id}>
                    <Link className="report-thumb" to={`/watch/${report.video.id}`}>
                      <img src={report.video.thumbnail_url} alt={report.video.title} loading="lazy" />
                    </Link>
                    <div className="report-content">
                      <div className="report-top">
                        <Link to={`/watch/${report.video.id}`} className="report-title">
                          {report.video.title}
                        </Link>
                        <span className={`badge ${report.status === 'open' ? 'badge-warning' : 'badge-muted'}`}>
                          {reportStatusLabel(report.status)}
                        </span>
                      </div>
                      <p className="muted">
                        {channelName(report.video.owner)} · {formatViews(report.video.views_count)} · жалоба от{' '}
                        {channelName(report.reporter)} · {formatDate(report.created_at)}
                      </p>
                      <p className="report-category">{reportCategoryLabel(report.category)}</p>
                      {report.reason ? <p className="report-reason">{report.reason}</p> : null}
                      {report.status !== 'open' && report.resolution_note ? (
                        <p className="hint">Решение: {report.resolution_note}</p>
                      ) : null}
                      {report.status === 'open' ? (
                        <div className="report-actions">
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            onClick={() => setResolving({ report, action: 'hide' })}
                          >
                            <EyeOffIcon size={16} /> Скрыть видео
                          </button>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => setResolving({ report, action: 'dismiss' })}
                          >
                            Отклонить жалобу
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
              <Pager page={reports.page} pages={reports.pages} onChange={setReportPage} />
            </>
          ) : null}
        </>
      ) : (
        <>
          {error ? <div className="alert alert-error">{error}</div> : null}
          {loading ? <div className="page-loader"><span className="spinner" /> Загрузка видео…</div> : null}
          {!loading && hiddenVideos && !hiddenVideos.items.length ? (
            <div className="empty-state compact">
              <EyeOffIcon size={38} />
              <h2>Скрытых видео нет</h2>
            </div>
          ) : null}
          {hiddenVideos && hiddenVideos.items.length ? (
            <>
              <div className="history-list">
                {hiddenVideos.items.map((video) => (
                  <div className="history-row" key={video.id}>
                    <Link className="history-thumb" to={`/watch/${video.id}`}>
                      <img src={video.thumbnail_url} alt={video.title} loading="lazy" />
                    </Link>
                    <div className="history-info">
                      <Link to={`/watch/${video.id}`}>{video.title}</Link>
                      <Link to={`/channel/${video.owner.username}`} className="muted">
                        {channelName(video.owner)}
                      </Link>
                      <span className="muted">
                        {formatViews(video.views_count)} · скрыто модератором
                      </span>
                    </div>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => restore(video)}>
                      Восстановить
                    </button>
                  </div>
                ))}
              </div>
              <Pager page={hiddenVideos.page} pages={hiddenVideos.pages} onChange={setVideoPage} />
            </>
          ) : null}
        </>
      )}

      {resolving ? (
        <ResolveModal
          report={resolving.report}
          action={resolving.action}
          onClose={() => setResolving(null)}
          onDone={() => {
            loadReports();
            if (resolving.action === 'hide') loadVideos();
          }}
        />
      ) : null}
    </div>
  );
}
