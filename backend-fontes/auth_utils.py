from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

SECRET_KEY = "segredo-teste"
ALGORITHM = "HS256"

def get_current_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
