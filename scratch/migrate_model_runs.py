import sqlite3
import os

db_paths = ["fixproof_dev.db", "services/api/fixproof_dev.db"]

for path in db_paths:
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Check existing columns in model_runs
        cursor.execute("PRAGMA table_info(model_runs)")
        cols = [row[1] for row in cursor.fetchall()]
        print(f"[{path}] Existing columns in model_runs: {len(cols)}")
        
        new_columns = [
            ("model_provider", "VARCHAR(50) DEFAULT 'roboflow'"),
            ("citizen_confirmed_category", "VARCHAR(50)"),
            ("error_info", "TEXT"),
            ("duplicate_candidates_json", "TEXT"),
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in cols:
                try:
                    cursor.execute(f"ALTER TABLE model_runs ADD COLUMN {col_name} {col_type};")
                    print(f"  Added column: {col_name}")
                except Exception as e:
                    print(f"  Could not add {col_name}: {e}")
            else:
                print(f"  Column already exists: {col_name}")
                
        conn.commit()
        conn.close()
        print(f"[{path}] Migration complete!\n")
    else:
        print(f"Database file not found: {path}")
