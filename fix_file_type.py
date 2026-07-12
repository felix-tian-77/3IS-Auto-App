import sys
sys.path.insert(0, 'backend')

import asyncio
from sqlalchemy import text
from backend.db.database import engine

async def fix_column():
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'attachments' AND column_name = 'file_type'
        """))
        row = result.fetchone()
        print('Current file_type:', row)

        if row and row[2] and row[2] < 32:
            print('Altering file_type column to VARCHAR(32)...')
            await conn.execute(text('ALTER TABLE attachments ALTER COLUMN file_type TYPE VARCHAR(32)'))
            await conn.commit()
            print('Done!')
        else:
            print('file_type column is already large enough')

asyncio.run(fix_column())
