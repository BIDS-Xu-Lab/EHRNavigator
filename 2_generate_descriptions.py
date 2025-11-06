import json
import os
from typing import Dict, List
from sqlalchemy import create_engine, inspect, MetaData, Table, text
import pandas as pd
import openai
from dotenv import load_dotenv
from llama_index.core import PromptTemplate

class SQLiteTableDescriptionGenerator:
    def __init__(self, db_path: str):
        """
        Initialize the SQLite table description generator
        
        Args:
            db_path: Path to the SQLite database file
        """
        # Special handling if path contains colon
        if ':' in db_path:
            db_path = db_path.replace(':', '')
        
        # Print debug information
        print(f"\nConnecting to database: {db_path}")
        print(f"Database exists: {os.path.exists(db_path)}")
        print(f"Database size: {os.path.getsize(db_path) / 1024:.2f} KB")
        
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.inspector = inspect(self.engine)
        self.metadata = MetaData()
        self.table_descriptions = {}
        
        # Initialize LLM (use OPENAI_API_KEY from environment)
        load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if openai_api_key:
            openai.api_key = openai_api_key
            print("Using OpenAI API for table description generation")
        else:
            print("Warning: OPENAI_API_KEY not set. LLM calls will fail until you set this environment variable.")
        
        # Define prompt template for table description
        self.prompt_template = PromptTemplate(
            template="""
            Please provide a clear and concise description of the database table based on its structure:
            
            Table Name: {table_name}
            
            Columns:
            {columns}
            
            Primary Keys: {primary_keys}
            Foreign Keys: {foreign_keys}
            
            Generate a comprehensive description that explains:
            1. The purpose of this table
            2. The meaning of key fields
            
            Description:
            """
        )
        
    def get_table_info(self, table_name: str) -> Dict:
        """
        Get information about a specific table from SQLite database
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary containing table information
        """
        columns = self.inspector.get_columns(table_name)
        pk = self.inspector.get_pk_constraint(table_name)
        fk = self.inspector.get_foreign_keys(table_name)
        
        return {
            "table_name": table_name,
            "columns": [{
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "default": str(col["default"]) if col["default"] else None,
                "is_primary_key": col["name"] in pk["constrained_columns"] if pk else False,
            } for col in columns],
            "primary_keys": pk["constrained_columns"] if pk else [],
            "foreign_keys": [{
                "referred_table": fk_data["referred_table"],
                "referred_columns": fk_data["referred_columns"],
                "constrained_columns": fk_data["constrained_columns"]
            } for fk_data in fk]
        }
            
    def generate_table_description(self, table_info: Dict) -> str:
        """
        Generate human-readable description based on table information using LLM
        
        Args:
            table_info: Dictionary containing table information
            
        Returns:
            Generated table description string
        """
        if not table_info:
            return ""
            
        # Format column information
        columns_text = []
        for col in table_info["columns"]:
            nullable_str = "NULL" if col["nullable"] else "NOT NULL"
            pk_str = "PRIMARY KEY" if col["is_primary_key"] else ""
            default_str = f"DEFAULT {col['default']}" if col["default"] else ""
            columns_text.append(
                f"- {col['name']} ({col['type']}) {nullable_str} {pk_str} {default_str}".strip()
            )
            
        # Format foreign keys
        fk_text = []
        if table_info["foreign_keys"]:
            for fk in table_info["foreign_keys"]:
                const_cols = ", ".join(fk["constrained_columns"])
                ref_cols = ", ".join(fk["referred_columns"])
                fk_text.append(
                    f"{const_cols} → {fk['referred_table']}({ref_cols})"
                )
                
        # Prepare prompt inputs
        prompt_inputs = {
            "table_name": table_info["table_name"],
            "columns": "\n".join(columns_text),
            "primary_keys": ", ".join(table_info["primary_keys"]),
            "foreign_keys": "\n".join(fk_text) if fk_text else "None"
        }
        
        # Generate description using LLM
        prompt = self.prompt_template.format(**prompt_inputs)
        response = ""
        try:
            if not getattr(openai, 'api_key', None):
                raise RuntimeError("OpenAI API key not configured")

            # Call OpenAI using the new openai.OpenAI client (openai>=1.0.0)
            # Instantiate client (will pick up openai.api_key if set)
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=512,
            )
            # response content lives in resp.choices[0].message.content
            try:
                response = resp.choices[0].message.content
            except Exception:
                # Fallback to dict-style access for some SDK shapes
                response = resp['choices'][0]['message']['content']

            # Format final description
            description = [
                f"Table: {table_info['table_name']}",
                "",
                "Technical Details:",
                f"Primary Keys: {prompt_inputs['primary_keys']}",
                "Columns:",
                prompt_inputs['columns']
            ]
            
            if fk_text:
                description.extend([
                    "Foreign Keys:",
                    prompt_inputs['foreign_keys']
                ])
                
            description.extend([
                "",
                "Description:",
                response
            ])
            
            return "\n".join(description)
            
        except Exception as e:
            print(f"Error generating description for table {table_info['table_name']}: {str(e)}")
            return "\n".join([
                f"Table: {table_info['table_name']}",
                "Error: Could not generate description using LLM",
                "Technical Details:",
                prompt_inputs['columns']
            ])
        
    def process_all_tables(self) -> Dict[str, str]:
        """
        Process all tables in the database and generate descriptions
        
        Returns:
            Dictionary mapping table names to their descriptions
        """
        print("\nQuerying database for tables...")
        try:
            # Use raw SQL query to get table list
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
                raw_tables = result.fetchall()
                print(f"Raw SQL query found {len(raw_tables)} tables")
                print(f"Table names: {[t[0] for t in raw_tables]}")
            
            # Use SQLAlchemy inspector
            table_names = self.inspector.get_table_names()
            print(f"\nSQLAlchemy inspector found {len(table_names)} tables")
            print(f"Table names: {table_names}")
            
            for table_name in table_names:
                print(f"\nProcessing table: {table_name}")
                try:
                    table_info = self.get_table_info(table_name)
                    description = self.generate_table_description(table_info)
                    self.table_descriptions[table_name] = description
                    print(f"Successfully processed {table_name}")
                except Exception as e:
                    print(f"Error processing table {table_name}: {str(e)}")
                    
        except Exception as e:
            print(f"Error accessing database: {str(e)}")
                
        return self.table_descriptions
        
    def save_descriptions(self, output_path: str):
        """
        Save all table descriptions to a file
        
        Args:
            output_path: Path to the output file
        """
        with open(output_path, 'w') as f:
            json.dump(self.table_descriptions, f, indent=2)

def main():
    # Configure paths
    db_path = "./my_database_mimic.db"  # Use file without colon prefix
    backup_db_path = db_path #"/home/lq62/EHR-QA/baseline_mimic/:my_database_mimic.db"  # Backup database path
    output_path = "/home/lq62/EHR-QA/code/structured/sqlite_table_descriptions.json"
    
    # First try the primary database file
    if not os.path.exists(db_path):
        print(f"Primary database not found at {db_path}")
        if os.path.exists(backup_db_path):
            print(f"Using backup database at {backup_db_path}")
            db_path = backup_db_path
        else:
            print("No valid database file found!")
            return
    
    # Create generator instance
    generator = SQLiteTableDescriptionGenerator(db_path)
    
    # Process all tables
    descriptions = generator.process_all_tables()
    
    # Save results
    generator.save_descriptions(output_path)
    
    print(f"Generated descriptions for {len(descriptions)} tables")
    print(f"Results saved to {output_path}")
    
    # Print example of the first table description
    if descriptions:
        first_table = next(iter(descriptions))
        print(f"\nExample description for table '{first_table}':")
        print(descriptions[first_table])

if __name__ == "__main__":
    main()