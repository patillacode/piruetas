from starlette.requests import Request

MONTH_NAMES: dict[str, list[str]] = {
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
    "es": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
           "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"],
}

WEEKDAY_NAMES: dict[str, list[str]] = {
    # Python weekday(): 0=Monday … 6=Sunday
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "es": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "sign_in": "Sign in",
        "sign_out": "Sign out",
        "account": "Account",
        "publish": "Publish",
        "unpublish": "Unpublish",
        "copy_link": "Copy link",
        "link": "Link",
        "undo": "Undo",
        "redo": "Redo",
        "image": "Image",
        "share": "Share",
        "copy_btn": "Copy",
        "copied": "Copied!",
        "write_anything": "Write anything...",
        "word": "word",
        "words": "words",
        "saved": "Saved",
        "error_saving": "Error saving",
        "username": "Username",
        "password": "Password",
        "new_password": "New password",
        "new_user": "New user",
        "create_user": "Create user",
        "users": "Users",
        "role": "Role",
        "joined": "Joined",
        "actions": "Actions",
        "reset_pw": "Reset pw",
        "delete": "Delete",
        "save": "Save",
        "written_with": "Written with Piruetas",
        "more_entries": "More entries",
        "admin_back": "← Admin",
        "change_password": "Change password",
        "current_password": "Current password",
        "confirm_password": "Confirm new password",
        "update_password": "Update password",
        "admin_role": "admin",
        "user_role": "user",
        "stop_sharing": "Stop sharing",
        "delete_confirm": "Delete {name}? This cannot be undone.",
        "delete_entry": "Delete entry",
        "delete_entry_confirm": "This will permanently delete this entry and cannot be undone.",
        "delete_entry_published": "This entry is currently published — deleting it will also remove the public link.",
        "cancel": "Cancel",
    },
    "es": {
        "sign_in": "Entrar",
        "sign_out": "Salir",
        "account": "Cuenta",
        "publish": "Publicar",
        "unpublish": "Despublicar",
        "copy_link": "Copiar enlace",
        "link": "Enlace",
        "undo": "Deshacer",
        "redo": "Rehacer",
        "image": "Imagen",
        "share": "Compartir",
        "copy_btn": "Copiar",
        "copied": "¡Copiado!",
        "write_anything": "Escribe algo...",
        "word": "palabra",
        "words": "palabras",
        "saved": "Guardado",
        "error_saving": "Error al guardar",
        "username": "Usuario",
        "password": "Contraseña",
        "new_password": "Nueva contraseña",
        "new_user": "Nuevo usuario",
        "create_user": "Crear usuario",
        "users": "Usuarios",
        "role": "Rol",
        "joined": "Registro",
        "actions": "Acciones",
        "reset_pw": "Cambiar contraseña",
        "delete": "Eliminar",
        "save": "Guardar",
        "written_with": "Escrito con Piruetas",
        "more_entries": "Más entradas",
        "admin_back": "← Admin",
        "change_password": "Cambiar contraseña",
        "current_password": "Contraseña actual",
        "confirm_password": "Confirmar nueva contraseña",
        "update_password": "Actualizar contraseña",
        "admin_role": "admin",
        "user_role": "usuario",
        "stop_sharing": "Dejar de compartir",
        "delete_confirm": "¿Eliminar {name}? Esta acción no se puede deshacer.",
        "delete_entry": "Eliminar entrada",
        "delete_entry_confirm": "Esta acción eliminará permanentemente esta entrada y no se puede deshacer.",
        "delete_entry_published": "Esta entrada está publicada — eliminarla también eliminará el enlace público.",
        "cancel": "Cancelar",
    },
}


def get_locale(request: Request) -> str:
    return request.cookies.get("piruetas_locale", "en")


def get_t(request: Request) -> dict[str, str]:
    return TRANSLATIONS.get(get_locale(request), TRANSLATIONS["en"])


def get_month_names(locale: str) -> list[str]:
    return MONTH_NAMES.get(locale, MONTH_NAMES["en"])


def get_weekday_names(locale: str) -> list[str]:
    return WEEKDAY_NAMES.get(locale, WEEKDAY_NAMES["en"])
