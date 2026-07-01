from ninja import Router
from ninja.errors import HttpError
from django.contrib.auth.hashers import make_password, check_password
from lms.models import User
from lms.schemas import (
    RegisterSchema, LoginSchema, TokenSchema, RefreshSchema,
    UserProfileSchema, UserUpdateSchema, MessageSchema
)
from lms.auth import (
    JWTAuth, create_access_token, create_refresh_token, decode_token
)
from lms.mongo import log_activity

router = Router(tags=["Auth"])

@router.post("/register", response={201: MessageSchema})
def register(request, payload: RegisterSchema):
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(400, "Username already exists")
    if User.objects.filter(email=payload.email).exists():
        raise HttpError(400, "Email already exists")
        
    user = User.objects.create(
        username=payload.username,
        email=payload.email,
        password=make_password(payload.password),
        role=payload.role
    )
    
    log_activity(
        user=user,
        action="REGISTER",
        resource_type="user",
        resource_id=user.id,
        metadata={"role": user.role},
        request=request
    )
    return 201, {"message": "User registered successfully"}


@router.post("/login", response=TokenSchema)
def login(request, payload: LoginSchema):
    try:
        user = User.objects.get(username=payload.username)
    except User.DoesNotExist:
        raise HttpError(401, "Invalid username or password")

    if not check_password(payload.password, user.password):
        raise HttpError(401, "Invalid username or password")

    log_activity(
        user=user,
        action="LOGIN",
        resource_type="user",
        resource_id=user.id,
        request=request
    )

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


@router.post("/refresh", response=TokenSchema)
def refresh(request, payload: RefreshSchema):
    token_payload = decode_token(payload.refresh_token)
    if token_payload.get("type") != "refresh":
        raise HttpError(401, "Invalid token type")
        
    try:
        user = User.objects.get(id=token_payload.get("user_id"))
    except User.DoesNotExist:
        raise HttpError(401, "User not found")

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


@router.get("/me", response=UserProfileSchema, auth=JWTAuth())
def get_me(request):
    return request.auth


@router.put("/me", response=UserProfileSchema, auth=JWTAuth())
def update_me(request, payload: UserUpdateSchema):
    user = request.auth
    if payload.email is not None:
        user.email = payload.email
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    user.save()
    return user
