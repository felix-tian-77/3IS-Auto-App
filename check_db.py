import sys
sys.path.insert(0, 'backend')

import asyncio
from sqlalchemy import text
from backend.db.database import engine

async def check_columns():
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'transactions' ORDER BY ordinal_position
        """))
        cols = [r[0] for r in result.fetchall()]
        print('transactions columns:', cols)

        if 'holder_phone' not in cols:
            print('holder_phone column missing! Adding...')
            await conn.execute(text('ALTER TABLE transactions ADD COLUMN holder_phone VARCHAR(20)'))
            await conn.commit()
            print('holder_phone column added!')
        else:
            print('holder_phone column exists')

        if 'tax_exempt' not in cols:
            print('tax_exempt column missing! Adding...')
            await conn.execute(text('ALTER TABLE transactions ADD COLUMN tax_exempt BOOLEAN NOT NULL DEFAULT FALSE'))
            await conn.commit()
            print('tax_exempt column added!')
        else:
            print('tax_exempt column exists')

        if 'is_transfer' not in cols:
            print('is_transfer column missing! Adding...')
            await conn.execute(text('ALTER TABLE transactions ADD COLUMN is_transfer BOOLEAN NOT NULL DEFAULT FALSE'))
            await conn.commit()
            print('is_transfer column added!')
        else:
            print('is_transfer column exists')

asyncio.run(check_columns())
