from fastapi import APIRouter

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.get("/secure-test")
def secure_test():
    return {
        "message": "secure route"
    }