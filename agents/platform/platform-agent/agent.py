"""
Platform Agent — Graph Assembly (T053 + T064)

يبني LangGraph StateGraph لكل workflow:
  - build_launch_graph()  → Launch Workflow (THEME_APPROVED → NEW_PRODUCT_LIVE)
  - build_update_graph()  → Update Workflow (THEME_UPDATED → THEME_UPDATED_LIVE)
"""
from __future__ import annotations
import logging
import os
import psycopg2
from langgraph.graph import END, StateGraph

from db.registry import ProductRegistry
from nodes.launch.launch_entry import make_launch_entry_node
from nodes.launch.inconsistency_check import make_inconsistency_check_node
from nodes.launch.contract_parser import make_contract_parser_node
from nodes.launch.asset_waiter import make_asset_waiter_node
from nodes.launch.product_creator import make_product_creator_node
from nodes.launch.license_configurator import make_license_configurator_node
from nodes.launch.vip_catalog_updater import make_vip_catalog_updater_node
from nodes.launch.page_writer import make_page_writer_node
from nodes.launch.page_renderer import make_page_renderer_node
from nodes.launch.human_review_gate import make_human_review_gate_node, route_after_review
from nodes.launch.saga_publisher import make_saga_publisher_node
from nodes.launch.registry_recorder import make_registry_recorder_node
from nodes.launch.launch_announcer import make_launch_announcer_node
from nodes.update.update_entry import make_update_entry_node
from nodes.update.changelog_validator import make_changelog_validator_node
from nodes.update.registry_loader import make_registry_loader_node
from nodes.update.wp_content_updater import make_wp_content_updater_node
from nodes.update.ls_file_updater import make_ls_file_updater_node
from nodes.update.eligibility_filter import make_eligibility_filter_node
from nodes.update.notification_sender import make_notification_sender_node
from nodes.update.version_recorder import make_version_recorder_node
from nodes.update.update_announcer import make_update_announcer_node
from services.wp_client import WordPressClient
from services.ls_client import LemonSqueezyClient
from services.redis_bus import RedisBus
from services.resend_client import ResendClient
from state import LaunchState, UpdateState, PlatformStatus

logger = logging.getLogger("platform_agent.agent")


def _make_services():
    db_conn = psycopg2.connect(os.environ["DATABASE_URL"])
    registry = ProductRegistry(db_conn)
    wp_client = WordPressClient()
    ls_client = LemonSqueezyClient()
    redis_bus = RedisBus()
    resend = ResendClient()
    return registry, wp_client, ls_client, redis_bus, resend


def _fail_route(state, ok_target):
    return "end" if state.get("status") == PlatformStatus.FAILED else ok_target


