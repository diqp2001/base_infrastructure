"""docker-compose.yml: nothing published beyond localhost, hardened dashboard container."""

import os
import re
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _interpolate_defaults(value: str) -> str:
    """Resolve ${VAR:-default} to its default (the committed configuration)."""
    return re.sub(r"\$\{[^}:]+:-([^}]*)\}", r"\1", str(value))


class ComposeExposureTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "docker-compose.yml"), encoding="utf-8") as f:
            cls.compose = yaml.safe_load(f)
        cls.services = cls.compose["services"]

    def test_published_ports_are_bound_to_localhost(self):
        for name, svc in self.services.items():
            for port in svc.get("ports", []):
                spec = _interpolate_defaults(port)
                parts = spec.split(":")
                self.assertEqual(len(parts), 3, f"{name}: {port} must name the host address")
                self.assertEqual(parts[0], "127.0.0.1", f"{name}: {port}")

    def test_no_docker_socket_and_private_network(self):
        text = open(os.path.join(ROOT, "docker-compose.yml"), encoding="utf-8").read()
        self.assertNotIn("docker.sock", text)
        for name, svc in self.services.items():
            self.assertEqual(svc.get("networks"), ["backend"], name)
            self.assertNotIn("network_mode", svc, name)

    def test_dashboard_container_is_hardened(self):
        m = self.services["monitor"]
        self.assertTrue(m["read_only"])
        self.assertIn("ALL", m["cap_drop"])
        self.assertIn("no-new-privileges:true", m["security_opt"])
        self.assertTrue(all(v.endswith(":ro") for v in m["volumes"]), m["volumes"])
        self.assertNotIn("secrets", m)
        env = m["environment"]
        self.assertNotIn("DB_PASSWORD", env)            # only the read-only login
        self.assertNotIn("DB_USER", env)
        self.assertIn("DB_READONLY_USER", env)
        self.assertIn("src.interfaces.flask.monitoring_app:app", " ".join(m["command"]))

    def test_secrets_are_not_environment_variables(self):
        ibkr = self.services["ibkr"]["environment"]
        self.assertNotIn("TWS_PASSWORD", ibkr)
        self.assertEqual(ibkr["TWS_PASSWORD_FILE"], "/run/secrets/ibkr_password")

    def test_paper_trading_is_the_default(self):
        self.assertEqual(_interpolate_defaults(self.services["ibkr"]["environment"]["TRADING_MODE"]), "paper")
        self.assertEqual(_interpolate_defaults(self.services["app"]["environment"]["IBKR_ALLOW_LIVE"]), "no")
        example = open(os.path.join(ROOT, ".env.example"), encoding="utf-8").read()
        self.assertIn("IBKR_ACCOUNT_MODE=paper", example)
        self.assertIn("DASHBOARD_BIND=127.0.0.1", example)

    def test_env_files_are_git_ignored(self):
        ignore = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read().split()
        for entry in (".env", ".env.windows", "secrets/", ".monitor/"):
            self.assertIn(entry, ignore)


if __name__ == "__main__":
    unittest.main()
