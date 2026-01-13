# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Idempotency handling for payments
"""

import frappe
from typing import Optional, Dict, Any
from datetime import datetime


class PaymentIdempotency:
	"""Handle payment idempotency"""

	@staticmethod
	def check_existing_payment(gateway_name: str, order_id: str) -> Optional[Dict[str, Any]]:
		"""
		Check for existing payment with same order_id
		
		Args:
			gateway_name: Payment gateway name
			order_id: Order ID
			
		Returns:
			Existing payment data or None
		"""
		if not order_id:
			return None
		
		# Escape order_id to prevent SQL injection
		# frappe.db.escape() handles escaping for both PostgreSQL and MySQL
		# It returns a quoted string, so we use it directly in the LIKE pattern
		escaped_order_id = frappe.db.escape(order_id)
		
		existing = frappe.get_all(
			"Integration Request",
			filters={
				"integration_request_service": gateway_name,
				"data": ["like", f'%"order_id": {escaped_order_id}%'],
				"status": ["in", ["Queued", "Completed"]]
			},
			fields=["name", "data", "status"],
			limit=1
		)
		
		if existing:
			ir = frappe.get_doc("Integration Request", existing[0].name)
			data = frappe.parse_json(ir.data)
			return {
				"payment_url": data.get("payment_url"),
				"status": ir.status,
				"integration_request": ir.name
			}
		
		return None

	@staticmethod
	def generate_idempotency_key(gateway_name: str, order_id: str) -> str:
		"""
		Generate idempotency key
		
		Args:
			gateway_name: Payment gateway name
			order_id: Order ID
			
		Returns:
			Idempotency key
		"""
		timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
		return f"{gateway_name}_{order_id}_{timestamp}"

	@staticmethod
	def store_idempotency_key(integration_request_name: str, idempotency_key: str):
		"""
		Store idempotency key in integration request
		
		Args:
			integration_request_name: Integration request name
			idempotency_key: Idempotency key
		"""
		try:
			ir = frappe.get_doc("Integration Request", integration_request_name)
			data = frappe.parse_json(ir.data) or {}
			data["idempotency_key"] = idempotency_key
			ir.data = frappe.as_json(data)
			ir.save(ignore_permissions=True)
			frappe.db.commit()
		except Exception as e:
			frappe.log_error(
				f"Error storing idempotency key: {str(e)}",
				"Idempotency Error"
			)
