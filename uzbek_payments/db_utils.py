# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Database utilities for PostgreSQL and MySQL/MariaDB compatibility
"""

import frappe


def is_postgres() -> bool:
	"""Check if database is PostgreSQL"""
	return frappe.db.db_type == "postgres"


def is_mysql() -> bool:
	"""Check if database is MySQL/MariaDB"""
	return frappe.db.db_type == "mariadb"


def get_table_name(table_name: str) -> str:
	"""
	Get properly quoted table name based on database type
	
	Args:
		table_name: Table name without quotes
		
	Returns:
		Properly quoted table name
	"""
	if is_postgres():
		return f'"{table_name}"'
	else:
		return f"`{table_name}`"


def format_sql_query(query: str) -> str:
	"""
	Format SQL query for database compatibility
	
	Args:
		query: SQL query string
		
	Returns:
		Formatted SQL query
	"""
	# Replace backticks with double quotes for PostgreSQL
	if is_postgres():
		# Replace backticks with double quotes, but preserve existing double quotes
		import re
		# Replace backticks around table/column names
		query = re.sub(r'`([^`]+)`', r'"\1"', query)
	
	return query


def get_year_function(date_field: str) -> str:
	"""
	Get year function based on database type
	
	Args:
		date_field: Date field name
		
	Returns:
		Year function call
	"""
	if is_postgres():
		return f"EXTRACT(YEAR FROM {date_field})"
	else:
		return f"YEAR({date_field})"


def get_date_trunc(part: str, field: str) -> str:
	"""
	Get date truncation function based on database type
	
	Args:
		part: Date part (day, month, year)
		field: Date field name
		
	Returns:
		Date truncation function call
	"""
	if is_postgres():
		return f"DATE_TRUNC('{part}', {field})"
	else:
		if part == "day":
			return f"DATE({field})"
		elif part == "month":
			return f"DATE_FORMAT({field}, '%Y-%m-01')"
		elif part == "year":
			return f"DATE_FORMAT({field}, '%Y-01-01')"
		else:
			return f"DATE({field})"


def get_database_function() -> str:
	"""
	Get database name function based on database type
	
	Returns:
		Database name function call
	"""
	if is_postgres():
		return "current_database()"
	else:
		return "DATABASE()"
