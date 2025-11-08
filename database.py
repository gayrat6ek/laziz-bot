import aiosqlite
from typing import List, Optional, Dict, Any
from config import get_settings

settings = get_settings()


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    phone_number TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Categories table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Questions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    order_num INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
                )
            """)

            # Answers table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    answer_text TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
                )
            """)

            # User responses table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_chat_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    answer_id INTEGER NOT NULL,
                    value INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_chat_id) REFERENCES users (chat_id),
                    FOREIGN KEY (category_id) REFERENCES categories (id),
                    FOREIGN KEY (question_id) REFERENCES questions (id),
                    FOREIGN KEY (answer_id) REFERENCES answers (id)
                )
            """)

            # Test sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS test_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_chat_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    total_score INTEGER DEFAULT 0,
                    completed BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_chat_id) REFERENCES users (chat_id),
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            """)

            # Category responses table (score-based responses)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS category_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    min_score INTEGER NOT NULL,
                    max_score INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
                )
            """)

            await db.commit()

    # User operations
    async def add_user(self, chat_id: int, phone_number: str, first_name: str = None, 
                      last_name: str = None, username: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users (chat_id, phone_number, first_name, last_name, username)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, phone_number, first_name, last_name, username))
            await db.commit()

    async def get_user(self, chat_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    # Category operations
    async def create_category(self, name: str, description: str = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO categories (name, description) VALUES (?, ?)
            """, (name, description))
            await db.commit()
            return cursor.lastrowid

    async def get_all_categories(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM categories ORDER BY created_at") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_category(self, category_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM categories WHERE id = ?", (category_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def delete_category(self, category_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            await db.commit()

    # Question operations
    async def create_question(self, category_id: int, question_text: str, order_num: int = 0) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO questions (category_id, question_text, order_num) VALUES (?, ?, ?)
            """, (category_id, question_text, order_num))
            await db.commit()
            return cursor.lastrowid

    async def get_questions_by_category(self, category_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM questions WHERE category_id = ? ORDER BY order_num, id
            """, (category_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_question(self, question_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM questions WHERE id = ?", (question_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def delete_question(self, question_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            await db.commit()

    # Answer operations
    async def create_answer(self, question_id: int, answer_text: str, value: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO answers (question_id, answer_text, value) VALUES (?, ?, ?)
            """, (question_id, answer_text, value))
            await db.commit()
            return cursor.lastrowid

    async def get_answers_by_question(self, question_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM answers WHERE question_id = ? ORDER BY value
            """, (question_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def delete_answer(self, answer_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM answers WHERE id = ?", (answer_id,))
            await db.commit()

    # Test session operations
    async def create_test_session(self, user_chat_id: int, category_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO test_sessions (user_chat_id, category_id) VALUES (?, ?)
            """, (user_chat_id, category_id))
            await db.commit()
            return cursor.lastrowid

    async def save_user_response(self, user_chat_id: int, category_id: int, 
                                 question_id: int, answer_id: int, value: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_responses (user_chat_id, category_id, question_id, answer_id, value)
                VALUES (?, ?, ?, ?, ?)
            """, (user_chat_id, category_id, question_id, answer_id, value))
            await db.commit()

    async def complete_test_session(self, session_id: int, total_score: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE test_sessions 
                SET total_score = ?, completed = 1, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (total_score, session_id))
            await db.commit()

    async def get_user_test_history(self, user_chat_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT ts.*, c.name as category_name 
                FROM test_sessions ts
                JOIN categories c ON ts.category_id = c.id
                WHERE ts.user_chat_id = ? AND ts.completed = 1
                ORDER BY ts.completed_at DESC
            """, (user_chat_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # Category response operations
    async def create_category_response(self, category_id: int, min_score: int, max_score: int, 
                                       title: str, response_text: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO category_responses (category_id, min_score, max_score, title, response_text)
                VALUES (?, ?, ?, ?, ?)
            """, (category_id, min_score, max_score, title, response_text))
            await db.commit()
            return cursor.lastrowid

    async def get_category_responses(self, category_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM category_responses 
                WHERE category_id = ? 
                ORDER BY min_score
            """, (category_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_response_for_score(self, category_id: int, score: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM category_responses 
                WHERE category_id = ? AND ? BETWEEN min_score AND max_score
                LIMIT 1
            """, (category_id, score)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def delete_category_response(self, response_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM category_responses WHERE id = ?", (response_id,))
            await db.commit()


# Global database instance
db = Database(settings.DATABASE_PATH)

