from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field

from src.container import Container
from src.domain.models.product import Product
from src.infrastructure.db.repositories.exceptions import NotFound

router = APIRouter(tags=["Products"], prefix="/products")


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=255, description="Название продукта")
    description: Optional[str] = Field(None, description="Описание продукта")


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="Название продукта")
    description: Optional[str] = Field(None, description="Описание продукта")


class ProductWithReviewsCount(BaseModel):
    product: Product
    reviews_count: int


class ProductCreateResponse(BaseModel):
    id: UUID


@router.get(
    "/",
    response_model=List[ProductWithReviewsCount],
    summary="Список продуктов",
    description="Возвращает список продуктов с количеством отзывов",
)
async def list_products(
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество"),
    offset: int = Query(0, ge=0, description="Смещение"),
) -> List[ProductWithReviewsCount]:
    app = Container.product_application()
    products_with_counts = await app.list_with_reviews_count(limit=limit, offset=offset)
    return [
        ProductWithReviewsCount(product=p, reviews_count=count)
        for p, count in products_with_counts
    ]


@router.get(
    "/{product_id}",
    response_model=Product,
    summary="Получить продукт",
    description="Возвращает продукт по ID",
)
async def get_product(
    product_id: UUID = Path(..., description="UUID продукта"),
) -> Product:
    app = Container.product_application()
    try:
        return await app.get(product_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Продукт не найден")


@router.post(
    "/",
    response_model=ProductCreateResponse,
    status_code=201,
    summary="Создать продукт",
    description="Создаёт новый продукт",
)
async def create_product(data: ProductCreate) -> ProductCreateResponse:
    app = Container.product_application()
    product = Product(name=data.name, description=data.description)
    product_id = await app.create(product)
    return ProductCreateResponse(id=product_id)


@router.patch(
    "/{product_id}",
    response_model=Product,
    summary="Обновить продукт",
    description="Обновляет данные продукта",
)
async def update_product(
    product_id: UUID = Path(..., description="UUID продукта"),
    data: ProductUpdate = ...,
) -> Product:
    app = Container.product_application()
    try:
        return await app.update(
            product_id=product_id,
            name=data.name,
            description=data.description,
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Продукт не найден")


@router.delete(
    "/{product_id}",
    status_code=204,
    summary="Удалить продукт",
    description="Удаляет продукт и все связанные данные",
)
async def delete_product(
    product_id: UUID = Path(..., description="UUID продукта"),
) -> None:
    app = Container.product_application()
    try:
        await app.delete(product_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Продукт не найден")
