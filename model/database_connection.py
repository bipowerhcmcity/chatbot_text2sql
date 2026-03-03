import pandas as pd
from sqlalchemy import create_engine, text
import sqlite3 # Use appropriate driver for your DB

def initalize_db_connection():
    conn = sqlite3.connect("/Users/lap60851/Library/DBeaverData/workspace6/.metadata/sample-database-sqlite-1/Chinook.db")
    return conn 

def retrieve_db_result(query, conn, limit: int = 200):
    # Retrieve to database and get the pandas dataframe result 
    # Read SQL query into pandas
    try:
        df = pd.read_sql_query(query, conn)
        # Limit number of rows returned to avoid huge payloads
        if limit is not None:
            df = df.head(limit)
        # Replace NaN with None so it's JSON serializable
        df = df.where(pd.notnull(df), None)
        # Return list of row dicts (suitable for frontend rendering)
        return df.to_dict(orient='records')
    except Exception as e:
        # Log and return an error dict so caller can handle it
        print(f"Error executing query: {e}")
        return {"error": str(e)}