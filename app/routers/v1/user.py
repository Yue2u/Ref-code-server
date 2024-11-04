import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi_users.authentication.authenticator import Authenticator
from fastapi_users.authentication.strategy import JWTStrategy
from fastapi_users.authentication.transport.bearer import BearerResponse
from fastapi_users.exceptions import UserNotExists

from app.core.auth.auth import (
    User,
    UserManager,
    auth_backend,
    auth_settings,
    current_verified_user,
    fastapi_users_app,
    get_jwt_refresh_strategy,
    get_jwt_strategy,
    get_user_manager,
)
from app.core.auth.auth_routers import get_auth_router, get_register_router
from app.core.auth.oauth2 import github_oauth_client, google_oauth_client
from app.core.auth.settings import settings as auth_settings
from app.ref_code_manager import ReferralCodeManager, get_ref_code_manager
from app.schemas.user import (
    ReferralCodeExpiraton,
    ReferralCodeRead,
    ReferralCodeReadWithExpire,
    ReferralCodeRequest,
    UserCreate,
    UserRead,
    UserReferrals,
    UserUpdate,
)

router = APIRouter()


router.include_router(
    get_auth_router(
        auth_backend,
        get_user_manager,
        Authenticator([auth_backend], get_user_manager),
        get_jwt_refresh_strategy,
    ),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    get_register_router(get_user_manager, UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users_app.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users_app.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users_app.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
router.include_router(
    fastapi_users_app.get_oauth_router(
        google_oauth_client,
        auth_backend,
        auth_settings.OAUTH_GOOGLE_SECRET,
        associate_by_email=True,
    ),
    prefix="/auth/google",
    tags=["auth"],
)
router.include_router(
    fastapi_users_app.get_oauth_associate_router(
        google_oauth_client, UserRead, auth_settings.OAUTH_GOOGLE_SECRET
    ),
    prefix="/auth/associate/google",
    tags=["auth"],
)
router.include_router(
    fastapi_users_app.get_oauth_router(
        github_oauth_client,
        auth_backend,
        auth_settings.OAUTH_GITHUB_SECRET,
        associate_by_email=True,
    ),
    prefix="/auth/github",
    tags=["auth"],
)
router.include_router(
    fastapi_users_app.get_oauth_associate_router(
        github_oauth_client, UserRead, auth_settings.OAUTH_GITHUB_SECRET
    ),
    prefix="/auth/associate/github",
    tags=["auth"],
)


@router.post("/auth/refresh", tags=["auth"], response_model=BearerResponse)
async def refresh_token(
    strategy: Annotated[JWTStrategy, Depends(get_jwt_strategy)],
    refresh_strategy: Annotated[JWTStrategy, Depends(get_jwt_refresh_strategy)],
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not provided.")

    user = await refresh_strategy.read_token(refresh_token, user_manager)
    if not user:
        raise HTTPException(status_code=401, detail="Refresh token expired.")

    new_refresh_token = await refresh_strategy.write_token(user)

    response = await auth_backend.login(strategy, user)
    response.set_cookie(
        "refresh_token",
        new_refresh_token,
        httponly=True,
        domain=auth_settings.COOKIE_DOMAIN,
        secure=True,
    )


@router.get("/users/me/referrals", tags=["users"], response_model=UserReferrals)
async def get_my_referrals(
    user: Annotated[User, Depends(current_verified_user)],
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
):
    return UserReferrals(referrals=await user_manager.get_referrals(user.id))


@router.post("/users/referrals/{user_id}", tags=["users"], response_model=UserReferrals)
async def get_user_referrals(
    user_manager: Annotated[UserManager, Depends(get_user_manager)], user_id: uuid.UUID
):
    try:
        user = await user_manager.get(user_id)
    except UserNotExists:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserReferrals(referrals=await user_manager.get_referrals(user.id))


@router.post("/users/referral_code", tags=["users"], response_model=ReferralCodeRead)
async def get_token_by_user_email(
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
    ref_code_manager: Annotated[ReferralCodeManager, Depends(get_ref_code_manager)],
    request: ReferralCodeRequest,
):
    user: User = await user_manager.get_by_email(request.email)
    print(user)
    if user is None:
        raise UserNotExists()

    ref_code = await ref_code_manager.retrieve_code(user.id)
    if ref_code is None:
        raise HTTPException(
            status_code=404, detail="User has no active referral codes."
        )

    return ReferralCodeRead(referral_code=ref_code)


@router.get(
    "/users/me/referral_code", response_model=ReferralCodeReadWithExpire, tags=["users"]
)
async def get_my_referral_code(
    user: Annotated[User, Depends(current_verified_user)],
    ref_code_manager: Annotated[ReferralCodeManager, Depends(get_ref_code_manager)],
):
    ref_code = await ref_code_manager.retrieve_code(user.id)

    if ref_code is None:
        raise HTTPException(
            status_code=400, detail="You don't have any active referral codes."
        )

    ttl = await ref_code_manager.retrieve_ttl_by_user_id(user.id)

    return ReferralCodeReadWithExpire(referral_code=ref_code, expires_in=ttl)


@router.post(
    "/users/me/referral_code", response_model=ReferralCodeReadWithExpire, tags=["users"]
)
async def create_new_code(
    user: Annotated[User, Depends(current_verified_user)],
    ref_code_manager: Annotated[ReferralCodeManager, Depends(get_ref_code_manager)],
    ttl: ReferralCodeExpiraton,
):
    new_ref_code = await ref_code_manager.create(user.id, ttl.expires_in_seconds)

    if new_ref_code is None:
        prev_ref_code = await ref_code_manager.retrieve_code(user.id)
        prev_ttl = await ref_code_manager.retrieve_ttl_by_user_id(user.id)
        raise HTTPException(
            status_code=400,
            detail=f"You already have referral code {prev_ref_code}, that expires in {prev_ttl} seconds",
        )

    return ReferralCodeReadWithExpire(
        referral_code=new_ref_code, expires_in=ttl.expires_in_seconds
    )


@router.delete(
    "/users/me/referral_code",
    tags=["users"],
)
async def delete_referral_code(
    user: Annotated[User, Depends(current_verified_user)],
    ref_code_manager: Annotated[ReferralCodeManager, Depends(get_ref_code_manager)],
):
    is_deleted = await ref_code_manager.delete(user.id)
    if not is_deleted:
        raise HTTPException(
            status_code=400, detail="You don't have any active referral codes."
        )

    return Response(status_code=204)
