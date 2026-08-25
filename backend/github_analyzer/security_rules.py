"""
security_rules.py — Security vulnerability detection rules.

Each rule defines:
  - pattern: regex to match in file content
  - severity: critical / high / medium / low / info
  - category: secret, injection, ssrf, xss, etc.
  - title: short title
  - description: detailed explanation
  - recommendation: how to fix
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Rule:
    id: str
    pattern: str
    severity: str
    category: str
    title: str
    description: str
    recommendation: str
    flags: int = re.IGNORECASE
    languages: List[str] = field(default_factory=list)  # empty = all languages
    exclude_patterns: List[str] = field(default_factory=list)


# ── SECRET / CREDENTIAL DETECTION ──────────────────────────────────────────

SECRET_RULES = [
    Rule(
        id="SEC-001",
        pattern=r"""(?:aws_access_key_id|aws_secret_access_key)\s*[:=]\s*['"]?([A-Z0-9]{20,})['"]?""",
        severity="critical", category="secret",
        title="AWS Access Key",
        description="AWS access key ID detected. This can be used to access AWS services and resources.",
        recommendation="Revoke the key immediately in AWS IAM console. Use environment variables or IAM roles instead.",
    ),
    Rule(
        id="SEC-002",
        pattern=r"""(?:aws_secret_access_key|SECRET_KEY)\s*[:=]\s*['"]([A-Za-z0-9/+=]{40})['"]""",
        severity="critical", category="secret",
        title="AWS Secret Key",
        description="AWS secret access key detected. Provides full access to AWS account.",
        recommendation="Revoke immediately. Rotate credentials and use AWS Secrets Manager or environment variables.",
    ),
    Rule(
        id="SEC-003",
        pattern=r"""(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}""",
        severity="critical", category="secret",
        title="GitHub Personal Access Token",
        description="GitHub PAT detected. Grants access to repositories, user data, and organization resources.",
        recommendation="Revoke the token on GitHub Settings > Developer settings > Personal access tokens. Never commit tokens to source code.",
    ),
    Rule(
        id="SEC-004",
        pattern=r"""(?:glpat|glptt|glfbt|glsoat)-[A-Za-z0-9\-_]{20,}""",
        severity="critical", category="secret",
        title="GitLab Personal Access Token",
        description="GitLab PAT detected. Can access repos, CI/CD, and user data.",
        recommendation="Revoke at GitLab > User Settings > Access Tokens. Use CI/CD variables instead.",
    ),
    Rule(
        id="SEC-005",
        pattern=r"""(?:AKIA|ASIA)[A-Z0-9]{16}""",
        severity="critical", category="secret",
        title="AWS Access Key ID (AKIA/ASIA)",
        description="AWS access key ID starting with AKIA or ASIA detected.",
        recommendation="Rotate credentials immediately. Check CloudTrail for unauthorized access.",
    ),
    Rule(
        id="SEC-006",
        pattern=r"""['"]?sk[_-]?(?:live|test|pk)[_-][A-Za-z0-9]{20,}['"]?""",
        severity="critical", category="secret",
        title="Stripe API Key",
        description="Stripe secret API key detected. Can process payments and access financial data.",
        recommendation="Revoke in Stripe Dashboard > Developers > API keys. Use environment variables.",
    ),
    Rule(
        id="SEC-007",
        pattern=r"""(?:SG\.[A-Za-z0-9\-_]{22,}\.[A-Za-z0-9\-_]{43,})""",
        severity="critical", category="secret",
        title="SendGrid API Key",
        description="SendGrid API key detected. Can send emails and access contact lists.",
        recommendation="Revoke in SendGrid dashboard. Rotate and store securely.",
    ),
    Rule(
        id="SEC-008",
        pattern=r"""(?:xox[bpsa]-[0-9]{10,}-[A-Za-z0-9-]+)""",
        severity="critical", category="secret",
        title="Slack Token",
        description="Slack API token detected. Can access channels, messages, and workspace data.",
        recommendation="Revoke in Slack App settings. Regenerate tokens.",
    ),
    Rule(
        id="SEC-009",
        pattern=r"""['"]?(?:AIza[0-9A-Za-z\-_]{35})['"]?""",
        severity="high", category="secret",
        title="Google API Key",
        description="Google API key detected. May provide access to various Google services.",
        recommendation="Restrict the key in Google Cloud Console. Use service accounts instead.",
    ),
    Rule(
        id="SEC-010",
        pattern=r"""['"]?(?:[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com)['"]?""",
        severity="high", category="secret",
        title="Google OAuth Client ID",
        description="Google OAuth client ID detected. Can be used for phishing or OAuth attacks.",
        recommendation="Regenerate credentials in Google Cloud Console.",
    ),
    Rule(
        id="SEC-011",
        pattern=r"""(?:sk_live_[0-9a-zA-Z]{24,})""",
        severity="critical", category="secret",
        title="Stripe Live Secret Key",
        description="Stripe LIVE secret key detected — this is production!",
        recommendation="URGENT: Revoke immediately in Stripe Dashboard. Check for unauthorized charges.",
    ),
    Rule(
        id="SEC-012",
        pattern=r"""(?:sk_test_[0-9a-zA-Z]{24,})""",
        severity="medium", category="secret",
        title="Stripe Test Secret Key",
        description="Stripe test secret key detected. Lower risk but should still be rotated.",
        recommendation="Rotate the key and remove from source code.",
    ),
    Rule(
        id="SEC-013",
        pattern=r"""(?:sq0atp-[0-9A-Za-z\-_]{22})""",
        severity="critical", category="secret",
        title="Square Access Token",
        description="Square access token detected. Can access payment and business data.",
        recommendation="Revoke in Square Developer Dashboard.",
    ),
    Rule(
        id="SEC-014",
        pattern=r"""(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}""",
        severity="critical", category="secret",
        title="AWS Key ID Pattern",
        description="AWS key ID pattern detected. Verify if this is an active key.",
        recommendation="Check AWS IAM for active keys. Rotate if valid.",
    ),
    Rule(
        id="SEC-015",
        pattern=r"""-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----""",
        severity="critical", category="secret",
        title="Private Key in Source Code",
        description="A private cryptographic key is embedded in the source code.",
        recommendation="Remove immediately. Use a secrets manager or environment variable. Revoke the key.",
    ),
    Rule(
        id="SEC-016",
        pattern=r"""['"]?(?:sk|pk)_(?:test|live)_[A-Za-z0-9]{20,}['"]?""",
        severity="critical", category="secret",
        title="Payment Provider Key",
        description="Payment provider secret key detected.",
        recommendation="Revoke and rotate. Never commit payment keys to source control.",
    ),
    Rule(
        id="SEC-017",
        pattern=r"""(?:password|passwd|pwd)\s*[:=]\s*['"]([^\s'"]{6,})['"]""",
        severity="high", category="secret",
        title="Hardcoded Password",
        description="A hardcoded password was found in the source code.",
        recommendation="Move to environment variables or a secrets manager. Never hardcode passwords.",
    ),
    Rule(
        id="SEC-018",
        pattern=r"""(?:api[_-]?key|apikey)\s*[:=]\s*['"]([A-Za-z0-9\-_]{20,})['"]""",
        severity="high", category="secret",
        title="API Key in Source Code",
        description="An API key was found hardcoded in the source code.",
        recommendation="Move to environment variables. Rotate the key if it's a real credential.",
    ),
    Rule(
        id="SEC-019",
        pattern=r"""(?:token|auth_token|access_token|bearer)\s*[:=]\s*['"]([A-Za-z0-9\-_.]{20,})['"]""",
        severity="high", category="secret",
        title="Auth Token in Source Code",
        description="An authentication token was found hardcoded in the source code.",
        recommendation="Move to environment variables. Revoke and regenerate the token.",
    ),
    Rule(
        id="SEC-020",
        pattern=r"""(?:HEROKU_API_KEY|HEROKU_AUTH_TOKEN)\s*[:=]\s*['"]([A-Za-z0-9\-]{40,})['"]""",
        severity="critical", category="secret",
        title="Heroku API Key",
        description="Heroku API key detected. Can deploy, manage, and destroy apps.",
        recommendation="Revoke in Heroku Account Settings > API Key.",
    ),
    Rule(
        id="SEC-021",
        pattern=r"""(?:NPM_TOKEN|npm_token)\s*[:=]\s*['"]([A-Za-z0-9\-]{30,})['"]""",
        severity="critical", category="secret",
        title="NPM Access Token",
        description="NPM token detected. Can publish packages to npm registry.",
        recommendation="Revoke at npmjs.com > Access Tokens. Use environment variables.",
    ),
    Rule(
        id="SEC-022",
        pattern=r"""(?:TWILIO_AUTH_TOKEN|twilio_auth_token)\s*[:=]\s*['"]([A-Za-z0-9]{32})['"]""",
        severity="critical", category="secret",
        title="Twilio Auth Token",
        description="Twilio auth token detected. Can send SMS, make calls, and access account.",
        recommendation="Revoke in Twilio Console. Regenerate immediately.",
    ),
    Rule(
        id="SEC-023",
        pattern=r"""(?:MAILGUN_API_KEY|MAILGUN_SEND_KEY)\s*[:=]\s*['"]?(key-[A-Za-z0-9]{32})['"]?""",
        severity="critical", category="secret",
        title="Mailgun API Key",
        description="Mailgun API key detected. Can send emails and access logs.",
        recommendation="Revoke in Mailgun dashboard. Rotate keys.",
    ),
    Rule(
        id="SEC-024",
        pattern=r"""(?:OPENAI_API_KEY|openai_api_key)\s*[:=]\s*['"]?(sk-[A-Za-z0-9]{40,})['"]?""",
        severity="critical", category="secret",
        title="OpenAI API Key",
        description="OpenAI API key detected. Can make API calls billed to your account.",
        recommendation="Revoke at platform.openai.com > API Keys. Use environment variables.",
    ),
]

