"""Extract matchCentreData from WhoScored match page HTML."""

import json
import re


def extract_match_centre_data(html: str) -> dict:
    """Extract matchCentreData from WhoScored match page HTML.

    WhoScored embeds match data in a script block as:
        require.config.params["args"] = {..., "matchCentreData": {...}, ...};
    """
    match = re.search(r'require\.config\.params\["args"\]\s*=\s*', html)
    if not match:
        raise ValueError(
            'Could not find require.config.params["args"] in page HTML. '
            "The page may not have loaded correctly, or WhoScored changed its structure."
        )

    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(html, match.end())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse args JSON at offset {match.end()}: {exc}") from exc

    if "matchCentreData" not in data:
        raise ValueError(
            f"matchCentreData key not found in args. Present keys: {list(data.keys())}"
        )

    return data["matchCentreData"]
