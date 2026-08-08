"""Workflow diagram generation."""

from __future__ import annotations

from pathlib import Path


def generate_workflow_diagram(output_path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    except ImportError as exc:
        raise RuntimeError(
            "Install diagram dependencies with: pip install .[diagram]"
        ) from exc

    figure, axis = plt.subplots(figsize=(15, 9))
    axis.set_xlim(0, 15)
    axis.set_ylim(0, 9)
    axis.axis("off")

    def box(
        x: float,
        y: float,
        width: float,
        height: float,
        title: str,
        text: str,
        color: str,
    ) -> None:
        patch = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.04,rounding_size=0.12",
            facecolor=color,
            edgecolor="#263238",
            linewidth=1.6,
        )
        axis.add_patch(patch)
        axis.text(
            x + width / 2,
            y + height - 0.35,
            title,
            ha="center",
            va="top",
            fontsize=12,
            fontweight="bold",
        )
        axis.text(
            x + 0.18,
            y + height - 0.8,
            text,
            ha="left",
            va="top",
            fontsize=8.3,
        )

    def arrow(
        start: tuple[float, float],
        end: tuple[float, float],
        label: str = "",
    ) -> None:
        axis.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=14,
                linewidth=1.4,
                color="#455A64",
            )
        )
        if label:
            axis.text(
                (start[0] + end[0]) / 2,
                (start[1] + end[1]) / 2 + 0.15,
                label,
                ha="center",
                fontsize=8,
                color="#37474F",
            )

    box(
        0.3,
        3.25,
        2.2,
        2.0,
        "Customer",
        "Text inquiry\nItems, quantities\nRequested delivery date",
        "#FFF3E0",
    )
    box(
        3.2,
        3.0,
        2.7,
        2.5,
        "1. Orchestrator Agent",
        "process_customer_request_tool\nParses and validates request\n"
        "Delegates atomic workflow\nReturns customer-safe rationale",
        "#E3F2FD",
    )
    box(
        6.8,
        6.0,
        3.3,
        2.2,
        "2. Inventory Agent",
        "inventory_snapshot_tool -> get_all_inventory\n"
        "stock_level_tool -> get_stock_level\n"
        "supplier_timeline_tool ->\n  get_supplier_delivery_date\n"
        "reorder_tool ->\n  get_cash_balance + create_transaction",
        "#E8F5E9",
    )
    box(
        6.8,
        3.0,
        3.3,
        2.2,
        "3. Quoting Agent",
        "quote_history_tool -> search_quote_history\n"
        "build_quote_tool -> catalog cost +\n  historical quote anchor\n"
        "Applies transparent 0-15% volume discount",
        "#F3E5F5",
    )
    box(
        6.8,
        0.0,
        3.3,
        2.2,
        "4. Fulfillment Agent",
        "business_health_tool -> generate_financial_report\n"
        "record_sale_tool ->\n  get_stock_level + create_transaction\n"
        "Commits only feasible complete orders",
        "#E0F7FA",
    )
    box(
        11.3,
        3.0,
        3.2,
        2.5,
        "SQLite Database",
        "products\ntransactions\nquotes\n\nAtomic source of truth for stock,\n"
        "financials, and quote history",
        "#ECEFF1",
    )

    arrow((2.5, 4.25), (3.2, 4.25), "request")
    arrow((3.2, 3.7), (2.5, 3.7), "response")
    arrow((5.9, 4.8), (6.8, 6.8), "stock / reorder")
    arrow((5.9, 4.25), (6.8, 4.25), "price")
    arrow((5.9, 3.55), (6.8, 1.2), "sale")
    arrow((10.1, 7.0), (11.3, 4.9), "read/write")
    arrow((10.1, 4.1), (11.3, 4.1), "read/write")
    arrow((10.1, 1.1), (11.3, 3.3), "read/write")
    axis.text(
        7.5,
        8.65,
        "Beaver's Choice Paper Company - Four-Agent Workflow",
        ha="center",
        fontsize=17,
        fontweight="bold",
    )
    axis.text(
        7.5,
        8.3,
        "Four pydantic-ai agents backed by atomic services and SQLite.",
        ha="center",
        fontsize=10,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
