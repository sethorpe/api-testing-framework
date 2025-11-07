import base64

import httpx

TOKEN_URL = "https://accounts.spotify.com/api/token"


def fetch_spotify_token(client_id: str, client_secret: str) -> tuple[str, int]:
    """
    Returns (access_token, expires_in_seconds)
    """
    client_id = client_id.strip()
    client_secret = client_secret.strip()
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode("ascii")).decode()
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}
    json = True
    resp = httpx.post(TOKEN_URL, data=data, headers=headers, json=json)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError:
        try:
            err = resp.json()
        except ValueError:
            err = resp.text
        raise RuntimeError(f"Spotify token fetch failed ({resp.status_code}): {err!r}")
    body = resp.json()
    return body["access_token"], body["expires_in"]
