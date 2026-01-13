# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Tests for module integrations
"""

import unittest
from unittest.mock import patch, MagicMock

import frappe
from frappe.tests.utils import FrappeTestCase

from uzbek_payments.integrations import (
	_is_module_installed,
	integrate_with_accounting,
	integrate_with_banking,
	get_available_integrations,
)


class TestIntegrations(FrappeTestCase):
	"""Tests for module integrations"""

	@patch("uzbek_payments.integrations.frappe.db.exists")
	def test_is_module_installed_true(self, mock_exists):
		"""Test module installation check - installed"""
		mock_exists.return_value = True
		
		with patch("uzbek_payments.integrations.frappe.get_doc") as mock_get_doc:
			mock_module = MagicMock()
			mock_module.get.return_value = False
			mock_get_doc.return_value = mock_module
			
			result = _is_module_installed("Uzbek Banking")
			self.assertTrue(result)

	@patch("uzbek_payments.integrations.frappe.db.exists")
	def test_is_module_installed_false(self, mock_exists):
		"""Test module installation check - not installed"""
		mock_exists.return_value = False
		
		result = _is_module_installed("Uzbek Banking")
		self.assertFalse(result)

	def test_integrate_with_accounting(self):
		"""Test accounting integration"""
		payment_data = {"name": "PE-00001", "amount": 1000}
		try:
			integrate_with_accounting(payment_data)
		except Exception:
			self.fail("integrate_with_accounting raised an exception")

	@patch("uzbek_payments.integrations._is_module_installed")
	def test_integrate_with_banking_installed(self, mock_is_installed):
		"""Test banking integration when module is installed"""
		mock_is_installed.return_value = True
		
		bank_transaction_data = {"name": "BT-00001", "amount": 1000}
		try:
			integrate_with_banking(bank_transaction_data)
		except Exception:
			self.fail("integrate_with_banking raised an exception")

	@patch("uzbek_payments.integrations._is_module_installed")
	def test_get_available_integrations(self, mock_is_installed):
		"""Test getting available integrations"""
		mock_is_installed.return_value = True
		
		result = get_available_integrations()
		self.assertIn("accounting", result)
		self.assertIn("banking", result)
		self.assertTrue(result["accounting"])  # Always available
		self.assertTrue(result["banking"])


if __name__ == "__main__":
	unittest.main()
