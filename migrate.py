from sqlalchemy import create_engine, text
from config import DATABASE_URL

def run_migrations():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Create users table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Create chats table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chats (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                message TEXT NOT NULL,
                response TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Create documents table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(1024) NOT NULL,
                content_hash VARCHAR(64) UNIQUE,
                indexed BOOLEAN DEFAULT FALSE,
                indexed_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chats_timestamp ON chats(timestamp)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash)"))
        
        conn.commit()
    
    print("Database migrations completed successfully!")

if __name__ == "__main__":
    run_migrations()