from importlib import import_module

import pytest

from app.migrations import MIGRATIONS


class FakeConnection:
    def __init__(self):
        self.statements = []

    def execute(self, statement):
        self.statements.append(str(statement))


class FakeBegin:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeEngine:
    def __init__(self):
        self.connection = FakeConnection()

    def begin(self):
        return FakeBegin(self.connection)


class FailingEngine:
    def begin(self):
        raise RuntimeError("database unavailable")


def captured_sql(fake_engine):
    return "\n".join(fake_engine.connection.statements)


def test_create_vendor_metrics_table_includes_nullable_lineage_columns(monkeypatch):
    migration = import_module("app.migrations.create_vendor_metrics_table")
    fake_engine = FakeEngine()
    monkeypatch.setattr(migration, "engine", fake_engine)

    migration.upgrade()

    sql = captured_sql(fake_engine)
    assert "source_provider VARCHAR NULL" in sql
    assert "source_period_start DATE NULL" in sql
    assert "source_period_end DATE NULL" in sql
    assert "provider_currency VARCHAR NULL" in sql
    assert "UNIQUE (user_id, vendor, identifier, month)" in sql


def test_add_lineage_migration_is_additive_nullable_and_registered(monkeypatch):
    migration = import_module("app.migrations.add_lineage_to_vendor_metrics")
    fake_engine = FakeEngine()
    monkeypatch.setattr(migration, "engine", fake_engine)

    migration.upgrade()

    sql = captured_sql(fake_engine)
    assert migration.upgrade in MIGRATIONS
    assert "ADD COLUMN IF NOT EXISTS source_provider VARCHAR" in sql
    assert "ADD COLUMN IF NOT EXISTS source_period_start DATE" in sql
    assert "ADD COLUMN IF NOT EXISTS source_period_end DATE" in sql
    assert "ADD COLUMN IF NOT EXISTS provider_currency VARCHAR" in sql
    assert "DEFAULT" not in sql.upper()


def test_add_lineage_downgrade_drops_nullable_lineage_columns(monkeypatch):
    migration = import_module("app.migrations.add_lineage_to_vendor_metrics")
    fake_engine = FakeEngine()
    monkeypatch.setattr(migration, "engine", fake_engine)

    migration.downgrade()

    sql = captured_sql(fake_engine)
    assert "DROP COLUMN IF EXISTS provider_currency" in sql
    assert "DROP COLUMN IF EXISTS source_period_end" in sql
    assert "DROP COLUMN IF EXISTS source_period_start" in sql
    assert "DROP COLUMN IF EXISTS source_provider" in sql


def test_add_lineage_migration_logs_and_reraises_upgrade_errors(monkeypatch):
    migration = import_module("app.migrations.add_lineage_to_vendor_metrics")
    monkeypatch.setattr(migration, "engine", FailingEngine())

    with pytest.raises(RuntimeError, match="database unavailable"):
        migration.upgrade()


def test_add_lineage_migration_logs_and_reraises_downgrade_errors(monkeypatch):
    migration = import_module("app.migrations.add_lineage_to_vendor_metrics")
    monkeypatch.setattr(migration, "engine", FailingEngine())

    with pytest.raises(RuntimeError, match="database unavailable"):
        migration.downgrade()


def test_create_vendor_metric_ingestion_runs_table_registered(monkeypatch):
    migration = import_module(
        "app.migrations.create_vendor_metric_ingestion_runs_table"
    )
    fake_engine = FakeEngine()
    monkeypatch.setattr(migration, "engine", fake_engine)

    migration.upgrade()

    sql = captured_sql(fake_engine)
    assert MIGRATIONS[-1] is migration.upgrade
    assert "CREATE TABLE IF NOT EXISTS vendor_metric_ingestion_runs" in sql
    assert "user_id INTEGER NOT NULL REFERENCES users(id)" in sql
    assert "vendor VARCHAR NOT NULL" in sql
    assert "identifier VARCHAR NOT NULL" in sql
    assert "requested_period_start DATE NULL" in sql
    assert "requested_period_end DATE NULL" in sql
    assert "source_period_start DATE NULL" in sql
    assert "source_period_end DATE NULL" in sql
    assert "status VARCHAR NOT NULL DEFAULT 'running'" in sql
    assert "records_received INTEGER NOT NULL DEFAULT 0" in sql
    assert "records_stored INTEGER NOT NULL DEFAULT 0" in sql
    assert "error_category VARCHAR NULL" in sql
    assert "'success', 'partial', 'failed'" in sql
    assert "'provider_error'" in sql
    assert "'row_validation'" in sql
    assert "'incomplete_source'" in sql
    assert "idx_vendor_metric_ingestion_runs_scope_started" in sql


def test_create_vendor_metric_ingestion_runs_downgrade(monkeypatch):
    migration = import_module(
        "app.migrations.create_vendor_metric_ingestion_runs_table"
    )
    fake_engine = FakeEngine()
    monkeypatch.setattr(migration, "engine", fake_engine)

    migration.downgrade()

    assert "DROP TABLE IF EXISTS vendor_metric_ingestion_runs" in captured_sql(
        fake_engine
    )
