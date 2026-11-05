import { Link } from 'react-router-dom';
import { PlayIcon } from '../icons';

export default function NotFoundPage() {
  return (
    <div className="empty-state">
      <PlayIcon size={52} />
      <h1>404</h1>
      <h2>Страница не найдена</h2>
      <p>Возможно, ссылка устарела или видео было удалено.</p>
      <Link className="btn btn-primary" to="/">
        На главную
      </Link>
    </div>
  );
}
