export function channelName(user) {
  if (!user) return 'Канал';
  return user.display_name || user.username || 'Канал';
}

export function initials(name) {
  if (!name) return '?';
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

export function plural(number, one, few, many) {
  const abs = Math.abs(number) % 100;
  const last = abs % 10;
  if (abs > 10 && abs < 20) return many;
  if (last > 1 && last < 5) return few;
  if (last === 1) return one;
  return many;
}

export function formatCount(value) {
  const number = Number(value) || 0;
  return new Intl.NumberFormat('ru-RU', {
    notation: number >= 1000 ? 'compact' : 'standard',
    maximumFractionDigits: 1,
  }).format(number);
}

export function formatViews(value) {
  const number = Number(value) || 0;
  return `${formatCount(number)} ${plural(number, 'просмотр', 'просмотра', 'просмотров')}`;
}

export function formatSubscribers(value) {
  const number = Number(value) || 0;
  return `${formatCount(number)} ${plural(number, 'подписчик', 'подписчика', 'подписчиков')}`;
}

export function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'только что';
  if (minutes < 60) return `${minutes} ${plural(minutes, 'минуту', 'минуты', 'минут')} назад`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ${plural(hours, 'час', 'часа', 'часов')} назад`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} ${plural(days, 'день', 'дня', 'дней')} назад`;
  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
  });
}

export function formatDateTime(value) {
  if (!value) return '';
  return new Date(value).toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
  return `${minutes}:${String(secs).padStart(2, '0')}`;
}

export function formatBytes(bytes) {
  const value = Number(bytes) || 0;
  if (value < 1024) return `${value} Б`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} КБ`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} МБ`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(2)} ГБ`;
}

export function visibilityLabel(value) {
  return { public: 'Публичное', unlisted: 'По ссылке', private: 'Приватное' }[value] || value;
}

export function statusLabel(value) {
  return { published: 'Опубликовано', hidden: 'Скрыто' }[value] || value;
}

export function reportCategoryLabel(value) {
  return {
    spam: 'Спам или мошенничество',
    inappropriate: 'Неприемлемый контент',
    copyright: 'Нарушение авторских прав',
    other: 'Другое',
  }[value] || value;
}

export function reportStatusLabel(value) {
  return { open: 'Открыта', resolved: 'Решена', dismissed: 'Отклонена' }[value] || value;
}

export function roleLabel(value) {
  return { user: 'Пользователь', moderator: 'Модератор', admin: 'Администратор' }[value] || value;
}

export function qs(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value);
  });
  const text = search.toString();
  return text ? `?${text}` : '';
}

export function classNames(...values) {
  return values.filter(Boolean).join(' ');
}
