# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Webhook retry mechanism for failed payment callbacks
"""

import frappe
from datetime import datetime
from typing import Dict, Any


class WebhookRetry:
	"""Retry mechanism for failed webhooks"""

	MAX_RETRIES = 3
	RETRY_DELAYS = [60, 300, 900]  # 1 min, 5 min, 15 min

	@staticmethod
	def schedule_retry(integration_request_name: str, retry_count: int = 0):
		"""
		Schedule webhook retry
		
		Args:
			integration_request_name: Integration request name
			retry_count: Current retry count
		"""
		if retry_count >= WebhookRetry.MAX_RETRIES:
			frappe.log_error(
				f"Webhook retry limit exceeded for {integration_request_name}",
				"Webhook Retry Error"
			)
			return

		delay = WebhookRetry.RETRY_DELAYS[retry_count] if retry_count < len(WebhookRetry.RETRY_DELAYS) else 900

		frappe.enqueue(
			"uzbek_payments.webhook_retry.process_webhook_retry",
			integration_request_name=integration_request_name,
			retry_count=retry_count + 1,
			queue="long",
			timeout=300,
			delay=delay
		)

	@staticmethod
	def process_webhook_retry(integration_request_name: str, retry_count: int):
		"""
		Process webhook with retry
		
		Args:
			integration_request_name: Integration request name
			retry_count: Current retry count
		"""
		try:
			ir = frappe.get_doc("Integration Request", integration_request_name)
			
			if ir.status == "Completed":
				# Already processed, no need to retry
				return
			
			# Re-process callback based on gateway
			gateway_name = ir.integration_request_service
			
			# Get callback function
			if gateway_name == "Payme":
				callback_func = frappe.get_attr(
					"uzbek_payments.payment_gateways.doctype.payme_settings.payme_settings.callback"
				)
			elif gateway_name == "Click":
				callback_func = frappe.get_attr(
					"uzbek_payments.payment_gateways.doctype.click_settings.click_settings.callback"
				)
			elif gateway_name == "FreedomPay":
				callback_func = frappe.get_attr(
					"uzbek_payments.payment_gateways.doctype.freedompay_settings.freedompay_settings.callback"
				)
			else:
				frappe.log_error(
					f"Unknown gateway for retry: {gateway_name}",
					"Webhook Retry Error"
				)
				return
			
			# Reconstruct callback data from integration request
			data = frappe.parse_json(ir.data)
			if not data:
				frappe.log_error(
					f"Invalid or empty data in Integration Request {integration_request_name}",
					"Webhook Retry Error"
				)
				return
			
			# Set form_dict for callback processing
			if not hasattr(frappe.local, 'form_dict'):
				frappe.local.form_dict = {}
			frappe.local.form_dict.update(data)
			
			# Process callback
			result = callback_func()
			
			# Check result
			if result and (
				result.get("result", {}).get("status") == "success" or
				result.get("error") == 0 or
				result.get("status") == "success"
			):
				# Success - update integration request
				ir.status = "Completed"
				ir.save(ignore_permissions=True)
				frappe.db.commit()
			else:
				# Still failed - schedule another retry
				WebhookRetry.schedule_retry(integration_request_name, retry_count)
				
		except Exception as e:
			frappe.log_error(
				f"Error processing webhook retry: {str(e)}",
				"Webhook Retry Error"
			)
			WebhookRetry.schedule_retry(integration_request_name, retry_count)
