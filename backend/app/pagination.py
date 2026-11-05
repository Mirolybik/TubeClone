import math

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def paginate(db: Session, stmt: Select, page: int, page_size: int):
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    pages = max(1, math.ceil(total / page_size)) if total else 1
    return items, total, page, page_size, pages
