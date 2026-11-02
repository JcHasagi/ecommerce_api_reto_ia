from collections import Counter

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload

import database
import models
import schemas

app = FastAPI(
    title="E-commerce API",
    description="API del reto de IA en Ingeniería de Software (UIS): usuarios, productos y pedidos.",
    version="1.0.0",
)

DISCOUNT_THRESHOLD = 100
DISCOUNT_RATE = 0.10


models.Base.metadata.create_all(bind=database.engine)

def apply_discount(price: float) -> float:
    """Aplica un 10 % de descuento a los productos que cuestan más de 100."""
    if price > DISCOUNT_THRESHOLD:
        return round(price * (1 - DISCOUNT_RATE), 2)
    return price

@app.post(
    "/users/",
    response_model=schemas.UserOut,
    status_code=201,
    tags=["usuarios"],
    summary="Crear un usuario",
)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Registra un usuario nuevo y lo devuelve con el id asignado."""
    db_user = models.User(name=user.name, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get(
    "/users/{user_id}/orders",
    response_model=list[schemas.OrderOut],
    tags=["usuarios"],
    summary="Historial de pedidos de un usuario",
    responses={404: {"description": "Usuario no encontrado"}},
)
def get_user_orders(user_id: int, db: Session = Depends(database.get_db)):
    """Devuelve los pedidos del usuario, del más reciente al más antiguo, con el nombre, la cantidad y el
    precio unitario cobrado de cada producto. Un usuario sin pedidos devuelve una lista vacía."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Carga líneas y productos en dos consultas fijas, en vez de una por pedido y otra por línea (N+1)
    orders = (
        db.query(models.Order)
        .filter(models.Order.user_id == user_id)
        .options(selectinload(models.Order.items).joinedload(models.OrderItem.product))
        .order_by(models.Order.created_at.desc(), models.Order.id.desc())
        .all()
    )
    return [
        schemas.OrderOut(
            id=o.id,
            created_at=o.created_at,
            total_price=o.total_price,
            items=[
                schemas.OrderItemOut(
                    product_id=item.product_id,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in o.items
            ],
        )
        for o in orders
    ]

@app.get(
    "/products/",
    response_model=list[schemas.ProductOut],
    tags=["productos"],
    summary="Listar productos",
)
def get_products(
    limit: int = Query(20, ge=1, le=100, description="Número máximo de productos a devolver"),
    offset: int = Query(0, ge=0, description="Número de productos a saltar"),
    db: Session = Depends(database.get_db),
):
    """Lista los productos por páginas, ordenados por id."""
    # Sin un orden fijo, la base de datos puede devolver las páginas en distinto orden en cada consulta
    return db.query(models.Product).order_by(models.Product.id).offset(offset).limit(limit).all()

@app.post(
    "/orders/",
    response_model=schemas.OrderCreated,
    status_code=201,
    tags=["pedidos"],
    summary="Crear un pedido",
    responses={
        400: {"description": "Algún producto no existe"},
        404: {"description": "Usuario no encontrado"},
        409: {"description": "Stock insuficiente"},
    },
)
def process_order(order: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    """Crea un pedido y descuenta el stock. Repetir un id en `product_ids` pide una unidad más de ese producto.

    Los productos que cuestan más de 100 tienen un 10 % de descuento. Si falta stock de algún producto,
    no se crea el pedido ni se modifica el stock.
    """
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    quantities = Counter(order.product_ids)
    # FOR UPDATE bloquea las filas hasta el commit para que dos pedidos simultáneos
    # no descuenten el mismo stock; ordenar por id evita interbloqueos entre pedidos.
    products = (
        db.query(models.Product)
        .filter(models.Product.id.in_(list(quantities)))
        .order_by(models.Product.id)
        .with_for_update()
        .all()
    )
    products_by_id = {prod.id: prod for prod in products}
    for pid in quantities:
        if pid not in products_by_id:
            raise HTTPException(status_code=400, detail=f"Producto {pid} no existe")

    total = 0
    items = []
    for prod in products:
        quantity = quantities[prod.id]
        if prod.stock < quantity:
            raise HTTPException(status_code=409, detail=f"Stock insuficiente para el producto {prod.id}")

        final_price = apply_discount(prod.price)
        total += final_price * quantity
        prod.stock -= quantity
        items.append(models.OrderItem(product_id=prod.id, quantity=quantity, unit_price=final_price))

    new_order = models.Order(user_id=order.user_id, total_price=total, items=items)
    db.add(new_order)
    db.commit()
    return {"status": "ok", "order_id": new_order.id, "total": total}
