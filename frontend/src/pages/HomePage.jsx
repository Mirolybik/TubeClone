import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { qs } from '../utils';
import Pager from '../components/Pager';
import VideoCard from '../components/VideoCard';
import { UploadIcon } from '../icons';

function SkeletonGrid() {
  return (
    <div className="video-grid">
      {Array.from({ length: 8 }).map((_, index) => (
        <div className="skeleton-card" key={index}>
          <div className="skeleton skeleton-thumb" />
          <div className="skeleton skeleton-line wide" />
          <div className="skeleton skeleton-line" />
        </div>
      ))}
    </div>
  );
}

export default function HomePage() {
  const [sort, setSort] = useState('new');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api
      .get(`/feed${qs({ sort, page, page_size: 24 })}`)
      .then((result) => active && setData(result))
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [sort, page]);

  const changeSort = (value) => {
    setSort(value);
    setPage(1);
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Главная</h1>
          <p className="page-subtitle">Свежие публичные видео со всего TubeClone</p>
        </div>
        <div className="segmented">
          <button type="button" className={sort === 'new' ? 'active' : ''} onClick={() => changeSort('new')}>
            Новые
          </button>
          <button type="button" className={sort === 'popular' ? 'active' : ''} onClick={() => changeSort('popular')}>
            Популярные
          </button>
        </div>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading && !data ? <SkeletonGrid /> : null}

      {!loading && data && !data.items.length ? (
        <div className="empty-state">
          <UploadIcon size={42} />
          <h2>Пока нет видео</h2>
          <p>Загрузите первое видео — оно появится в ленте.</p>
          <Link className="btn btn-primary" to="/upload">
            Загрузить видео
          </Link>
        </div>
      ) : null}

      {data && data.items.length ? (
        <>
          <div className="video-grid">
            {data.items.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
          <Pager page={data.page} pages={data.pages} onChange={setPage} />
        </>
      ) : null}
    </div>
  );
}
