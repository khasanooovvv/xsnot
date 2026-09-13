"""Regression coverage for Telegram IDs above the signed int32 limit."""
import unittest
from unittest.mock import Mock, patch

try:
    from sqlalchemy import BigInteger, Integer, select
    from sqlalchemy.dialects.postgresql import asyncpg
    from app.models import Base, User
    from app.migrations import widen_telegram_ids
    AVAILABLE = True
except ModuleNotFoundError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'SQLAlchemy is required')
class TelegramIdTests(unittest.TestCase):
    def test_query_binds_large_telegram_id_as_bigint(self):
        query = select(User).where(User.telegram_id == 6_322_372_175)
        compiled = query.compile(dialect=asyncpg.dialect())
        self.assertIn('::BIGINT', str(compiled))
        self.assertIn(6_322_372_175, compiled.params.values())

    def test_all_telegram_foreign_keys_are_bigint(self):
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if column is User.__table__.c.telegram_id or any(
                    fk.target_fullname == 'users.telegram_id' for fk in column.foreign_keys
                ):
                    with self.subTest(table=table.name, column=column.name):
                        self.assertIsInstance(column.type, BigInteger)

    def test_upgrade_only_changes_legacy_id_columns_and_is_repeatable(self):
        connection = Mock()
        connection.dialect.identifier_preparer.quote.side_effect = lambda name: name
        inspector = Mock()
        legacy = True
        def columns(table_name):
            return [{'name':c.name, 'type':Integer() if legacy and isinstance(c.type, BigInteger) else c.type}
                    for c in Base.metadata.tables[table_name].columns]
        inspector.get_columns.side_effect = columns
        with patch('app.migrations.inspect', return_value=inspector):
            widen_telegram_ids(connection)
            statements = [str(c.args[0]) for c in connection.execute.call_args_list]
            self.assertIn('ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT', statements)
            self.assertIn('ALTER TABLE mini_messages ALTER COLUMN sender_id TYPE BIGINT', statements)
            self.assertFalse(any('ALTER COLUMN id ' in s for s in statements))
            self.assertEqual(len(statements), 11)
            connection.reset_mock()
            legacy = False
            widen_telegram_ids(connection)
            connection.execute.assert_not_called()
