from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.clients.github import GitHubOAuth2

from .settings import settings as auth_settins


google_oauth_client = GoogleOAuth2(
    auth_settins.OAUTH_GOOGLE_CLIENT_ID,
    auth_settins.OAUTH_GOOGLE_CLIENT_SECRET
)

github_oauth_client = GitHubOAuth2(
    auth_settins.OAUTH_GITHUB_CLIENT_ID,
    auth_settins.OAUTH_GITHUB_CLIENT_SECRET
)

