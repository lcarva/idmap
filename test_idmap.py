import contextlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

import idmap


class IdmapTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "idmap.db"
        self.conn = idmap.connect(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tempdir.cleanup()

    def run_command(self, *argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = idmap.main(["--db", str(self.db_path), *argv])
        return result, stdout.getvalue(), stderr.getvalue()

    def test_connect_enables_foreign_keys_and_creates_schema(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        tables = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertTrue({"entity", "namespace", "identifier"}.issubset(tables))

    def test_parse_ident_normalizes_namespace_and_preserves_handle(self):
        self.assertEqual(idmap.parse_ident(" GitHub:Alice Smith "), ("github", "Alice Smith"))

    def test_parse_ident_rejects_missing_parts(self):
        for value in ("alice", ":alice", "github:", "  :  "):
            with self.subTest(value=value):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        idmap.parse_ident(value)
            self.assertEqual(raised.exception.code, 2)

    def test_set_get_merges_entities_and_returns_sorted_identifiers(self):
        self.assertEqual(self.run_command("set", "GitHub:z", "ldap:asmith")[0], 0)
        self.assertEqual(self.run_command("set", "gitlab:alice", "github:z")[0], 0)
        self.assertEqual(
            self.run_command("get", "LDAP:asmith"),
            (0, "github:z\ngitlab:alice\nldap:asmith\n", ""),
        )

        entity_count = self.conn.execute("SELECT COUNT(*) FROM entity").fetchone()[0]
        self.assertEqual(entity_count, 1)

    def test_set_merges_existing_entities_and_preserves_name(self):
        self.run_command("set", "one:first")
        self.run_command("set", "two:second")
        self.run_command("name", "two:second", "Second Person")

        self.assertEqual(self.run_command("set", "one:first", "two:second")[0], 0)
        self.assertEqual(
            self.run_command("get", "one:first", "--name"),
            (0, "Second Person\n", ""),
        )
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM entity").fetchone()[0], 1
        )

    def test_get_namespace_and_name_return_status_without_output_when_unknown(self):
        self.run_command("set", "github:alice")
        self.assertEqual(self.run_command("get", "github:alice", "--ns", "ldap"), (1, "", ""))
        self.assertEqual(self.run_command("get", "github:alice", "--name"), (1, "", ""))
        self.assertEqual(self.run_command("get", "github:nobody"), (1, "", ""))

    def test_name_and_ls_show_labeled_entities(self):
        self.run_command("set", "github:alice", "ldap:asmith")
        self.run_command("name", "github:alice", "Alice Smith")
        self.assertEqual(
            self.run_command("ls"),
            (0, "#1 (Alice Smith): github:alice, ldap:asmith\n", ""),
        )
        self.assertEqual(
            self.run_command("ls", "--ns", "GITHUB"),
            (0, "github:alice\n", ""),
        )

    def test_unlink_splits_identifier_into_new_entity(self):
        self.run_command("set", "github:alice", "ldap:asmith", "quay:alice-q")
        self.run_command("unlink", "quay:alice-q")

        self.assertEqual(self.run_command("get", "quay:alice-q"), (0, "quay:alice-q\n", ""))
        self.assertEqual(
            self.run_command("get", "github:alice"),
            (0, "github:alice\nldap:asmith\n", ""),
        )
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM entity").fetchone()[0], 2)

    def test_rm_removes_identifier_and_prunes_empty_entity(self):
        self.run_command("set", "github:alice", "ldap:asmith")
        self.run_command("rm", "ldap:asmith")
        self.assertEqual(self.run_command("get", "github:alice"), (0, "github:alice\n", ""))
        self.assertEqual(self.run_command("get", "ldap:asmith"), (1, "", ""))

        self.run_command("rm", "github:alice")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM entity").fetchone()[0], 0)

    def test_missing_mutating_identifier_reports_error(self):
        for command in ("unlink", "rm", "name"):
            args = [command, "github:nobody"]
            if command == "name":
                args.append("Nobody")
            with self.subTest(command=command):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as raised:
                        idmap.main(["--db", str(self.db_path), *args])
                self.assertEqual(raised.exception.code, 2)
                self.assertIn("no such identifier: github:nobody", stderr.getvalue())
                self.assertEqual(stdout.getvalue(), "")

    def test_namespace_commands_normalize_and_sort(self):
        self.assertEqual(self.run_command("namespace", "set", "GitHub", "https://github.com")[0], 0)
        self.assertEqual(
            self.run_command("namespace", "get", "GITHUB"),
            (0, "https://github.com\n", ""),
        )
        self.run_command("namespace", "set", "ldap", "https://ldap.example")
        self.assertEqual(
            self.run_command("namespace", "ls"),
            (0, "github\thttps://github.com\nldap\thttps://ldap.example\n", ""),
        )

    def test_namespace_get_unknown_returns_one(self):
        self.assertEqual(self.run_command("namespace", "get", "github"), (1, "", ""))

    def test_cli_rejects_invalid_identifier(self):
        with self.assertRaises(SystemExit) as raised:
            self.run_command("set", "not-an-identifier")
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
