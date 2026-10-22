"""Build an isolated gateway section; never write the live configuration here."""
import argparse
import json
from pathlib import Path
import re
import subprocess

DOMAINS = ("fmfilms.in", "www.fmfilms.in", "admin.fmfilms.in")
BEGIN = "# BEGIN FMFILMS"
END = "# END FMFILMS"


def tokens(source):
    """Nginx tokens with byte/character offsets, ignoring comments and quoted braces."""
    pattern = r'''\s+|\#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[{};]|(?:\\.|\$\{[^}\s]+\}|[^\s{};#"'])+'''
    for match in re.finditer(pattern, source):
        value = match.group()
        if not value.isspace() and not value.startswith("#"):
            yield value, match.start(), match.end()


def http_bounds(source):
    stack, directive, found = [], [], []
    for value, start, end in tokens(source):
        if value == "{":
            name = directive[0] if directive else ""
            if name == "http" and not stack:
                found.append([end, None])
            stack.append(name)
            directive = []
        elif value == "}":
            if not stack:
                raise ValueError("Unbalanced gateway configuration")
            if stack == ["http"]:
                found[-1][1] = start
            stack.pop()
            directive = []
        elif value == ";":
            directive = []
        else:
            directive.append(value)
    if stack or len(found) != 1 or found[0][1] is None:
        raise ValueError("Expected exactly one top-level http block")
    return found[0]


def managed_span(source):
    starts = list(re.finditer(r"(?m)^[ \t]*# BEGIN FMFILMS[ \t]*\r?$", source))
    ends = list(re.finditer(r"(?m)^[ \t]*# END FMFILMS[ \t]*\r?$", source))
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or starts[0].start() >= ends[0].start():
        raise ValueError("Invalid or duplicate FMFILMS markers; inspect manually")
    return starts[0].start(), ends[0].end()


def assert_no_domains(source):
    directive = []
    for value, _, _ in tokens(source):
        if value in (";", "{", "}"):
            if directive and directive[0] == "server_name":
                for name in directive[1:]:
                    name = name.strip("\"'").lower()
                    if name in DOMAINS:
                        raise ValueError("Unmanaged FM Films server_name found; reconcile it manually")
            directive = []
        else:
            directive.append(value)


def merge(source, section):
    left, right = http_bounds(source)
    span = managed_span(source)
    if span:
        start, end = span
        if not left <= start < end <= right:
            raise ValueError("FMFILMS section must be inside http")
        # Ensure the markers are direct children of http, not in a server block.
        depth = 0
        for value, offset, _ in tokens(source):
            if offset >= start:
                break
            depth += (value == "{") - (value == "}")
        if depth != 1:
            raise ValueError("FMFILMS section is nested inside an unrelated block")
        unmanaged = source[:start] + source[end:]
        assert_no_domains(unmanaged)
        return source[:start] + section + source[end:]
    assert_no_domains(source)
    return source[:right] + "\n" + section + "\n" + source[right:]


def restore(source, previous):
    previous_span = managed_span(previous)
    if previous_span:
        return merge(source, previous[previous_span[0]:previous_span[1]])
    span = managed_span(source)
    if span:
        # Use merge first to validate placement and reject unmanaged duplicates.
        merge(source, render())
        return source[:span[0]] + source[span[1]:]
    return source


def proxy(upstream, location="/", websocket=False):
    extra = ""
    if websocket:
        extra = '''        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $fmfilms_connection_upgrade;
'''
    return f'''    location {location} {{
        set $fmfilms_upstream {upstream};
        proxy_pass http://$fmfilms_upstream$request_uri;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_read_timeout 3600s;
        proxy_send_timeout 300s;
        proxy_buffering off;
{extra}    }}
'''


