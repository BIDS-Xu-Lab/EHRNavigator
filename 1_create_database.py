import pandas as pd
import sqlite3
from sqlalchemy import create_engine, text
import os
from typing import List, Dict
from tqdm import tqdm

class MIMICDatabaseCreator:
    def __init__(self, csv_dir: str, db_path: str):
        """
        Initialize the MIMIC database creator
        
        Args:
            csv_dir: Directory containing the CSV files
            db_path: Path where the SQLite database will be created
        """
        self.csv_dir = csv_dir
        self.db_path = db_path
        self.engine = None
        
        self.table_schemas = {}
        self.primary_keys = {
            'PATIENTS': 'SUBJECT_ID',
            'ADMISSIONS': 'HADM_ID',
            'ICUSTAYS': 'ICUSTAY_ID',
            'PRESCRIPTIONS': 'ROW_ID',
            'CHARTEVENTS': 'ROW_ID',
            'LABEVENTS': 'ROW_ID'
        }
        
        # Common datetime columns for automatic type detection
        self.datetime_columns = {
            'DOB', 'DOD', 'DOD_HOSP', 'DOD_SSN', 'ADMITTIME', 'DISCHTIME', 
            'DEATHTIME', 'INTIME', 'OUTTIME', 'STARTDATE', 'ENDDATE', 
            'CHARTTIME', 'STORETIME'
        }
        
    def infer_column_type(self, column_name: str, sample_data: pd.Series) -> str:
        """
        Infer SQL column type from column name and sample data
        
        Args:
            column_name: Name of the column
            sample_data: Sample data from the column
            
        Returns:
            SQL column type as string
        """
        # Check if it's a datetime column
        if column_name in self.datetime_columns:
            return 'DATETIME'
            
        # Get the pandas dtype
        dtype = str(sample_data.dtype)
        
        # Numeric types
        if 'int' in dtype:
            return 'INTEGER'
        elif 'float' in dtype:
            return 'FLOAT'
            
        # Get the maximum length of string data
        if 'object' in dtype:
            max_length = sample_data.astype(str).str.len().max()
            max_length = max(max_length, 50)  # Minimum length of 50
            return f'VARCHAR({max_length})'
            
        # Default to TEXT for unknown types
        return 'TEXT'
        
    def generate_table_schema(self, table_name: str, csv_file: str):
        """
        Generate table schema from CSV file
        
        Args:
            table_name: Name of the table
            csv_file: Path to the CSV file
        """
        # Read a sample of the CSV file
        df_sample = pd.read_csv(csv_file, nrows=1000)
        df_sample = self.clean_column_names(df_sample)
        
        schema = {}
        for column in df_sample.columns:
            # If column is primary key
            if table_name in self.primary_keys and column == self.primary_keys[table_name]:
                schema[column] = 'INTEGER PRIMARY KEY'
            else:
                schema[column] = self.infer_column_type(column, df_sample[column])
                
        self.table_schemas[table_name] = schema
        
    def create_connection(self):
        """Create SQLite database connection"""
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        print(f"Database created at: {self.db_path}")
        
    def get_csv_files(self) -> List[str]:
        """Get list of all CSV files in the directory"""
        csv_files = []
        for file in os.listdir(self.csv_dir):
            if file.endswith('.csv'):
                csv_files.append(file)
        return csv_files
    
    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean column names to be SQL friendly"""
        df.columns = df.columns.str.strip()
        df.columns = df.columns.str.replace(' ', '_')
        df.columns = df.columns.str.replace('-', '_')
        df.columns = df.columns.str.upper()
        return df
    
    def create_table_schema(self, table_name: str):
        """
        Create table with predefined schema
        
        Args:
            table_name: Name of the table to create
        """
        if table_name not in self.table_schemas:
            raise ValueError(f"Schema not defined for table {table_name}")
            
        schema = self.table_schemas[table_name]
        columns = []
        for col_name, col_type in schema.items():
            columns.append(f"{col_name} {col_type}")
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {', '.join(columns)}
        );
        """
        
        with self.engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
            
    def create_table_from_csv(self, csv_file: str, chunk_size: int = 10000):
        """
        Create a table from CSV file and load data
        
        Args:
            csv_file: Name of the CSV file
            chunk_size: Number of rows to process at once
        """
        table_name = os.path.splitext(csv_file)[0].upper()
        file_path = os.path.join(self.csv_dir, csv_file)
        
        print(f"\nProcessing {table_name}...")
        
        # Generate schema from CSV file
        self.generate_table_schema(table_name, file_path)
        
        # Create table with the generated schema
        self.create_table_schema(table_name)
        
        # Read and insert data in chunks
        chunks = pd.read_csv(file_path, chunksize=chunk_size)
        total_rows = sum(1 for _ in open(file_path)) - 1  # subtract header row
        
        with tqdm(total=total_rows, desc=f"Loading {table_name}") as pbar:
            for chunk in chunks:
                chunk = self.clean_column_names(chunk)
                chunk.to_sql(table_name, self.engine, if_exists='append', index=False)
                pbar.update(len(chunk))
    
    def create_indices(self, table_indices: Dict[str, List[str]]):
        """
        Create indices for specified tables and columns
        
        Args:
            table_indices: Dictionary mapping table names to lists of columns to index
        """
        for table, columns in table_indices.items():
            print(f"\nCreating indices for table {table}...")
            for column in columns:
                index_name = f"idx_{table}_{column}"
                query = f"""
                CREATE INDEX IF NOT EXISTS {index_name} 
                ON {table} ({column});
                """
                with self.engine.connect() as conn:
                    conn.execute(text(query))
                    conn.commit()
                print(f"Created index {index_name}")
    
    def verify_tables(self):
        """Verify that all tables were created successfully"""
        with self.engine.connect() as conn:
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            tables = conn.execute(text(query)).fetchall()
            
        print("\nCreated tables:")
        for table in tables:
            query = f"SELECT COUNT(*) FROM {table[0]};"
            count = self.engine.connect().execute(text(query)).scalar()
            print(f"- {table[0]}: {count} rows")

def main():
    # Configure paths
    csv_dir = "/data/lq62/mimic-iii-clinical-database-1.4"  # MIMIC-III CSV files directory
    db_path = "/home/lq62/EHR-QA/baseline_mimic/my_database_mimic.db"
    
    # Define indices for commonly queried columns
    table_indices = {
        'ADMISSIONS': ['SUBJECT_ID', 'HADM_ID'],
        'PATIENTS': ['SUBJECT_ID'],
        'PRESCRIPTIONS': ['SUBJECT_ID', 'HADM_ID', 'DRUG'],
        'CHARTEVENTS': ['SUBJECT_ID', 'HADM_ID', 'ITEMID'],
        'LABEVENTS': ['SUBJECT_ID', 'HADM_ID', 'ITEMID'],
    }
    
    # Create database
    creator = MIMICDatabaseCreator(csv_dir, db_path)
    creator.create_connection()
    
    # Process each CSV file
    csv_files = creator.get_csv_files()
    for csv_file in csv_files:
        creator.create_table_from_csv(csv_file)
    
    # Create indices for faster querying
    creator.create_indices(table_indices)
    
    # Verify the database
    creator.verify_tables()

if __name__ == "__main__":
    main()