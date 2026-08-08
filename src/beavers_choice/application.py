"""Dependency-injection bootstrap for the complete multi-agent application."""

from __future__ import annotations

from pathlib import Path

from .agents import AgentSystem
from .database import Database
from .helpers import configure_default_application
from .repositories import (
    ProductRepository,
    QuoteRepository,
    ReportingRepository,
    TransactionRepository,
)
from .services.inventory import InventoryService
from .services.ordering import OrderService
from .services.parsing import RequestParser
from .services.pricing import PricingService


class BeaverChoiceApplication:
    def __init__(self, database_path: Path):
        self.database = Database(database_path)
        self.products = ProductRepository(self.database)
        self.transactions = TransactionRepository(self.database)
        self.quotes = QuoteRepository(self.database)
        self.reporting = ReportingRepository(self.database)
        self.parser = RequestParser()
        self.inventory = InventoryService(self.products, self.transactions)
        self.pricing = PricingService(
            self.products, self.quotes, self.parser
        )
        self.orders = OrderService(
            self.database,
            self.parser,
            self.inventory,
            self.pricing,
            self.transactions,
            self.quotes,
            self.reporting,
        )
        configure_default_application(self)
        self.agents = AgentSystem(self)

    def initialize(self, reset: bool = False) -> None:
        self.database.initialize(reset=reset)


def create_application(
    database_path: Path, reset: bool = False
) -> BeaverChoiceApplication:
    application = BeaverChoiceApplication(database_path)
    application.initialize(reset=reset)
    return application
