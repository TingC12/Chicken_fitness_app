import os
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")

engine = create_async_engine(db_url, echo=True, pool_pre_ping=True)

async def main():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Conneted! result = ", result.scalar())
    except Exception as e:
        print("Connection failed:", e)  
        
if __name__ == "__main__":
    asyncio.run(main())
            