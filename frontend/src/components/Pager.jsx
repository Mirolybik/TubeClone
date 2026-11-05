export default function Pager({ page, pages, onChange }) {
  if (!pages || pages <= 1) return null;
  return (
    <div className="pager">
      <button type="button" className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Назад
      </button>
      <span>
        Страница {page} из {pages}
      </span>
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        Вперёд →
      </button>
    </div>
  );
}
