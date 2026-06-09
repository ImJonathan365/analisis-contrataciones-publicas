import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 1. Load environment variables from the .env file
load_dotenv()

# 2. Configure file and table names
archivo_excel = "data/raw/2-detalle-pliego-de-condiciones-glinny-mondragon.xlsx"
nombre_tabla = "public_contracts"

# 3. Get credentials from the .env file
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST", "127.0.0.1")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME")

print("Reading the Excel file (this may take a moment due to the 84 MB size).")
df = pd.read_excel(archivo_excel)
print("File successfully loaded into memory.")

print("Connecting to MySQL and migrating data...")
try:
    # Create the connection string for MySQL (SQLAlchemy)
    # If you use pymysql, change 'mysqldb' to 'pymysql'
    connection_string = f"mysql+mysqldb://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_string)
    
    # Migrate the data. If the table already exists, it will be replaced.
    df.to_sql(nombre_tabla, con=engine, if_exists="replace", index=False)
    print(f"The data is now in the '{nombre_tabla}' table in MySQL.")

except Exception as e:
    print(f"Error connecting or migrating to MySQL: {e}")
    exit()

# 4. Generate the summary for the AI chat
print("\n--- MYSQL COLUMN STRUCTURE ---")
print(df.dtypes.to_string())

print("\n--- SAMPLE DATA (FIRST 3 ROWS) ---")
print(df.head(3).fillna("N/A").to_string())