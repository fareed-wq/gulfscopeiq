import time
import httpx
import ipaddress
import ssl
import socket
import hashlib
import dns.resolver
import dns.exception
from urllib.parse import urljoin
from typing import Optional, Dict, Any, List, Tuple

from app.models.infrastructure import InfrastructureProfile, TLSSummary, IPIntelligence
from app.models.intelligence import Evidence, IntelligenceEntity, IntelligenceRelationship
from app.intelligence.company_web import fetch_website_safely, check_url_safety

IANA_DNS_URL = "https://data.iana.org/rdap/dns.json"
IANA_IPV4_URL = "https://data.iana.org/rdap/ipv4.json"
IANA_IPV6_URL = "https://data.iana.org/rdap/ipv6.json"

_rdap_cache: Dict[str, Any] = {}

async def safe_fetch_json(url: str, max_redirects: int = 3) -> dict:
    current_url = url
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            check_url_safety(current_url)
            resp = await client.get(current_url)
            if 300 <= resp.status_code < 400:
                loc = resp.headers.get("location")
                if not loc:
                    break
                current_url = urljoin(current_url, loc)
                continue
            if resp.status_code == 200:
                return resp.json()
            break
    return {}

def get_deterministic_id(*args) -> str:
    s = "-".join(str(a).lower() for a in args)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

async def get_iana_bootstrap(url: str):
    now = time.time()
    if url in _rdap_cache and now - _rdap_cache[url]["time"] < 86400:
        return _rdap_cache[url]["data"]
    data = await safe_fetch_json(url)
    if not data:
        raise Exception("Bootstrap fetch failed")
    _rdap_cache[url] = {"time": now, "data": data}
    return data

async def resolve_dns(domain: str) -> Tuple[dict, bool]:
    res = dns.resolver.Resolver()
    res.timeout = 2.0
    res.lifetime = 2.0

    records = {"A": [], "AAAA": [], "MX": [], "NS": []}
    has_error = False

    def _resolve(rtype):
        nonlocal has_error
        try:
            return res.resolve(domain, rtype)
        except dns.resolver.NoAnswer:
            return []
        except Exception:
            has_error = True
            return []

    for rdata in _resolve("A"):
        ip = rdata.to_text()
        try:
            if ipaddress.ip_address(ip).is_global:
                records["A"].append(ip)
        except ValueError:
            pass
            
    for rdata in _resolve("AAAA"):
        ip = rdata.to_text()
        try:
            if ipaddress.ip_address(ip).is_global:
                records["AAAA"].append(ip)
        except ValueError:
            pass

    for rdata in _resolve("MX"):
        host = rdata.exchange.to_text()
        if host.endswith('.'):
            host = host[:-1]
        records["MX"].append(host)

    for rdata in _resolve("NS"):
        host = rdata.target.to_text()
        if host.endswith('.'):
            host = host[:-1]
        records["NS"].append(host)

    records["A"] = list(dict.fromkeys(records["A"]))[:4]
    records["AAAA"] = list(dict.fromkeys(records["AAAA"]))[:4]
    records["MX"] = list(dict.fromkeys(records["MX"]))[:5]
    records["NS"] = list(dict.fromkeys(records["NS"]))[:5]

    return records, has_error

