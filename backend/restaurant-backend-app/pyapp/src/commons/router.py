"""APIGRR-based HTTP router adapter for the API handler."""

from __future__ import annotations

import inspect
import json
import re
from collections.abc import Callable

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
from aws_lambda_powertools.event_handler.exceptions import NotFoundError
from enums.http_status_code import HttpStatusCode

from commons.response import LambdaResponse

RouteHandler = Callable[..., LambdaResponse]


class Router:
    """Small adapter around APIGatewayRestResolver with existing handler contracts."""

    _TEMPLATE_PARAM_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

    def __init__(self) -> None:
        """Wrap APIGatewayRestResolver to adapt to existing handler contracts and response model."""
        self._app = APIGatewayRestResolver()
        self._register_not_found_handler()

    def add(self, method: str, template: str, handler: RouteHandler) -> None:
        """Register an API route and dispatch to the provided handler."""
        normalized_method = method.upper()
        normalized_template = self._convert_template(template)

        # podrzava pozivanje handlera sa event dict-om ili bez
        handler_parameters = inspect.signature(handler).parameters
        expects_event = len(handler_parameters) > 0

        @self._app.route(normalized_template, method=[normalized_method])
        def _route_handler(**path_parameters: str):
            event = dict(self._app.current_event.raw_event)
            resolved_path_parameters = self._app.current_event.path_parameters or {}
            existing_path_parameters = event.get("pathParameters") or {}
            event["pathParameters"] = {
                **path_parameters,
                **resolved_path_parameters,
                **existing_path_parameters,
            }

            response = handler(event) if expects_event else handler()
            headers = dict(response.headers)
            content_type = headers.pop("Content-Type", "application/json")

            return Response(
                status_code=response.statusCode,
                content_type=content_type,
                headers=headers,
                body=response.body,
            )

    def dispatch(self, event: dict, context: object) -> LambdaResponse:
        """Resolve request via APIGRR and return existing LambdaResponse model."""
        resolved = self._app.resolve(event, context)
        return LambdaResponse.model_validate(resolved)

    @classmethod
    def _convert_template(cls, template: str) -> str:
        """Convert /path/{id} templates to APIGRR /path/<id> syntax."""
        return cls._TEMPLATE_PARAM_PATTERN.sub(r"<\1>", template)

    def _register_not_found_handler(self) -> None:
        """Keep not-found response payload compatible with existing behavior."""

        @self._app.not_found
        def _not_found(_: NotFoundError):
            return Response(
                status_code=HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                content_type="application/json",
                body=json.dumps({"message": "Route not found"}),
            )
