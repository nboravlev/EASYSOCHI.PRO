from pydantic import BaseModel, Field
from typing import Optional, List

# 🔄 ВЫНЕСЕНО: Все Pydantic схемы в отдельный файл

class DonationRequest(BaseModel):
    """Запрос на создание доната"""
    amount: int = Field(..., ge=50, description="Сумма в рублях")
    name: Optional[str] = Field(None, max_length=150)
    email: Optional[str] = Field(None, max_length=150)

class DonationResponse(BaseModel):
    """Ответ с ссылкой на оплату"""
    confirmation_url: str

class DonorInfo(BaseModel):
    """Информация о донатере"""
    name: str
    amount: int
    
class StatsResponse(BaseModel):
    """Статистика сборов"""
    raised: int
    goal: int
    donors: List[DonorInfo]
