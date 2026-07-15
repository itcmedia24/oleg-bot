# -*- coding: utf-8 -*-
"""Хранение данных пользователей в SQLite.

Прогресс по программе хранится как позиция (program_day) — номер текущего
задания. Человек двигается сам: следующее задание открывается по кнопке,
в своём темпе. Календарь не используется — пропуск дней ничего не
перескакивает.
"""

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
                program_start TEXT,
                program_day INTEGER
            )
            """
        )
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Добавляет колонку program_day и переносит старый прогресс.

    Раньше день считался по календарю от program_start. Чтобы никто не
    потерял место, конвертируем эту дату в позицию program_day.
    """
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)")]
    if "program_day" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN program_day INTEGER")
        rows = conn.execute(
            "SELECT user_id, program_start FROM users WHERE program_start IS NOT NULL"
        ).fetchall()
        for r in rows:
            try:
                start = date.fromisoformat(r["program_start"])
            except (TypeError, ValueError):
                continue
            day = (date.today() - start).days + 1
            day = max(1, min(day, 60))  # 60 — максимальная длина программы
            conn.execute(
                "UPDATE users SET program_day = ? WHERE user_id = ?",
                (day, r["user_id"]),
            )


def set_user_type(user_id: int, type_num: int) -> None:
    """Сохраняет тип пользователя. Сброс прогресса при смене типа."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT type FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (user_id, type, program_start, program_day) "
                "VALUES (?, ?, NULL, NULL)",
                (user_id, type_num),
            )
        elif row["type"] != type_num:
            conn.execute(
                "UPDATE users SET type = ?, program_day = NULL WHERE user_id = ?",
                (type_num, user_id),
            )


def get_user_type(user_id: int) -> int | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT type FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["type"] if row else None


def start_program(user_id: int) -> None:
    """Запускает программу с первого задания."""
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET program_day = 1, program_start = ? WHERE user_id = ?",
            (date.today().isoformat(), user_id),
        )


def get_program_day(user_id: int) -> int | None:
    """Возвращает номер текущего задания (1..N) или None, если не начато."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT program_day FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["program_day"] if row and row["program_day"] is not None else None


def set_program_day(user_id: int, day: int) -> None:
    """Устанавливает номер текущего задания."""
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET program_day = ? WHERE user_id = ?", (day, user_id)
        )


def advance_program(user_id: int, total: int) -> int:
    """Двигает прогресс на одно задание вперёд (не выше total). Возвращает новый день."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT program_day FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        current = row["program_day"] if row and row["program_day"] else 1
        new_day = min(current + 1, total)
        conn.execute(
            "UPDATE users SET program_day = ? WHERE user_id = ?", (new_day, user_id)
        )
        return new_day


def reset_program(user_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET program_day = NULL WHERE user_id = ?", (user_id,)
        )