async def get_domain_rdap(domain: str) -> Tuple[dict, bool]:
    try:
        tld = domain.split('.')[-1].lower()
        data = await get_iana_bootstrap(IANA_DNS_URL)
        base_url = None
        for service in data.get("services", []):
            if tld in service[0]:
                for u in service[1]:
                    if u.startswith("https://"):
                        base_url = u
                        break
            if base_url: break

        if not base_url:
            return {}, False

        rdap_url = urljoin(base_url, f"domain/{domain}")
        payload = await safe_fetch_json(rdap_url)
        if not payload:
            return {}, False # Treated as not found, not necessarily operational error, wait... if safe_fetch_json fails due to timeout, it's an exception. Wait, safe_fetch_json catches nothing! It will bubble httpx exceptions. So try/except will catch it and return error. If it just returns {} (like a 404), then no error.

        registrar = None
        reg_date = None
        exp_date = None
        status = payload.get("status", [])

        for ent in payload.get("entities", []):
            roles = [r.lower() for r in ent.get("roles", [])]
            if "registrar" in roles:
                vcard = ent.get("vcardArray", [])
                if isinstance(vcard, list) and len(vcard) > 1:
                    for prop in vcard[1]:
                        if prop[0] == "fn":
                            registrar = str(prop[3])
                            break

        for ev in payload.get("events", []):
            action = ev.get("eventAction", "").lower()
            dt = ev.get("eventDate")
            if action == "registration":
                reg_date = dt
            elif action == "expiration":
                exp_date = dt

        return {
            "registrar": registrar,
            "registered_at": reg_date,
            "expires_at": exp_date,
            "domain_status": list(set(status))
        }, False
    except Exception:
        return {}, True

async def get_ip_rdap(ip: str) -> Tuple[dict, bool]:
    try:
        ip_obj = ipaddress.ip_address(ip)
        url = IANA_IPV6_URL if ip_obj.version == 6 else IANA_IPV4_URL
        data = await get_iana_bootstrap(url)
        base_url = None
        for service in data.get("services", []):
            for prefix in service[0]:
                try:
                    if ip_obj in ipaddress.ip_network(prefix):
                        for u in service[1]:
                            if u.startswith("https://"):
                                base_url = u
                                break
                except ValueError:
                    pass
            if base_url: break

        if not base_url:
            return {}, False

        rdap_url = urljoin(base_url, f"ip/{ip}")
        payload = await safe_fetch_json(rdap_url)
        if not payload:
            return {}, False

        org = payload.get("name")
        country = payload.get("country")
        
        if not org:
            for ent in payload.get("entities", []):
                vcard = ent.get("vcardArray", [])
                if isinstance(vcard, list) and len(vcard) > 1:
                    for prop in vcard[1]:
                        if prop[0] == "fn":
                            org = str(prop[3])
                            break
                if org: break

        return {
            "network_organization": org,
            "country": country
        }, False
    except Exception:
        return {}, True

def get_tls_summary(ip: str, domain: str) -> Tuple[Optional[TLSSummary], bool]:
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    
    sock = socket.socket(socket.AF_INET6 if ':' in ip else socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(4.0)
    try:
        sock.connect((ip, 443))
        with context.wrap_socket(sock, server_hostname=domain) as ssock:
            cert = ssock.getpeercert()
            if not cert:
                return None, False
                
            issuer = ""
            for rdn in cert.get("issuer", []):
                for attr in rdn:
                    if attr[0] in ("organizationName", "commonName"):
                        issuer = attr[1]
            
            san_names = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]
            
            return TLSSummary(
                issuer=issuer,
                valid_from=cert.get("notBefore", ""),
                valid_until=cert.get("notAfter", ""),
                san_count=len(san_names),
                san_names=san_names[:5]
            ), False
    except Exception:
        return None, True
    finally:
        sock.close()

def detect_technologies(headers: dict, html: str) -> List[str]:
    techs = set()
    headers = {k.lower(): str(v).lower() for k, v in headers.items()}
    html_lower = html.lower()

    if "cloudfront" in headers.get("via", "") or headers.get("x-amz-cf-id"): techs.add("AWS CloudFront")
    if "akamai" in headers.get("server", "") or headers.get("x-akamai-transformed"): techs.add("Akamai")
    if "varnish" in headers.get("via", "") or "cache-" in headers.get("x-served-by", ""): techs.add("Fastly")
    if "vercel" in headers.get("server", "") or headers.get("x-vercel-id"): techs.add("Vercel")
    if "netlify" in headers.get("server", "") or headers.get("x-nf-request-id"): techs.add("Netlify")
    
    server = headers.get("server", "")
    if "nginx" in server: techs.add("Nginx")
    if "apache" in server: techs.add("Apache")
    if "microsoft-iis" in server: techs.add("IIS")
    
    if "/wp-content/" in html_lower or "/wp-includes/" in html_lower or "wordpress" in html_lower: techs.add("WordPress")
    if "x-nextjs-cache" in headers or "/_next/" in html_lower: techs.add("Next.js")
    if '__next' in html_lower or "data-reactroot" in html_lower: techs.add("React")
    if "vue." in html_lower or "data-v-" in html_lower: techs.add("Vue.js")
    
    if "php" in headers.get("x-powered-by", ""): techs.add("PHP")
    if "asp.net" in headers.get("x-powered-by", ""): techs.add("ASP.NET")
    
    if "google-analytics.com" in html_lower or "googletagmanager.com/gtag" in html_lower or "ua-" in html_lower or "g-" in html_lower: techs.add("Google Analytics")
    if "googletagmanager.com/gtm" in html_lower: techs.add("Google Tag Manager")

    return sorted(list(techs))

