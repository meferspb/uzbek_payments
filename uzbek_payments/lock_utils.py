# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Lock utilities for payment processing
"""

import frappe
from contextlib import contextmanager
from typing import Optional
from frappe import _


@contextmanager
def payment_lock(order_id: str, timeout: int = 30):
	"""
	Lock for payment processing to prevent race conditions
	
	Args:
		order_id: Order ID
		timeout: Lock timeout in seconds
		
	Yields:
		None
	"""
	lock_key = f"payment_lock_{order_id}"
	
	# Try to acquire lock
	lock_acquired = frappe.cache().set(
		lock_key,
		frappe.session.user if hasattr(frappe, 'session') else "system",
		ex=timeout,
		nx=True  # Only set if not exists
	)
	
	if not lock_acquired:
		frappe.throw(
			_("Payment is already being processed. Please wait."),
			exc=frappe.ValidationError
		)
	
	try:
		yield
	finally:
		# Release lock
		frappe.cache().delete(lock_key)
