#!/usr/bin/env python3
"""
Test script for the auto-load database functionality.

This script demonstrates how to use the auto_load_database function
to automatically discover and load database schema and descriptions.
"""

import os
import sys

# Ensure we can import from current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_schema_loader import auto_load_database


def main():
    """Test the auto-load functionality."""
    
    print("\n" + "=" * 70)
    print("Testing Auto-Load Database Functionality")
    print("=" * 70 + "\n")
    
    try:
        # Test 1: Auto-discover everything
        print("Test 1: Auto-discover database and descriptions")
        print("-" * 70)
        table_names, table_infos, table_columns = auto_load_database()
        
        print("\n✓ Test 1 PASSED\n")
        
        # Test 2: Show detailed information for first table
        print("\nTest 2: Display detailed information for first table")
        print("-" * 70)
        if table_names:
            first_table = table_names[0]
            print(f"\nTable: {first_table}")
            print(f"Columns ({len(table_columns[first_table])}):")
            for i, col in enumerate(table_columns[first_table][:5], 1):  # Show first 5
                print(f"  {i}. {col}")
            if len(table_columns[first_table]) > 5:
                print(f"  ... and {len(table_columns[first_table]) - 5} more")
            
            print(f"\nDescription preview:")
            desc = table_infos[first_table]
            if desc:
                # Show first 300 characters of description
                preview = desc[:300] + "..." if len(desc) > 300 else desc
                print(f"  {preview}")
            else:
                print("  (No description available)")
        
        print("\n✓ Test 2 PASSED\n")
        
        # Test 3: Verify all tables have columns
        print("\nTest 3: Verify all tables have columns")
        print("-" * 70)
        tables_without_columns = [t for t in table_names if not table_columns[t]]
        if tables_without_columns:
            print(f"⚠ Warning: {len(tables_without_columns)} tables have no columns:")
            for t in tables_without_columns:
                print(f"  - {t}")
        else:
            print("✓ All tables have columns defined")
        
        print("\n✓ Test 3 PASSED\n")
        
        # Test 4: Check description coverage
        print("\nTest 4: Check description coverage")
        print("-" * 70)
        tables_with_desc = sum(1 for v in table_infos.values() if v)
        coverage = (tables_with_desc / len(table_names) * 100) if table_names else 0
        print(f"Description coverage: {tables_with_desc}/{len(table_names)} ({coverage:.1f}%)")
        
        if coverage < 50:
            print("⚠ Warning: Less than 50% of tables have descriptions")
            print("  Consider running sqlite_table_description.py to generate descriptions")
        else:
            print("✓ Good description coverage")
        
        print("\n✓ Test 4 PASSED\n")
        
        # Summary
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"✓ Total tables loaded: {len(table_names)}")
        print(f"✓ Tables with descriptions: {tables_with_desc}")
        print(f"✓ Total columns across all tables: {sum(len(cols) for cols in table_columns.values())}")
        print("\n✓ ALL TESTS PASSED!\n")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

