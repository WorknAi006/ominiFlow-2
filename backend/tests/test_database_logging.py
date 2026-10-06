import unittest
from unittest.mock import Mock, patch

from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from app.core import database


class DatabaseLoggingTests(unittest.TestCase):
    def test_application_engine_hides_parameters(self) -> None:
        self.assertTrue(database.engine.hide_parameters)
        self.assertFalse(database.engine.echo)
        self.assertIs(database.SessionLocal.kw["bind"], database.engine)

    def test_exception_format_hides_representative_bound_values(self) -> None:
        values = (
            "synthetic-password-DoNotLog",
            "+15550102030",
            "synthetic private message body",
        )
        error = StatementError(
            "synthetic database failure",
            "INSERT INTO synthetic_table (password, phone, body) VALUES (?, ?, ?)",
            values,
            RuntimeError("synthetic driver failure"),
            hide_parameters=database.engine.hide_parameters,
        )

        formatted = str(error)
        for value in values:
            self.assertNotIn(value, formatted)

    def test_get_db_still_yields_and_closes_synchronous_session(self) -> None:
        session = Mock(spec=Session)
        with patch.object(database, "SessionLocal", return_value=session) as factory:
            dependency = database.get_db()
            self.assertIs(next(dependency), session)
            factory.assert_called_once_with()
            dependency.close()
            session.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
