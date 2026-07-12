import sys
sys.path.insert(0, 'backend')

import asyncio
from sqlalchemy import text
from backend.db.database import get_engine

async def check_and_fix():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'attachments' ORDER BY ordinal_position
        """))
        columns = [row[0] for row in result.fetchall()]
        print('Current columns:', columns)

        if 'local_path' not in columns:
            print('Adding local_path column...')
            await conn.execute(text('ALTER TABLE attachments ADD COLUMN local_path VARCHAR(512)'))
            await conn.commit()
            print('local_path column added!')
        else:
            print('local_path column already exists')

if __name__ == '__main__':
    asyncio.run(check_and_fix())