# ─────────────────────────────────────────────────────────────
# T053 — build_launch_graph
# ─────────────────────────────────────────────────────────────
def build_launch_graph(registry=None, wp_client=None, ls_client=None, redis_bus=None, resend=None):
    if registry is None:
        registry, wp_client, ls_client, redis_bus, resend = _make_services()

    g = StateGraph(LaunchState)

    g.add_node("launch_entry",        make_launch_entry_node(registry))
    g.add_node("inconsistency_check", make_inconsistency_check_node(registry, resend))
    g.add_node("contract_parser",     make_contract_parser_node(registry))
    g.add_node("asset_waiter",        make_asset_waiter_node(registry, redis_bus))
    g.add_node("product_creator",     make_product_creator_node(registry, ls_client))
    g.add_node("license_configurator",make_license_configurator_node(registry))
    g.add_node("vip_catalog_updater", make_vip_catalog_updater_node(registry, ls_client))
    g.add_node("page_writer",         make_page_writer_node(registry))
    g.add_node("page_renderer",       make_page_renderer_node(registry))
    g.add_node("human_review_gate",   make_human_review_gate_node(registry, resend, redis_bus))
    g.add_node("saga_publisher",      make_saga_publisher_node(registry, wp_client, ls_client, resend))
    g.add_node("registry_recorder",   make_registry_recorder_node(registry))
    g.add_node("launch_announcer",    make_launch_announcer_node(registry, redis_bus, resend))

    g.set_entry_point("launch_entry")

    # launch_entry → inconsistency_check
    g.add_edge("launch_entry", "inconsistency_check")

    # inconsistency_check →
    g.add_conditional_edges("inconsistency_check",
        lambda s: "end" if s.get("status") in (PlatformStatus.INCONSISTENT_EXTERNAL_STATE, PlatformStatus.FAILED) else "contract_parser",
        {"end": END, "contract_parser": "contract_parser"})

    # contract_parser → asset_waiter →
    g.add_edge("contract_parser", "asset_waiter")
    g.add_conditional_edges("asset_waiter",
        lambda s: "end" if s.get("status") == PlatformStatus.WAITING_ASSETS else "product_creator",
        {"end": END, "product_creator": "product_creator"})

    # product_creator → license_configurator
    g.add_conditional_edges("product_creator",
        lambda s: "end" if s.get("status") == PlatformStatus.FAILED else "license_configurator",
        {"end": END, "license_configurator": "license_configurator"})

    # license_configurator → vip_catalog_updater → page_writer → page_renderer
    g.add_edge("license_configurator", "vip_catalog_updater")
    g.add_edge("vip_catalog_updater", "page_writer")
    g.add_conditional_edges("page_writer",
        lambda s: "end" if s.get("status") == PlatformStatus.FAILED else "page_renderer",
        {"end": END, "page_renderer": "page_renderer"})
    g.add_conditional_edges("page_renderer",
        lambda s: "end" if s.get("status") == PlatformStatus.FAILED else "human_review_gate",
        {"end": END, "human_review_gate": "human_review_gate"})

    # human_review_gate → (routing)
    def _route_review(state):
        target = route_after_review(state)
        return "end" if target == "END" else target
    g.add_conditional_edges("human_review_gate", _route_review,
        {"end": END, "saga_publisher": "saga_publisher", "page_writer": "page_writer"})

    # saga_publisher → registry_recorder
    g.add_conditional_edges("saga_publisher",
        lambda s: "end" if s.get("status") in (PlatformStatus.INCONSISTENT_EXTERNAL_STATE, PlatformStatus.FAILED) else "registry_recorder",
        {"end": END, "registry_recorder": "registry_recorder"})

    g.add_edge("registry_recorder", "launch_announcer")
    g.add_edge("launch_announcer", END)

    return g.compile()


# ─────────────────────────────────────────────────────────────
# T064 — build_update_graph
# ─────────────────────────────────────────────────────────────
def build_update_graph(registry=None, wp_client=None, ls_client=None, redis_bus=None, resend=None):
    if registry is None:
        registry, wp_client, ls_client, redis_bus, resend = _make_services()

    g = StateGraph(UpdateState)

    g.add_node("update_entry",        make_update_entry_node(registry))
    g.add_node("changelog_validator", make_changelog_validator_node(registry))
    g.add_node("registry_loader",     make_registry_loader_node(registry))
    g.add_node("wp_content_updater",  make_wp_content_updater_node(registry, wp_client))
    g.add_node("ls_file_updater",     make_ls_file_updater_node(registry, ls_client))
    g.add_node("eligibility_filter",  make_eligibility_filter_node(registry, ls_client))
    g.add_node("notification_sender", make_notification_sender_node(registry, resend))
    g.add_node("version_recorder",    make_version_recorder_node(registry))
    g.add_node("update_announcer",    make_update_announcer_node(registry, redis_bus))

    g.set_entry_point("update_entry")

    for src, tgt in [
        ("update_entry",        "changelog_validator"),
        ("changelog_validator", "registry_loader"),
        ("registry_loader",     "wp_content_updater"),
        ("wp_content_updater",  "ls_file_updater"),
    ]:
        g.add_conditional_edges(src,
            lambda s, t=tgt: "end" if s.get("status") == PlatformStatus.FAILED else t,
            {"end": END, tgt: tgt})

    g.add_edge("ls_file_updater",    "eligibility_filter")
    g.add_edge("eligibility_filter", "notification_sender")
    g.add_edge("notification_sender","version_recorder")
    g.add_edge("version_recorder",   "update_announcer")
    g.add_edge("update_announcer",   END)

    return g.compile()


if __name__ == "__main__":
    from logging_config import configure_logging
    configure_logging()
    import threading
    from listeners.launch_listener import LaunchListener
    from listeners.update_listener import UpdateListener
    t1 = threading.Thread(target=LaunchListener().run, daemon=True)
    t2 = threading.Thread(target=UpdateListener().run, daemon=True)
    t1.start(); t2.start()
    logger.info("Platform Agent running — waiting for events...")
    t1.join(); t2.join()
