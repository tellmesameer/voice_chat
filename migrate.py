# migrate.py
from sqlalchemy import create_engine, text, inspect
from config import DATABASE_URL

def run_migrations():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
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
        
        # Check if documents table exists and has user_id column
        if inspector.has_table("documents"):
            columns = [column['name'] for column in inspector.get_columns("documents")]
            
            # Add user_id column if it doesn't exist
            if "user_id" not in columns:
                conn.execute(text("""
                    ALTER TABLE documents 
                    ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
                """))
                print("Added user_id column to documents table")
            else:
                print("user_id column already exists in documents table")
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chats_timestamp ON chats(timestamp)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash)"))
        
        # Only create this index if the user_id column exists
        if inspector.has_table("documents") and "user_id" in [column['name'] for column in inspector.get_columns("documents")]:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)"))
        
        conn.commit()
    
    print("Database migrations completed successfully!")

if __name__ == "__main__":
    run_migrations()