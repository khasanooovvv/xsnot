"""Idempotent upgrade for deployments created with 32-bit Telegram IDs."""
from sqlalchemy import BigInteger, Integer, inspect, text
from app.models import Base


def widen_telegram_ids(connection):
    inspector = inspect(connection)
    quote = connection.dialect.identifier_preparer.quote
    for table in Base.metadata.sorted_tables:
        # Only Telegram identity columns, including every reference to users.
        targets = {
            column.name for column in table.columns
            if (table.name == 'users' and column.name == 'telegram_id')
            or any(fk.target_fullname == 'users.telegram_id' for fk in column.foreign_keys)
        }
        if not targets:
            continue
        for column in inspector.get_columns(table.name):
            if column['name'] not in targets:
                continue
            if isinstance(column['type'], BigInteger):
                continue
            if not isinstance(column['type'], Integer):
                raise RuntimeError(f"Unexpected Telegram ID type: {table.name}.{column['name']}")
            connection.execute(text(
                f"ALTER TABLE {quote(table.name)} ALTER COLUMN {quote(column['name'])} TYPE BIGINT"
            ))
