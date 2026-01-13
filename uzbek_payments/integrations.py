# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Integration with other Frappe modules
"""

from typing import Any, Dict, Optional

import frappe
from frappe import _


def _is_module_installed(module_name: str) -> bool:
	"""
	Check if module is installed
	
	Args:
		module_name: Module name
		
	Returns:
		True if module is installed
	"""
	try:
		if not frappe.db.exists("Module Def", module_name):
			return False
		
		module = frappe.get_doc("Module Def", module_name)
		return not module.get("disabled", False)
	except Exception:
		return False


def integrate_with_accounting(payment_data: Dict[str, Any]) -> None:
	"""
	Integrate with accounting module
	
	Args:
		payment_data: Payment data
	"""
	try:
		# Integration with accounting is already implemented through Payment Entry
		# Additional integration can be added here
		
		# Example: Auto-create journal entries for commissions
		if payment_data.get("create_commission_entry"):
			# Logic for creating commission entries can be added here
			pass
	except Exception as e:
		frappe.log_error(
			message=f"Error in accounting integration: {str(e)}",
			title="Accounting Integration Error"
		)


def integrate_with_banking(bank_transaction_data: Dict[str, Any]) -> None:
	"""
	Integrate with banking module
	
	Args:
		bank_transaction_data: Bank transaction data
	"""
	try:
		# Check if uzbek_banking module is installed
		if not _is_module_installed("Uzbek Banking"):
			return
		
		# Additional integration logic can be added here
		# Example: Sync payment transactions with bank statements
		payment_entry = bank_transaction_data.get("payment_entry")
		if payment_entry and frappe.db.exists("Payment Entry", payment_entry):
			# Logic for syncing with bank statements can be added here
			pass
	except Exception as e:
		frappe.log_error(
			message=f"Error in banking integration: {str(e)}",
			title="Banking Integration Error"
		)


def integrate_with_analytics(payment_data: Dict[str, Any]) -> None:
	"""
	Integrate with analytics module
	
	Args:
		payment_data: Payment data
	"""
	try:
		# Check if analytics module is installed
		if not _is_module_installed("Analytics"):
			return
		
		# Additional integration logic can be added here
		# Example: Send payment data to analytics module
		pass
	except Exception as e:
		frappe.log_error(
			message=f"Error in analytics integration: {str(e)}",
			title="Analytics Integration Error"
		)


@frappe.whitelist()
def get_available_integrations() -> Dict[str, bool]:
	"""
	Get list of available integrations
	
	Returns:
		Dictionary with available integrations
	"""
	return {
		"accounting": True,  # Always available through ERPNext
		"banking": _is_module_installed("Uzbek Banking"),
		"analytics": _is_module_installed("Analytics"),
	}
