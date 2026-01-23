import importlib
import pkgutil
from pathlib import Path

from fastapi import APIRouter

# Базовый роутер для API v1
api_router = APIRouter()

# Путь к директории с модулями API
api_v1_path = Path(__file__).parent
package_name = "src.presentation.server.api.v1"


def _register_routers() -> None:
    for module_info in pkgutil.iter_modules([str(api_v1_path)]):
        if module_info.name == "router":
            continue

        module_name = f"{package_name}.{module_info.name}"
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "router"):
                api_router.include_router(module.router)
        except ImportError as e:
            print(f"Warning: Failed to import {module_name}: {e}")


_register_routers()
