# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
API response validators
"""

import frappe
from typing import Dict, Any
from frappe import _


class APIResponseValidator:
	"""Validate API responses"""

	@staticmethod
	def validate_payme_response(response: Dict[str, Any]) -> bool:
		"""
		Validate Payme API response
		
		Args:
			response: API response
			
		Returns:
			True if valid
		"""
		if not response:
			frappe.throw(_("Empty response from Payme API"))
		
		if "result" not in response:
			frappe.throw(_("Invalid Payme API response format"))
		
		result = response.get("result", {})
		
		if "checkout_url" not in result:
			frappe.throw(_("Missing checkout_url in Payme response"))
		
		if "id" not in result:
			frappe.throw(_("Missing payment id in Payme response"))
		
		return True

	@staticmethod
	def validate_click_response(response: Dict[str, Any]) -> bool:
		"""
		Validate Click API response
		
		Args:
			response: API response
			
		Returns:
			True if valid
		"""
		if not response:
			frappe.throw(_("Empty response from Click API"))
		
		if "click_trans_id" not in response:
			frappe.throw(_("Missing click_trans_id in Click response"))
		
		if "payment_url" not in response and "redirect_url" not in response:
			frappe.throw(_("Missing payment URL in Click response"))
		
		return True

	@staticmethod
	def validate_freedompay_response(response: Dict[str, Any]) -> bool:
		"""
		Validate FreedomPay API response
		
		Args:
			response: API response
			
		Returns:
			True if valid
		"""
		if not response:
			frappe.throw(_("Empty response from FreedomPay API"))
		
		if "payment_url" not in response:
			frappe.throw(_("Missing payment_url in FreedomPay response"))
		
		if "payment_id" not in response:
			frappe.throw(_("Missing payment_id in FreedomPay response"))
		
		return True
