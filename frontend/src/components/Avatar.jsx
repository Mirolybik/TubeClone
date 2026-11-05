import { channelName, classNames, initials } from '../utils';

const COLORS = [
  '#c62828',
  '#5c6bc0',
  '#00796b',
  '#ef6c00',
  '#6d4c41',
  '#455a64',
];

function hash(value = '') {
  let result = 0;
  for (let index = 0; index < value.length; index += 1) {
    result = (result * 31 + value.charCodeAt(index)) % 997;
  }
  return result;
}

export default function Avatar({ user, size = 40, className = '' }) {
  const name = channelName(user);
  const color = COLORS[hash(user?.username || name) % COLORS.length];
  const style = { width: size, height: size, fontSize: Math.max(12, size * 0.36), background: color };
  if (user?.avatar_url) {
    return (
      <img
        className={classNames('avatar', className)}
        style={{ width: size, height: size }}
        src={user.avatar_url}
        alt={name}
      />
    );
  }
  return (
    <span className={classNames('avatar', className)} style={style} title={name}>
      {initials(name)}
    </span>
  );
}