def render(cert=None):
    challenge = '''    location ^~ /.well-known/acme-challenge/ {
        root /var/www/certbot;
        default_type text/plain;
        try_files $uri =404;
    }
'''
    result = BEGIN + '''
map $http_upgrade $fmfilms_connection_upgrade {
    default upgrade;
    '' close;
}
server {
    listen 80;
    server_name fmfilms.in www.fmfilms.in admin.fmfilms.in;
''' + challenge
    result += "    location / { return 301 https://$host$request_uri; }\n" if cert else "    location / { return 503; }\n"
    result += "}\n"
    if cert:
        if not re.fullmatch(r"/etc/letsencrypt/live/[A-Za-z0-9_.-]+", cert):
            raise ValueError("Unexpected certificate path")
        for names, upstream in (("fmfilms.in www.fmfilms.in", "fmfilms-web:3000"), ("admin.fmfilms.in", "fmfilms-admin:3000")):
            result += f'''server {{
    listen 443 ssl;
    server_name {names};
    ssl_certificate {cert}/fullchain.pem;
    ssl_certificate_key {cert}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    resolver 127.0.0.11 valid=10s ipv6=off;
    client_max_body_size 110m;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
'''
            result += challenge
            result += proxy("fmfilms-backend:8000", "^~ /api/v1/", True)
            result += proxy("fmfilms-backend:8000", "= /api/v1", True)
            result += proxy("fmfilms-backend:8000", "= /health")
            result += proxy(upstream)
            result += "}\n"
    return result + END


def certificate(root=Path("/etc/letsencrypt/live"), allow_expired=False):
    """Discover an exact three-domain, non-staging, currently valid lineage."""
    for directory in sorted(root.glob("*")):
        fullchain = directory / "fullchain.pem"
        if not fullchain.is_file() or not (directory / "privkey.pem").is_file():
            continue
        try:
            details = subprocess.check_output(["openssl", "x509", "-in", str(fullchain), "-noout", "-ext", "subjectAltName", "-issuer"], text=True)
            sans = set(re.findall(r"DNS:([^,\s]+)", details))
            valid = subprocess.run(["openssl", "x509", "-in", str(fullchain), "-noout", "-checkend", "0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            if sans == set(DOMAINS) and (valid or allow_expired) and not re.search(r"staging|fake|pretend", details, re.I):
                return directory
        except subprocess.CalledProcessError:
            continue
    raise ValueError("No valid production certificate covering exactly the three FM Films names")


def preflight(inspect):
    data = json.loads(inspect)[0]
    if not data["State"]["Running"]:
        raise ValueError("lovenzea-gateway must be running")
    if "lovenzea_default" not in data["NetworkSettings"]["Networks"]:
        raise ValueError("Gateway is not on lovenzea_default")
    mounts = {m["Destination"]: m for m in data["Mounts"]}
    for destination, source in (("/etc/nginx/nginx.conf", "/var/www/lovenzea_v1/gateway.nginx.conf"), ("/etc/letsencrypt", "/etc/letsencrypt"), ("/var/www/certbot", "/var/www/certbot")):
        if destination not in mounts or mounts[destination]["Source"] != source:
            raise ValueError(f"Unexpected gateway mount for {destination}; inspect before proceeding")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("candidate", "restore", "certificate", "preflight", "check-dump"))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--certificate")
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--allow-expired", action="store_true")
    args = parser.parse_args()
    if args.command == "certificate":
        print(certificate(allow_expired=args.allow_expired))
    elif args.command == "preflight":
        import sys
        preflight(sys.stdin.read())
    elif args.command == "check-dump":
        import sys
        dump = sys.stdin.read()
        span = managed_span(dump)
        if span:
            dump = dump[:span[0]] + dump[span[1]:]
        assert_no_domains(dump)
    else:
        source = args.config.read_bytes().decode("utf-8")
        if args.command == "restore":
            candidate = restore(source, args.previous.read_bytes().decode("utf-8"))
        else:
            candidate = merge(source, render(args.certificate))
        args.output.write_bytes(candidate.encode("utf-8"))


if __name__ == "__main__":
    main()
