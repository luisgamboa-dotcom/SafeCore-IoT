"""Admin users routes (/admin/users)."""
from fastapi import APIRouter

import controllers.usersController as usersController

admin_router = APIRouter(prefix="/admin", tags=["admin"])


admin_router.get("/users")(usersController.showUsersPage)
admin_router.get("/users/{id_user}/edit")(usersController.showEditUserForm)
admin_router.post("/users/{id_user}/edit")(usersController.updateUserFromAdmin)
