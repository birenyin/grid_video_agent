from __future__ import annotations

import json
from collections import OrderedDict
from urllib.parse import parse_qsl, urlparse

from volcengine.Credentials import Credentials
from volcengine.auth.SignerV4 import SignerV4
from volcengine.base.Request import Request


def build_signed_headers(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict | list | str | None,
    ak: str,
    sk: str,
    service: str,
    region: str,
    session_token: str = "",
) -> dict[str, str]:
    parsed = urlparse(url)
    request = Request()
    request.set_schema(parsed.scheme or "https")
    request.set_method(method.upper())
    request.set_host(parsed.netloc)
    request.set_path(parsed.path or "/")
    request.set_query(OrderedDict(parse_qsl(parsed.query, keep_blank_values=True)))
    request.set_headers(OrderedDict((key, value) for key, value in headers.items()))
    if body is None:
        request.set_body("")
    elif isinstance(body, (dict, list)):
        request.set_body(json.dumps(body, ensure_ascii=False, separators=(",", ":")))
    else:
        request.set_body(str(body))

    credentials = Credentials(ak, sk, service, region, session_token)
    SignerV4.sign(request, credentials)
    return dict(request.headers)


def format_task_url(url_template: str, task_id: str) -> str:
    return url_template.replace("{task_id}", task_id).replace("{id}", task_id)


def is_seedance_operator_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.endswith(".volces.com") and "/api/v1/contents/generations/tasks" in parsed.path
