import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { qs } from '../utils';
import Pager from '../components/Pager';
import VideoCard from '../components/VideoCard';
import { SearchIcon } from '../icons';

export default function SearchPage() {
  const [params] = useSearchParams();
  const query = params.get('q') || '';
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setPage(1);
  }, [query]);

  useEffect(() => {
    if (!query.trim()) {
      setData(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError('');
    api
      .get(`/search${qs({ q: query, page, page_size: 20 })}`)
      .then((result) => active && setData(result))
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [query, page]);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Поиск</h1>
          <p className="page-subtitle">
            {query ? (
              <>
                Результаты по запросу <strong>«{query}»</strong>
                {data ? ` — ${data.total}` : ''}
              </>
            ) : (
              'Введите название видео в строке поиска сверху'
            )}
          </p>
        </div>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading ? <div className="page-loader"><span className="spinner" /> Ищем видео…</div> : null}

      {!query ? (
        <div className="empty-state">
          <SearchIcon size={42} />
          <h2>Что будем смотреть?</h2>
          <p>Поиск работает по названию видео.</p>
        </div>
      ) : null}

      {!loading && data && !data.items.length ? (
        <div className="empty-state">
          <SearchIcon size={42} />
          <h2>Ничего не найдено</h2>
          <p>Попробуйте изменить запрос.</p>
        </div>
      ) : null}

      {data && data.items.length ? (
        <>
          <div className="video-list">
            {data.items.map((video) => (
              <VideoCard key={video.id} video={video} variant="row" />
            ))}
          </div>
          <Pager page={data.page} pages={data.pages} onChange={setPage} />
        </>
      ) : null}
    </div>
  );
}
