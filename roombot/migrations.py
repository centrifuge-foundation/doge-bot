from mautrix.util.async_db import UpgradeTable, Connection, Scheme

upgrade_table = UpgradeTable()

@upgrade_table.register(description="Initial revision")
async def upgrade_v1(conn: Connection, scheme: Scheme) -> None:
  await conn.execute(
    """
    CREATE TABLE groups (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
  )
  await conn.execute(
    """
    CREATE TABLE group_users (
      group_id INTEGER NOT NULL,
      user_id TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (group_id, user_id)
    );
    """
  )
  await conn.execute(
    """
    CREATE TABLE group_rooms (
      group_id INTEGER NOT NULL,
      room_id TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (group_id, room_id)
    );
    """
  )