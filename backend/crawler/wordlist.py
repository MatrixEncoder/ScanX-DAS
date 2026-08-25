"""
wordlist.py — Common hidden paths and sensitive file wordlist for endpoint discovery.
"""

# Common sensitive paths to probe during crawling
SENSITIVE_PATHS = [
    # Config files
    "/.env",
    "/.env.local",
    "/.env.production",
    "/config.php",
    "/config.json",
    "/config.yml",
    "/config.yaml",
    "/configuration.php",
    "/settings.json",
    "/settings.php",
    "/web.config",
    "/appsettings.json",
    "/application.properties",
    "/.htaccess",
    "/.htpasswd",

    # Git
    "/.git/config",
    "/.git/HEAD",
    "/.gitignore",

    # Backup files
    "/backup.sql",
    "/backup.zip",
    "/backup.tar.gz",
    "/db.sql",
    "/database.sql",
    "/dump.sql",
    "/index.php.bak",
    "/index.php~",
    "/index.php.swp",

    # Admin panels
    "/admin",
    "/admin/",
    "/admin/login",
    "/administrator",
    "/wp-admin",
    "/wp-admin/",
    "/phpmyadmin",
    "/phpmyadmin/",
    "/cpanel",
    "/manager",

    # API endpoints
    "/api",
    "/api/",
    "/api/v1",
    "/api/v1/",
    "/api/v2",
    "/api/v2/",
    "/api/docs",
    "/api/swagger",
    "/swagger-ui.html",
    "/swagger.json",
    "/openapi.json",
    "/graphql",

    # Debug / Info
    "/phpinfo.php",
    "/info.php",
    "/test.php",
    "/debug",
    "/debug/",
    "/server-status",
    "/server-info",
    "/elmah.axd",
    "/trace.axd",

    # Common paths
    "/robots.txt",
    "/sitemap.xml",
    "/crossdomain.xml",
    "/clientaccesspolicy.xml",
    "/favicon.ico",
    "/.well-known/security.txt",
    "/.well-known/apple-app-site-association",

    # Logs
    "/logs/",
    "/log/",
    "/error.log",
    "/access.log",
    "/debug.log",

    # Misc
    "/.DS_Store",
    "/Thumbs.db",
    "/WEB-INF/web.xml",
    "/META-INF/MANIFEST.MF",
    "/CONSOLE",
    "/jolokia",
    "/actuator",
    "/actuator/env",
    "/actuator/health",
    "/metrics",
    "/health",
    "/status",
]