async def investigate_infrastructure(domain: str) -> dict:
    profile = InfrastructureProfile(domain=domain)
    entities = []
    relationships = []
    
    dom_id = get_deterministic_id("domain", domain)
    entities.append(IntelligenceEntity(id=dom_id, type="Domain", label=domain, attributes={}))
    
    has_success = False
    has_error = False
    
    dns_records, dns_err = await resolve_dns(domain)
    if dns_err: has_error = True
    profile.ipv4 = dns_records["A"]
    profile.ipv6 = dns_records["AAAA"]
    profile.mx = dns_records["MX"]
    profile.nameservers = dns_records["NS"]
    
    if any([profile.ipv4, profile.ipv6, profile.mx, profile.nameservers]):
        has_success = True

    rdap, rdap_err = await get_domain_rdap(domain)
    if rdap_err: has_error = True
    if rdap:
        profile.registrar = rdap.get("registrar")
        profile.registered_at = rdap.get("registered_at")
        profile.expires_at = rdap.get("expires_at")
        profile.domain_status = rdap.get("domain_status", [])
        has_success = True

    public_ips = (profile.ipv4 + profile.ipv6)[:2]
    
    for ip in public_ips:
        ip_data, ip_err = await get_ip_rdap(ip)
        if ip_err: has_error = True
        intel = IPIntelligence(
            ip=ip,
            network_organization=ip_data.get("network_organization"),
            country=ip_data.get("country")
        )
        profile.ip_intelligence.append(intel)
        
        ip_id = get_deterministic_id("ip", ip)
        entities.append(IntelligenceEntity(id=ip_id, type="IPAddress", label=ip, attributes={}))
        relationships.append(IntelligenceRelationship(source=dom_id, target=ip_id, type="resolves_to", confidence="high"))

    if public_ips:
        tls, tls_err = get_tls_summary(public_ips[0], domain)
        if tls_err: has_error = True
        if tls:
            profile.tls = tls

    try:
        web_res = await fetch_website_safely(f"https://{domain}")
        html = web_res.get("html", "")
        headers = web_res.get("headers", {})
        techs = detect_technologies(headers, html)
        profile.technologies = techs
        for t in techs:
            t_id = get_deterministic_id("technology", t)
            entities.append(IntelligenceEntity(id=t_id, type="Technology", label=t, attributes={}))
            relationships.append(IntelligenceRelationship(source=dom_id, target=t_id, type="uses", confidence="medium"))
        has_success = True
    except Exception:
        has_error = True
        
    if not has_success:
        profile.status = "unavailable"
    elif has_error:
        profile.status = "partial"
    else:
        profile.status = "collected"

    # Deduplicate
    seen_ent = set()
    uniq_ent = []
    for e in entities:
        if e.id not in seen_ent:
            uniq_ent.append(e)
            seen_ent.add(e.id)
            
    seen_rel = set()
    uniq_rel = []
    for r in relationships:
        key = f"{r.source}-{r.target}-{r.type}"
        if key not in seen_rel:
            uniq_rel.append(r)
            seen_rel.add(key)

    return {
        "profile": profile,
        "entities": uniq_ent,
        "relationships": uniq_rel,
        "status": profile.status
    }
