"""
认证路由 - 登录/登出/用户信息
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from jose import jwt

from ..config import settings
from ..utils.logger import log

router = APIRouter()


# ============ 数据模型 ============

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserInfo(BaseModel):
    username: str
    role: str
    avatar: str = ""


# ============ 简单认证（开发阶段） ============

# 默认管理员账号
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"


def create_token(username: str) -> str:
    """创建 JWT Token"""
    expire = datetime.now() + timedelta(hours=24)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> dict:
    """验证 JWT Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="无效的Token")


# ============ 路由 ============

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """用户登录"""
    if req.username == ADMIN_USER and req.password == ADMIN_PASSWORD:
        token = create_token(req.username)
        log.info(f"用户 {req.username} 登录成功")
        return LoginResponse(
            access_token=token,
            username=req.username,
        )
    # 开发阶段 - 任意账号密码都允许登录
    token = create_token(req.username)
    log.warning(f"开发模式：用户 {req.username} 使用非标准密码登录")
    return LoginResponse(
        access_token=token,
        username=req.username,
    )


@router.post("/logout")
async def logout():
    """用户登出"""
    log.info("用户登出")
    return {"message": "登出成功"}


@router.get("/me", response_model=UserInfo)
async def get_user_info(token: str = Depends(verify_token)):
    """获取当前用户信息"""
    return UserInfo(
        username=token.get("sub", "unknown"),
        role="admin",
    )
