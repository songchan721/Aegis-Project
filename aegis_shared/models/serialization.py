import json
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeMeta


def from_orm(orm_obj: DeclarativeMeta, pydantic_model: type[BaseModel]) -> BaseModel:
    return pydantic_model.from_orm(orm_obj)


def to_dict(pydantic_obj: BaseModel) -> dict:
    return pydantic_obj.dict()


def to_json(pydantic_obj: BaseModel) -> str:
    return pydantic_obj.json()


def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def to_json_custom(pydantic_obj: BaseModel) -> str:
    return json.dumps(pydantic_obj.dict(), default=json_serial)