# ── CODE INJECTION / VULNERABILITIES ────────────────────────────────────────

CODE_RULES = [
    Rule(
        id="VUL-001",
        pattern=r"""(?:eval|exec)\s*\(\s*(?:request\.(?:args|form|values|json|data|params)|[^)]*(?:input|param|argv|user))""",
        severity="critical", category="injection",
        title="Code Injection via eval/exec",
        description="User-controlled input is passed to eval() or exec(). Allows arbitrary code execution.",
        recommendation="Never use eval/exec with user input. Use safe alternatives like ast.literal_eval().",
    ),
    Rule(
        id="VUL-002",
        pattern=r"""(?:os\.system|os\.popen|subprocess\.call|subprocess\.run|subprocess\.Popen)\s*\((?:f['"]|.*%s|.*\.format|.*\+\s*)""",
        severity="critical", category="injection",
        title="Command Injection",
        description="User input may be passed to a system command. Allows command injection.",
        recommendation="Use subprocess with shell=False. Pass arguments as a list. Sanitize input.",
    ),
    Rule(
        id="VUL-003",
        pattern=r"""(?:cursor\.execute|db\.execute)\s*\(\s*(?:f['"]|['"].*%s|['"].*\.format|.*\+\s*)""",
        severity="critical", category="injection",
        title="SQL Injection",
        description="String interpolation used in SQL query. Allows SQL injection attacks.",
        recommendation="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
    ),
    Rule(
        id="VUL-004",
        pattern=r"""(?:render_template_string|Markup|jinja2\.Template)\s*\((?:f['"]|.*%s|.*\.format|.*\+\s*request)""",
        severity="high", category="injection",
        title="Template Injection (SSTI)",
        description="User input passed to template rendering. May allow Server-Side Template Injection.",
        recommendation="Never pass user input to template strings. Use template files with auto-escaping.",
    ),
    Rule(
        id="VUL-005",
        pattern=r"""(?:pickle\.loads?|yaml\.load|yaml\.unsafe_load|marshal\.loads?)\s*\((?:request|[^)]*(?:user|input|data|param))""",
        severity="critical", category="injection",
        title="Unsafe Deserialization",
        description="Unsafe deserialization of user-controlled data. Can lead to remote code execution.",
        recommendation="Use yaml.safe_load() instead. Avoid pickle with untrusted data. Use JSON.",
    ),
    Rule(
        id="VUL-006",
        pattern=r"""(?:innerHTML|document\.write|\.html\(|dangerouslySetInnerHTML|v-html)""",
        severity="high", category="xss",
        title="Potential XSS Sink",
        description="DOM manipulation that may allow Cross-Site Scripting if user input is involved.",
        recommendation="Sanitize input. Use textContent instead of innerHTML. Use DOMPurify for HTML.",
    ),
    Rule(
        id="VUL-007",
        pattern=r"""(?:res\.send\(|response\.write|echo\s|print\s*\()""",
        severity="medium", category="xss",
        title="Unescaped Output",
        description="Data sent directly to response without encoding. May allow reflected XSS.",
        recommendation="HTML-encode all output. Use templating engine auto-escaping.",
    ),
    Rule(
        id="VUL-008",
        pattern=r"""(?:fetch|axios|XMLHttpRequest|\.ajax|http\.get|http\.post|requests\.get|requests\.post)\s*\((?:[^)]*(?:req\.(?:body|query|params)|user|input|param))""",
        severity="high", category="ssrf",
        title="Server-Side Request Forgery (SSRF)",
        description="User-controlled input used in server-side HTTP requests. Can access internal services.",
        recommendation="Validate and whitelist URLs. Use allowlists for internal IPs. Block metadata endpoints.",
    ),
    Rule(
        id="VUL-009",
        pattern=r"""redirect\s*\((?:[^)]*(?:request\.(?:args|form|params)|req\.query|user|param|location))""",
        severity="high", category="redirect",
        title="Open Redirect",
        description="User-controlled input used in redirect. Can redirect to malicious sites.",
        recommendation="Validate redirect targets against an allowlist. Use relative paths.",
    ),
    Rule(
        id="VUL-010",
        pattern=r"""(?:set_cookie|Set-Cookie).*?(?:[^;]*;\s*)?(?:[Ss]ecure\s*=\s*(?:false|0|no)|[Hh]ttply\s*=\s*(?:false|0|no))""",
        severity="medium", category="cookie",
        title="Insecure Cookie Configuration",
        description="Cookie set without Secure or HttpOnly flags.",
        recommendation="Always set Secure, HttpOnly, and SameSite flags on sensitive cookies.",
    ),
    Rule(
        id="VUL-011",
        pattern=r"""(?:DEBUG\s*=\s*True|debug\s*:\s*true|FLASK_DEBUG\s*=\s*1)""",
        severity="medium", category="config",
        title="Debug Mode Enabled",
        description="Debug mode is enabled. Exposes detailed error messages and may have performance issues.",
        recommendation="Disable debug mode in production. Use proper error handling and logging.",
    ),
    Rule(
        id="VUL-012",
        pattern=r"""(?:ALLOWED_HOSTS\s*=\s*\[.*\*|CORS\s*.*\*|Access-Control-Allow-Origin.*\*)""",
        severity="medium", category="config",
        title="Overly Permissive CORS/Hosts",
        description="Wildcard CORS or allowed hosts configuration. May allow unauthorized cross-origin requests.",
        recommendation="Restrict to specific trusted domains. Never use * in production.",
    ),
    Rule(
        id="VUL-013",
        pattern=r"""(?:verify\s*=\s*False|VERIFY_SSL\s*=\s*(?:False|0|no)|NODE_TLS_REJECT_UNAUTHORIZED\s*=?\s*['"]0['"])""",
        severity="medium", category="config",
        title="SSL Verification Disabled",
        description="SSL certificate verification is disabled. Vulnerable to MITM attacks.",
        recommendation="Enable SSL verification. Use proper certificate bundles.",
    ),
    Rule(
        id="VUL-014",
        pattern=r"""(?:chmod\s+777|chmod\s+\+x|0o777)""",
        severity="medium", category="config",
        title="Overly Permissive File Permissions",
        description="World-readable/writable file permissions detected.",
        recommendation="Use least-privilege permissions (644 for files, 755 for directories).",
    ),
    Rule(
        id="VUL-015",
        pattern=r"""(?:curl|wget|http\.get|requests\.get|fetch)\s*\((?:.*(?:169\.254\.169\.254|metadata\.google\.internal|100\.100\.100\.200|fd[0-9]+\.socket\.elb\.amazonaws))""",
        severity="critical", category="ssrf",
        title="Cloud Metadata SSRF",
        description="Request to cloud metadata endpoint. Can steal IAM credentials and secrets.",
        recommendation="Block access to metadata IPs. Use IMDSv2. Validate all URLs.",
    ),
    Rule(
        id="VUL-016",
        pattern=r"""(?:bcrypt|md5|sha1|sha256)\s*\(\s*(?:password|passwd|pwd|secret|token)""",
        severity="info", category="crypto",
        title="Weak Hashing Detected",
        description="Weak or deprecated hash algorithm used for sensitive data.",
        recommendation="Use bcrypt, scrypt, or argon2 for passwords. Use SHA-256+ for data hashing.",
    ),
    Rule(
        id="VUL-017",
        pattern=r"""(?:random\.random|random\.randint|random\.choice|Math\.random)\s*\(\s*\)""",
        severity="low", category="crypto",
        title="Weak Random Number Generator",
        description="Non-cryptographic PRNG used. Predictable output for security contexts.",
        recommendation="Use secrets module (Python) or crypto.randomBytes (Node.js) for security.",
    ),
    Rule(
        id="VUL-018",
        pattern=r"""(?:\.env|env\.|process\.env)\s*\.\s*(?:SECRET|KEY|TOKEN|PASSWORD|CREDENTIAL)""",
        severity="info", category="config",
        title="Secret Loaded from Environment",
        description="Secret loaded from environment — this is the CORRECT pattern but verify it's not logged.",
        recommendation="Ensure secrets are never logged or exposed in error messages.",
    ),
    Rule(
        id="VUL-019",
        pattern=r"""(?:TODO|FIXME|HACK|XXX|WORKAROUND).*(?:secur|auth|password|token|secret|vuln)""",
        severity="info", category="code_quality",
        title="Security-Related TODO/FIXME",
        description="A TODO or FIXME comment mentioning security. May indicate an unfinished fix.",
        recommendation="Address the TODO before production deployment.",
    ),
    Rule(
        id="VUL-020",
        pattern=r"""(?:\.git|\.svn|\.hg|\.bzr|CVS|\.DS_Store|Thumbs\.db)""",
        severity="low", category="config",
        title="Version Control / OS File in Source",
        description="Version control or OS metadata file detected in source code.",
        recommendation="Add to .gitignore and remove from tracking.",
    ),
]

ALL_RULES = SECRET_RULES + CODE_RULES


def get_rules_for_language(language: str) -> List[Rule]:
    """Get rules applicable to a specific language."""
    result = []
    for rule in ALL_RULES:
        if not rule.languages or language in rule.languages:
            result.append(rule)
    return result
