# -*- coding: utf-8 -*-
"""Хранение данных пользователей в SQLite."""

import sqlite3
from datetime import date

DB_PATH = "bot.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                type INTEGER,
                program_start TEXT
            )
            """
        )


def set_user_type(user_id: int, type_num: int) -> None:
    """Сохраняет тип пользователя. Сброс программы при смене типа."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT type FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (user_id, type, program_start) VALUES (?, ?, NULL)",
                (user_id, type_num),
            )
        elif row["type"] != type_num:
            conn.execute(
                "UPDATE users SET type = ?, program_start = NULL WHERE user_id = ?",
                (type_num, user_id),
            )


def get_user_type(user_id: int) -> int | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT type FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["type"] if row else None


def start_program(user_id: int) -> None:
    """Запускает 30-дневную программу с сегодняшнего дня."""
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET program_start = ? WHERE user_id = ?",
            (date.today().isoformat(), user_id),
        )


def get_program_day(user_id: int) -> int | None:
    """Возвращает номер текущего дня программы (1..30+) или None, если не начата.

    День продвигается автоматически по календарю: день 1 — дата старта,
    день 2 — следующий день и так далее.
    """
    with _conn() as conn:
        row = conn.execute(
            "SELECT program_start FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None or row["program_start"] is None:
            return None
        start = date.fromisoformat(row["program_start"])
        return (date.today() - start).days + 1


def reset_program(user_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET program_start = NULL WHERE user_id = ?", (user_id,)
        )
