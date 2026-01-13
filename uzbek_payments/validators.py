# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Input validators for payment gateways
"""

import re
from typing import Optional

import frappe
from frappe import _


def validate_payment_amount(amount: float, currency: str = "UZS") -> bool:
	"""
	Validate payment amount
	
	Args:
		amount: Payment amount
		currency: Currency code
		
	Returns:
		True if valid
	"""
	if amount <= 0:
		frappe.throw(_("Payment amount must be greater than 0"))
	
	# Minimum amount in UZS (1000 UZS = 10.00)
	min_amount = 1000
	if amount < min_amount:
		frappe.throw(_("Payment amount must be at least {0} UZS").format(min_amount))
	
	# Maximum amount in UZS (100,000,000 UZS = 1,000,000.00)
	max_amount = 100000000
	if amount > max_amount:
		frappe.throw(_("Payment amount must not exceed {0} UZS").format(max_amount))
	
	# Check for reasonable precision (2 decimal places)
	if round(amount, 2) != amount:
		frappe.throw(_("Payment amount must have at most 2 decimal places"))
	
	return True


def validate_order_id(order_id: str) -> bool:
	"""
	Validate order ID
	
	Args:
		order_id: Order ID
		
	Returns:
		True if valid
		
	Note:
		This function validates order_id format but does not modify it.
		Use sanitize_payment_data() to sanitize the order_id if needed.
	"""
	if not order_id:
		frappe.throw(_("Order ID is required"))
	
	# Basic format validation
	if len(order_id) > 100:
		frappe.throw(_("Order ID must be less than 100 characters"))
	
	# Check for invalid characters (but don't modify - validation only)
	if not re.match(r'^[\w\-_]+$', order_id):
		frappe.throw(_("Order ID contains invalid characters. Only alphanumeric characters, hyphens and underscores are allowed."))
	
	return True


def sanitize_payment_data(data: dict) -> dict:
	"""
	Sanitize payment data
	
	Args:
		data: Payment data dictionary
		
	Returns:
		Sanitized data
	"""
	sanitized = {}
	
	for key, value in data.items():
		if isinstance(value, str):
			# Remove null bytes and control characters
			value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
			# Limit length
			if len(value) > 1000:
				value = value[:1000]
		sanitized[key] = value
	
	return sanitized
