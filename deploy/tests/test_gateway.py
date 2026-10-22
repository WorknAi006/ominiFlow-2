"""Regression tests for preservation of a shared production gateway."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("gateway", Path(__file__).parents[1] / "gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)

EXISTING = '''# gateway owned by another project
events { worker_connections 1024; }
http {
    map $http_upgrade $existing_upgrade { default upgrade; '' close; }
    # A brace in a comment } must not end the http block.
    server {
        listen 80;
        server_name existing.example;
        location / { return 200 "quoted } and { braces"; }
    }
}
# retain trailing content
'''


class GatewayTests(unittest.TestCase):
    def test_preserves_every_unrelated_byte_and_is_idempotent(self):
        section = gateway.render("/etc/letsencrypt/live/fmfilms-0001")
        merged = gateway.merge(EXISTING, section)
        self.assertEqual(merged.replace("\n" + section + "\n", "", 1), EXISTING)
        self.assertEqual(gateway.merge(merged, section), merged)

    def test_updates_only_marked_section(self):
        http = gateway.merge(EXISTING, gateway.render())
        tls = gateway.merge(http, gateway.render("/etc/letsencrypt/live/fmfilms-0001"))
        self.assertEqual(tls.count(gateway.BEGIN), 1)
        self.assertIn("ssl_certificate /etc/letsencrypt/live/fmfilms-0001/fullchain.pem;", tls)
        self.assertEqual(gateway.merge(tls, gateway.render()), http)

    def test_rejects_unmanaged_duplicate_domains_including_quoted_names(self):
        for domain in gateway.DOMAINS:
            source = EXISTING.replace("server_name existing.example", f'server_name "{domain}"')
            with self.assertRaises(ValueError):
                gateway.merge(source, gateway.render())

    def test_rejects_malformed_duplicate_and_nested_markers(self):
        samples = [
            EXISTING + "\n" + gateway.BEGIN,
            EXISTING + "\n" + gateway.BEGIN + "\n" + gateway.END,
            EXISTING.replace('listen 80;', gateway.BEGIN + "\n" + gateway.END + "\nlisten 80;"),
            gateway.merge(EXISTING, gateway.render()) + "\n" + gateway.render(),
        ]
        for source in samples:
            with self.subTest(source=source), self.assertRaises(ValueError):
                gateway.merge(source, gateway.render())

    def test_does_not_assume_last_brace_is_http(self):
        source = EXISTING + "stream { server { listen 127.0.0.1:9999; } }\n"
        result = gateway.merge(source, gateway.render())
        self.assertLess(result.index(gateway.END), result.index("stream {"))

    def test_preserves_unquoted_braced_nginx_variables(self):
        source = EXISTING.replace('return 200 "quoted } and { braces"', 'proxy_pass http://${existing_backend}')
        merged = gateway.merge(source, gateway.render())
        self.assertIn('proxy_pass http://${existing_backend};', merged)
        self.assertEqual(gateway.merge(merged, gateway.render()), merged)

    def test_routing_preserves_next_routes_and_uses_dynamic_docker_dns(self):
        result = gateway.render("/etc/letsencrypt/live/fmfilms")
        self.assertIn("location ^~ /api/v1/", result)
        self.assertNotIn("location /api/", result)
        self.assertIn("proxy_buffering off", result)
        self.assertIn("proxy_set_header Upgrade $http_upgrade", result)
        self.assertIn("resolver 127.0.0.11", result)
        self.assertIn("proxy_pass http://$fmfilms_upstream$request_uri", result)
        self.assertIn("root /var/www/certbot", result)
        self.assertNotIn("api.fmfilms.in", result)

    def test_restore_preserves_unrelated_changes_made_after_backup(self):
        previous = gateway.merge(EXISTING, gateway.render())
        current = gateway.merge(previous, gateway.render("/etc/letsencrypt/live/fmfilms"))
        current = current.replace("existing.example", "new-unrelated.example")
        restored = gateway.restore(current, previous)
        self.assertIn("new-unrelated.example", restored)
        self.assertNotIn("ssl_certificate", restored)

    def test_restore_without_previous_markers_removes_only_our_section(self):
        current = gateway.merge(EXISTING, gateway.render())
        restored = gateway.restore(current, EXISTING)
        self.assertNotIn(gateway.BEGIN, restored)
        self.assertIn('server_name existing.example;', restored)

    def test_certificate_path_cannot_inject_nginx_directives(self):
        with self.assertRaises(ValueError):
            gateway.render("/etc/letsencrypt/live/a; include /tmp/evil;")


if __name__ == "__main__":
    unittest.main()
