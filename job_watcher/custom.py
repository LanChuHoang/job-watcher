import json
from typing import Any, Dict, Optional, Union
from urllib.parse import urlencode

from scrapy import Request
from scrapy.http import FormRequest


class WrappedRequest(Request):
    """
    A wrapper around scrapy.Request to support:
      - `params`: dict of query parameters to append to the URL
      - `body`: dict or str to send in the request body
        - If `Content-Type` is 'application/json', `body` is serialized as JSON
        - If `Content-Type` is 'application/x-www-form-urlencoded', `body` is form-encoded
        - Otherwise, `body` is sent as-is
    """

    def __init__(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Union[Dict[str, Any], str, bytes]] = None,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        # Initialize headers if not provided
        headers = headers or {}

        # Handle query parameters
        if params:
            qs = urlencode(params, doseq=True)
            url = f"{url}?{qs}"

        # Determine Content-Type
        content_type = headers.get("Content-Type", "").lower()

        # Handle request body based on Content-Type
        if body is not None:
            if isinstance(body, dict):
                if content_type == "application/json":
                    body_bytes = json.dumps(body).encode("utf-8")
                elif content_type == "application/x-www-form-urlencoded":
                    # Use FormRequest for form-encoded data
                    form_request = FormRequest(
                        url=url,
                        method=method,
                        formdata=body,
                        headers=headers,
                        **kwargs,
                    )
                    # Copy attributes from FormRequest to self
                    self.__dict__.update(form_request.__dict__)
                    return
                else:
                    raise ValueError(
                        f"Unsupported Content-Type for dict body: {content_type}"
                    )
            elif isinstance(body, (str, bytes)):
                body_bytes = body.encode("utf-8") if isinstance(body, str) else body
            else:
                raise TypeError("body must be a dict, str, or bytes")

            # Set the body and initialize the Request
            super().__init__(
                url, method=method, headers=headers, body=body_bytes, **kwargs
            )
        else:
            # No body provided; proceed with standard Request
            super().__init__(url, method=method, headers=headers, **kwargs)
