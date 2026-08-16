from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str
    must_change_password: bool = False


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    full_name: str
    email: str | None = None
    password: str
    role_name: str


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: str | None = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    barber_id: int | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class MasterCodeSetRequest(BaseModel):
    current_password: str
    master_code: str


class RecoverPasswordRequest(BaseModel):
    username: str
    master_code: str
    new_password: str
