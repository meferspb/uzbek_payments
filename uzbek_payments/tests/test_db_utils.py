# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Tests for database utilities
"""

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from uzbek_payments.db_utils import (
	is_postgres,
	is_mysql,
	get_table_name,
	format_sql_query,
	get_year_function,
	get_date_trunc,
	get_database_function,
)


class TestDBUtils(FrappeTestCase):
	"""Tests for database utilities"""

	@patch("uzbek_payments.db_utils.frappe.db")
	def test_is_postgres(self, mock_db):
		"""Test PostgreSQL detection"""
		mock_db.db_type = "postgres"
		self.assertTrue(is_postgres())
		self.assertFalse(is_mysql())

	@patch("uzbek_payments.db_utils.frappe.db")
	def test_is_mysql(self, mock_db):
		"""Test MySQL/MariaDB detection"""
		mock_db.db_type = "mariadb"
		self.assertTrue(is_mysql())
		self.assertFalse(is_postgres())

	@patch("uzbek_payments.db_utils.is_postgres")
	def test_get_table_name_postgres(self, mock_is_postgres):
		"""Test table name formatting for PostgreSQL"""
		mock_is_postgres.return_value = True
		result = get_table_name("tabPayment Entry")
		self.assertEqual(result, '"tabPayment Entry"')

	@patch("uzbek_payments.db_utils.is_postgres")
	def test_get_table_name_mysql(self, mock_is_postgres):
		"""Test table name formatting for MySQL"""
		mock_is_postgres.return_value = False
		result = get_table_name("tabPayment Entry")
		self.assertEqual(result, "`tabPayment Entry`")


if __name__ == "__main__":
	unittest.main()
