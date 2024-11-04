from typing import Annotated, Tuple, Type

from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import exceptions, models, schemas
from fastapi_users.authentication import AuthenticationBackend, Authenticator, Strategy
from fastapi_users.authentication.strategy import StrategyDestroyNotSupportedError
from fastapi_users.manager import BaseUserManager, UserManagerDependency
from fastapi_users.openapi import OpenAPIResponseType
from fastapi_users.router.common import ErrorCode, ErrorModel
from fastapi_users.types import DependencyCallable

from app.ref_code_manager import ReferralCodeManager, get_ref_code_manager

from .settings import settings as auth_settings


def get_auth_router(
    backend: AuthenticationBackend,
    get_user_manager: UserManagerDependency[models.UP, models.ID],
    authenticator: Authenticator,
    get_refresh_strategy: DependencyCallable[Strategy[models.UP, models.ID]],
    requires_verification: bool = False,
) -> APIRouter:
    """Generate a router with login/logout routes for an authentication backend."""
    router = APIRouter()
    get_current_user_token = authenticator.current_user_token(
        active=True, verified=requires_verification
    )

    login_responses: OpenAPIResponseType = {
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorModel,
            "content": {
                "application/json": {
                    "examples": {
                        ErrorCode.LOGIN_BAD_CREDENTIALS: {
                            "summary": "Bad credentials or the user is inactive.",
                            "value": {"detail": ErrorCode.LOGIN_BAD_CREDENTIALS},
                        },
                        ErrorCode.LOGIN_USER_NOT_VERIFIED: {
                            "summary": "The user is not verified.",
                            "value": {"detail": ErrorCode.LOGIN_USER_NOT_VERIFIED},
                        },
                    }
                }
            },
        },
        **backend.transport.get_openapi_login_responses_success(),
    }

    @router.post(
        "/login",
        name=f"auth:{backend.name}.login",
        responses=login_responses,
    )
    async def login(
        request: Request,
        credentials: Annotated[OAuth2PasswordRequestForm, Depends()],
        user_manager: Annotated[
            BaseUserManager[models.UP, models.ID], Depends(get_user_manager)
        ],
        strategy: Annotated[
            Strategy[models.UP, models.ID], Depends(backend.get_strategy)
        ],
        refresh_strategy: Annotated[
            Strategy[models.UP, models.ID], Depends(get_refresh_strategy)
        ],
    ):
        user = await user_manager.authenticate(credentials)

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
            )
        if requires_verification and not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_USER_NOT_VERIFIED,
            )
        response = await backend.login(strategy, user)

        refresh_token = await refresh_strategy.write_token(user)
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            domain=auth_settings.COOKIE_DOMAIN,
            secure=True,
        )

        await user_manager.on_after_login(user, request, response)
        return response

    logout_responses: OpenAPIResponseType = {
        **{
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Missing token or inactive user."
            }
        },
        **backend.transport.get_openapi_logout_responses_success(),
    }

    @router.post(
        "/logout", name=f"auth:{backend.name}.logout", responses=logout_responses
    )
    async def logout(
        user_token: Annotated[Tuple[models.UP, str], Depends(get_current_user_token)],
        strategy: Annotated[
            Strategy[models.UP, models.ID], Depends(backend.get_strategy)
        ],
        refresh_strategy: Annotated[
            Strategy[models.UP, models.ID], Depends(get_refresh_strategy)
        ],
        refresh_token: Annotated[str | None, Cookie()] = None,
    ):
        user, token = user_token
        if refresh_token:
            try:
                await refresh_strategy.destroy_token(refresh_token, user)
            except StrategyDestroyNotSupportedError:
                pass
        response = await backend.logout(strategy, user, token)
        response.delete_cookie(
            "refresh_token",
            httponly=True,
            secure=True,
            domain=auth_settings.COOKIE_DOMAIN,
        )
        return response

    return router


def get_register_router(
    get_user_manager: UserManagerDependency[models.UP, models.ID],
    user_schema: Type[schemas.U],
    user_create_schema: Type[schemas.UC],
) -> APIRouter:
    """Generate a router with the register route."""
    router = APIRouter()

    @router.post(
        "/register",
        response_model=user_schema,
        status_code=status.HTTP_201_CREATED,
        name="register:register",
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "model": ErrorModel,
                "content": {
                    "application/json": {
                        "examples": {
                            ErrorCode.REGISTER_USER_ALREADY_EXISTS: {
                                "summary": "A user with this email already exists.",
                                "value": {
                                    "detail": ErrorCode.REGISTER_USER_ALREADY_EXISTS
                                },
                            },
                            ErrorCode.REGISTER_INVALID_PASSWORD: {
                                "summary": "Password validation failed.",
                                "value": {
                                    "detail": {
                                        "code": ErrorCode.REGISTER_INVALID_PASSWORD,
                                        "reason": "Password should be"
                                        "at least 3 characters",
                                    }
                                },
                            },
                        }
                    }
                },
            },
        },
    )
    async def register(
        request: Request,
        ref_code_manager: Annotated[ReferralCodeManager, Depends(get_ref_code_manager)],
        user_manager: Annotated[
            BaseUserManager[models.UP, models.ID], Depends(get_user_manager)
        ],
        user_create: user_create_schema,  # type: ignore
        referral_code: Annotated[str | None, Body()] = None,
    ):
        try:
            if referral_code is not None:
                referrer_doesnt_exist = HTTPException(
                    status_code=400,
                    detail="User with this referral code doesn't exist.",
                )
                referrer_id = await ref_code_manager.retieve_user_id_by_code(
                    referral_code
                )
                if referrer_id is None:
                    raise referrer_doesnt_exist
                try:
                    referrer = await user_manager.get(referrer_id)
                except exceptions.UserNotExists:
                    raise referrer_doesnt_exist

            created_user = await user_manager.create(
                user_create, safe=True, request=request
            )
            if referral_code is not None:
                created_user = await user_manager._update(
                    created_user, {"referrer_id": referrer.id}
                )
        except exceptions.UserAlreadyExists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.REGISTER_USER_ALREADY_EXISTS,
            )
        except exceptions.InvalidPasswordException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": ErrorCode.REGISTER_INVALID_PASSWORD,
                    "reason": e.reason,
                },
            )

        return schemas.model_validate(user_schema, created_user)

    return router
