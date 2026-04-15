"""Scenario seed templates and expansion logic."""

from __future__ import annotations

import random
from typing import Any

SCENARIO_TEMPLATES: dict[str, dict[str, Any]] = {
    "database_outage": {
        "type": "database_outage",
        "description": "Primary database node becomes unresponsive",
        "environment": "production",
        "hints": {
            "system": "PostgreSQL primary in AWS RDS",
            "symptoms": "connection timeouts, 503 errors from API",
            "likely_causes": ["disk full", "lock contention", "memory exhaustion", "failover needed"],
        },
    },
    "ddos_attack": {
        "type": "ddos_attack",
        "description": "Volumetric DDoS attack targeting the web layer",
        "environment": "production",
        "hints": {
            "system": "Public-facing web tier (CDN + load balancers)",
            "symptoms": "extreme latency, packet loss, CDN edge saturation",
            "likely_causes": ["L3/L4 flood", "L7 HTTP flood", "DNS amplification"],
        },
    },
    "cert_expiry": {
        "type": "cert_expiry",
        "description": "TLS certificate expires causing widespread HTTPS failures",
        "environment": "production",
        "hints": {
            "system": "API gateway / load balancer certificates",
            "symptoms": "SSL handshake errors, mobile app crashes, partner API failures",
            "likely_causes": ["auto-renewal failure", "cert not deployed", "wrong domain"],
        },
    },
    "deployment_regression": {
        "type": "deployment_regression",
        "description": "Recent code deployment introduces a critical regression",
        "environment": "production",
        "hints": {
            "system": "Microservices (payment service)",
            "symptoms": "payment failures, increased error rate, revenue impact",
            "likely_causes": ["config change", "dependency version", "null pointer", "race condition"],
        },
    },
    "third_party_api_failure": {
        "type": "third_party_api_failure",
        "description": "Critical third-party dependency becomes unavailable",
        "environment": "production",
        "hints": {
            "system": "Stripe payment processing / SendGrid email / Twilio SMS",
            "symptoms": "timeouts to external service, downstream feature failures",
            "likely_causes": ["vendor outage", "API key revoked", "rate limit", "endpoint change"],
        },
    },
}

SCENARIO_TYPES = list(SCENARIO_TEMPLATES.keys())


def pick_scenario_type(requested: str | None) -> str:
    """Return the requested type, or pick randomly."""
    if requested and requested in SCENARIO_TEMPLATES:
        return requested
    return random.choice(SCENARIO_TYPES)


def get_template(scenario_type: str) -> dict[str, Any]:
    return SCENARIO_TEMPLATES[scenario_type]
