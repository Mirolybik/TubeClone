import { useState } from 'react';
import { Link } from 'react-router-dom';
import { EyeOffIcon, LockIcon, LinkIcon, PlayIcon } from '../icons';
import { channelName, classNames, formatDate, formatDuration, formatViews, statusLabel, visibilityLabel } from '../utils';
import Avatar from './Avatar';

function Badges({ video }) {
  const badges = [];
  if (video.status === 'hidden') {
    badges.push(
      <span key="hidden" className="badge badge-danger">
        <EyeOffIcon size={12} /> {statusLabel(video.status)}
      </span>,
    );
  }
  if (video.visibility === 'private') {
    badges.push(
      <span key="private" className="badge badge-warning">
        <LockIcon size={12} /> {visibilityLabel(video.visibility)}
      </span>,
    );
  } else if (video.visibility === 'unlisted') {
    badges.push(
      <span key="unlisted" className="badge">
        <LinkIcon size={12} /> {visibilityLabel(video.visibility)}
      </span>,
    );
  }
  if (!badges.length) return null;
  return <div className="video-badges">{badges}</div>;
}

export default function VideoCard({ video, variant = 'grid' }) {
  const [broken, setBroken] = useState(false);
  const isRow = variant === 'row';

  return (
    <article className={classNames('video-card', isRow && 'video-card-row')}>
      <Link className="video-thumb" to={`/watch/${video.id}`} aria-label={video.title}>
        {broken ? (
          <div className="thumb-fallback">
            <PlayIcon size={30} />
            <span>{video.title}</span>
          </div>
        ) : (
          <img
            src={video.thumbnail_url}
            alt={video.title}
            loading="lazy"
            onError={() => setBroken(true)}
          />
        )}
        {video.duration_seconds ? <span className="duration-badge">{formatDuration(video.duration_seconds)}</span> : null}
        <Badges video={video} />
      </Link>

      <div className="video-card-body">
        <Link className="video-title" to={`/watch/${video.id}`}>
          {video.title}
        </Link>
        <div className="video-meta">
          <span>{formatViews(video.views_count)}</span>
          <span className="dot" />
          <span>{formatDate(video.created_at)}</span>
        </div>
        <Link className="video-channel" to={`/channel/${video.owner.username}`}>
          <Avatar user={video.owner} size={28} />
          <span>{channelName(video.owner)}</span>
        </Link>
        {isRow ? <p className="video-description">{video.description}</p> : null}
      </div>
    </article>
  );
}
