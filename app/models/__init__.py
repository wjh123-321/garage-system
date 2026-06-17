from .customer import Customer
from .work_order import WorkOrder, WorkOrderItem
from .part import Part, InventoryTransaction
from .reminder import ServiceReminder
from .ai_recommendation import AIRepairRecommendation, AIPartForecast, AICustomerInsight

__all__ = [
    "Customer",
    "WorkOrder",
    "WorkOrderItem",
    "Part",
    "InventoryTransaction",
    "ServiceReminder",
    "AIRepairRecommendation",
    "AIPartForecast",
    "AICustomerInsight",
]
