"""Application composition for Parent workspace use cases."""

from backend.application.container import AppContainer
from backend.modules.people.parent.commands import ParentCommands
from backend.modules.people.parent.queries import ParentQueries


def build_parent_queries(container: AppContainer) -> ParentQueries:
    return ParentQueries(container.unit_of_work_factory)


def build_parent_commands(container: AppContainer) -> ParentCommands:
    return ParentCommands(container.unit_of_work_factory)


__all__ = ["build_parent_commands", "build_parent_queries"]
