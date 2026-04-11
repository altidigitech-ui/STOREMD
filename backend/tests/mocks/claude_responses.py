"""Mock Claude API responses for testing."""

MOCK_ANALYSIS_RESPONSE = """{
    "score": 67,
    "mobile_score": 52,
    "desktop_score": 81,
    "trend": "up",
    "summary": "Your store health has improved. 3 issues remain.",
    "top_issues": [
        {
            "title": "App Privy injects 340KB of unminified JS",
            "severity": "critical",
            "impact": "+1.8s load time",
            "impact_value": 1.8,
            "impact_unit": "seconds",
            "scanner": "app_impact",
            "recommendation": "Replace Privy with a lighter alternative",
            "fix_type": "manual",
            "alternative": null
        }
    ]
}"""

MOCK_FIX_RESPONSE = """{
    "fix_description": "Remove the residual code left by the uninstalled app",
    "fix_type": "one_click",
    "estimated_impact": "Save 0.6 seconds of load time",
    "steps": null,
    "auto_fixable": true
}"""
