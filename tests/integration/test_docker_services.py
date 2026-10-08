"""
Connectivity of the Docker development services, run from the ``app`` container:

    app ──SQLAlchemy / pyodbc──► sqlserver:1433       (TestSqlServerConnectivity)
    app ──IBKR API (ibapi)────► ibkr:4004 IB Gateway  (TestIbGatewayConnectivity)

The tests only run where the environment points at those services (DB_HOST / IBKR_HOST, set
by docker-compose.yml); elsewhere they are skipped. No order is ever sent: the IBKR test only
connects, reads the server time and the account list, and checks it is a paper account.

    python -m pytest tests/integration -v
"""

import os
import threading
import time
import unittest
import uuid

DB_CONFIGURED = bool(os.getenv("DB_HOST") or os.getenv("DB_SERVER"))
IBKR_CONFIGURED = bool(os.getenv("IBKR_HOST"))


@unittest.skipUnless(DB_CONFIGURED, "DB_HOST not set: run inside the app container (docker compose)")
class TestSqlServerConnectivity(unittest.TestCase):

    def test_sqlalchemy_reaches_sql_server(self):
        import sqlalchemy as sa
        from src.infrastructure.database.settings import get_database_url

        engine = sa.create_engine(get_database_url("sql_server"))
        with engine.connect() as conn:
            version = conn.execute(sa.text("SELECT @@VERSION")).scalar()
            database = conn.execute(sa.text("SELECT DB_NAME()")).scalar()
        self.assertIn("Microsoft SQL Server", version)
        self.assertEqual(database, os.getenv("DB_NAME", "base_infra"))

    def test_existing_repositories_read_and_write(self):
        """DatabaseService('sql_server') creates the schema; a repository round trip works."""
        from src.application.services.database_service.database_service import DatabaseService
        from src.infrastructure.models.continent import ContinentModel
        from src.infrastructure.repositories.repository_factory import RepositoryFactory

        service = DatabaseService("sql_server")
        service.set_ext_db()
        session = service.session
        name = f"docker-check-{uuid.uuid4().hex[:8]}"
        try:
            repo = RepositoryFactory(session).get_local_repository("Continent")
            created = repo._create_or_get(name=name, hemisphere="Northern")
            self.assertIsNotNone(created)
            self.assertEqual(repo.get_by_name(name).name, name)
        finally:
            session.query(ContinentModel).filter(ContinentModel.name == name).delete()
            session.commit()
            session.close()


@unittest.skipUnless(IBKR_CONFIGURED, "IBKR_HOST not set: run inside the app container (docker compose)")
class TestIbGatewayConnectivity(unittest.TestCase):

    def test_api_connection_to_ib_gateway(self):
        from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
        from src.application.services.misbuffet.brokers.ibkr.ibkr_settings import resolve_endpoint

        # dedicated client id so the test never collides with a running application session
        endpoint = resolve_endpoint("127.0.0.1", 7497, int(os.getenv("IBKR_TEST_CLIENT_ID", "999")))
        client = IBTWSClient(endpoint.host, endpoint.port, endpoint.client_id)
        server_time = {}
        got_time = threading.Event()

        def current_time(t):
            server_time["t"] = t
            got_time.set()

        client.currentTime = current_time
        try:
            self.assertTrue(client.connect_to_tws(),
                            f"no IBKR API handshake with {endpoint.host}:{endpoint.port} - is the ibkr "
                            f"service healthy? (docker compose ps / docker compose logs ibkr)")
            client.reqCurrentTime()
            self.assertTrue(got_time.wait(10), "IB Gateway did not answer reqCurrentTime")
            self.assertLess(abs(server_time["t"] - time.time()), 300)

            deadline = time.time() + 10
            while not client.get_managed_accounts() and time.time() < deadline:
                time.sleep(0.2)
            accounts = client.get_managed_accounts()
            self.assertTrue(accounts, "no managed accounts reported by IB Gateway")
            if endpoint.paper:
                # IBKR paper accounts start with "D" (DU..., DF...)
                self.assertTrue(all(a.startswith("D") for a in accounts),
                                f"IBKR_ACCOUNT_MODE=paper but accounts {accounts} are not paper accounts")
        finally:
            client.disconnect_from_tws()


if __name__ == "__main__":
    unittest.main()
