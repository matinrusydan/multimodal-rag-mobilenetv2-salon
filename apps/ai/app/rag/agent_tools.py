"""Tool definitions + implementasi untuk agent admin (Gemini function-calling).

Setiap tool memanggil endpoint ringkasan Express (data live), dengan token internal.
Gemini memutuskan tool mana yang perlu dipanggil berdasarkan pertanyaan admin.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.rag.api_client import api_get

logger = logging.getLogger(__name__)


# --- Definisi tool untuk Gemini (function declarations) ---
TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "get_services_summary",
        "description": (
            "Ambil data layanan salon saat ini: jumlah layanan aktif, rentang harga, "
            "per-kategori, dan daftar layanan beserta harga & durasinya. "
            "Pakai untuk pertanyaan tentang layanan yang tersedia, harga layanan, kategori."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_revenue_summary",
        "description": (
            "Ambil ringkasan pemasukan (pembayaran berstatus paid): total pemasukan, "
            "jumlah transaksi dibayar, jumlah pembayaran pending, dan rincian per metode. "
            "Parameter from/to opsional (format YYYY-MM-DD) untuk membatasi periode. "
            "Pakai untuk pertanyaan 'pemasukan saat ini berapa', 'pendapatan hari ini', dll."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "from": {"type": "string", "description": "Tanggal awal (YYYY-MM-DD), opsional"},
                "to": {"type": "string", "description": "Tanggal akhir (YYYY-MM-DD), opsional"},
            },
            "required": [],
        },
    },
    {
        "name": "get_reservations_stats",
        "description": (
            "Ambil statistik reservasi: total reservasi, jumlah per status "
            "(pending/confirmed/cancelled/completed), dan jumlah per hari (N hari terakhir). "
            "Pakai untuk pertanyaan tentang jumlah reservasi/booking."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Jumlah hari terakhir (default 7)"},
            },
            "required": [],
        },
    },
]


async def _get_services_summary(args: dict[str, Any]) -> dict[str, Any]:
    return await api_get("/api/services/summary")


async def _get_revenue_summary(args: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if args.get("from"):
        params["from"] = args["from"]
    if args.get("to"):
        params["to"] = args["to"]
    return await api_get("/api/payments/summary", params=params or None)


async def _get_reservations_stats(args: dict[str, Any]) -> dict[str, Any]:
    days = args.get("days") or 7
    return await api_get("/api/reservations/stats", params={"days": days})


TOOL_IMPLS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "get_services_summary": _get_services_summary,
    "get_revenue_summary": _get_revenue_summary,
    "get_reservations_stats": _get_reservations_stats,
}


async def execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Jalankan tool berdasarkan nama. Return dict {ok, result|error}."""
    impl = TOOL_IMPLS.get(name)
    if not impl:
        return {"ok": False, "error": f"tool tidak dikenal: {name}"}
    try:
        result = await impl(args or {})
        return {"ok": True, "result": result}
    except Exception as exc:
        logger.warning("tool %s gagal: %s", name, exc)
        return {"ok": False, "error": str(exc)}
