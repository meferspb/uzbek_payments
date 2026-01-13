# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
# Integrating Click (click.uz)

Click is a popular payment system in Uzbekistan.

### Setup

1. Register at https://my.click.uz
2. Get your Merchant ID, Service ID, and Secret Key
3. Configure in Click Settings

### Usage

Example:

	from payments.utils import get_payment_gateway_controller

	controller = get_payment_gateway_controller("Click")
	controller().validate_transaction_currency("UZS")

	payment_details = {
		"amount": 100000,  # Amount in tiyin (1 UZS = 100 tiyin)
		"title": "Payment for Order #123",
		"description": "Payment via Click",
		"reference_doctype": "Sales Invoice",
		"reference_docname": "SI-00001",
		"payer_email": "customer@example.com",
		"payer_name": "John Doe",
		"order_id": "ORDER-123",
		"currency": "UZS",
		"redirect_to": "/success",
	}

	url = controller().get_payment_url(**payment_details)

### Callback

Click will send callback to: /api/method/uzbek_payments.payment_gateways.doctype.click_settings.click_settings.callback

"""

import hashlib
import hmac
import json
import time

import frappe
from frappe import _
from frappe.integrations.utils import create_request_log, make_post_request
from frappe.model.document import Document
from frappe.utils import call_hook_method, get_url

from payments.utils import create_payment_gateway
from uzbek_payments.metrics import PaymentMetrics


class ClickSettings(Document):
	"""Settings for Click payment gateway"""

	supported_currencies = ("UZS",)

	def validate(self):
		create_payment_gateway("Click")
		call_hook_method("payment_gateway_enabled", gateway="Click")
		if not self.flags.ignore_mandatory:
			self.validate_credentials()

	def validate_credentials(self):
		"""Validate Click credentials"""
		if self.merchant_id and self.service_id and self.secret_key:
			# Test connection with Click API
			try:
				# Click API endpoint for testing
				# This is a placeholder - actual validation depends on Click API
				pass
			except Exception:
				frappe.throw(
					_("Invalid Click credentials. Please check Merchant ID, Service ID, and Secret Key.")
				)

	def validate_transaction_currency(self, currency):
		"""Validate if currency is supported"""
		if currency not in self.supported_currencies:
			frappe.throw(_("Click only supports UZS currency. Please select UZS for payment."))

	def get_payment_url(self, **kwargs):
		"""Generate payment URL for Click checkout"""
		try:
			from uzbek_payments.validators import validate_payment_amount, validate_order_id
			from uzbek_payments.idempotency import PaymentIdempotency
			from uzbek_payments.api_validators import APIResponseValidator
			
			order_id = kwargs.get("order_id")
			amount = float(kwargs.get("amount", 0))
			
			if not order_id or not amount:
				frappe.throw(_("Missing order ID or amount"))
			
			# Validate inputs
			validate_order_id(order_id)
			validate_payment_amount(amount)
			
			# Check for existing payment (idempotency)
			existing = PaymentIdempotency.check_existing_payment("Click", order_id)
			if existing and existing.get("payment_url"):
				return existing["payment_url"]
			
			# Convert amount to tiyin (Click uses tiyin, 1 UZS = 100 tiyin)
			amount_uzs = amount
			amount_tiyin = int(amount_uzs * 100)

			# Create integration request
			integration_request = create_request_log(kwargs, service_name="Click")

			# Prepare payment data
			payment_data = {
				"merchant_id": self.merchant_id,
				"service_id": self.service_id,
				"amount": amount_tiyin,
				"transaction_param": kwargs.get("order_id"),
				"return_url": kwargs.get("redirect_to") or get_url("/payment-success"),
				"callback_url": get_url(
					f"/api/method/uzbek_payments.payment_gateways.doctype.click_settings.click_settings.callback"
				),
			}

			# Generate signature
			sign_string = f"{payment_data['merchant_id']}{payment_data['service_id']}{payment_data['amount']}{payment_data['transaction_param']}{payment_data['return_url']}{self.secret_key}"
			payment_data["sign_string"] = hashlib.md5(sign_string.encode("utf-8")).hexdigest()

			# Create payment request
			payment_request = self.create_payment_request(payment_data)
			
			# Validate response
			APIResponseValidator.validate_click_response(payment_request)

			if payment_request and payment_request.get("click_trans_id"):
				# Update integration request with payment ID
				integration_request_dict = frappe.parse_json(integration_request.data)
				integration_request_dict["click_trans_id"] = payment_request.get("click_trans_id")
				integration_request_dict["payment_url"] = payment_request.get("payment_url") or payment_request.get("redirect_url")
				
				# Store idempotency key
				idempotency_key = PaymentIdempotency.generate_idempotency_key("Click", order_id)
				integration_request_dict["idempotency_key"] = idempotency_key
				
				integration_request.data = frappe.as_json(integration_request_dict)
				integration_request.save(ignore_permissions=True)
				frappe.db.commit()
				
				PaymentIdempotency.store_idempotency_key(integration_request.name, idempotency_key)

				# Return payment URL
				return payment_request.get("payment_url") or payment_request.get("redirect_url")
			else:
				frappe.throw(_("Failed to create Click payment request"))

		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Click Payment URL Error")
			frappe.throw(_("Could not generate Click payment URL: {0}").format(str(e)))

	def create_payment_request(self, payment_data):
		"""Create payment request in Click system"""
		url = "https://my.click.uz/services/pay"

		headers = {
			"Content-Type": "application/json",
		}

		try:
			response = make_post_request(
				url=url,
				json=payment_data,
				headers=headers,
			)

			return response
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Click Create Payment Request Error")
			raise

	def verify_signature(self, data):
		"""Verify Click callback signature"""
		# Click uses MD5 for signature verification
		merchant_id = data.get("merchant_id")
		service_id = data.get("service_id")
		click_trans_id = data.get("click_trans_id")
		merchant_trans_id = data.get("merchant_trans_id")
		amount = data.get("amount")
		action = data.get("action")
		error = data.get("error")
		error_note = data.get("error_note")
		sign_time = data.get("sign_time")
		sign_string = data.get("sign_string")

		# Build sign string
		sign_string_to_verify = (
			f"{click_trans_id}{service_id}{self.secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
		)

		if error:
			sign_string_to_verify += error

		expected_signature = hashlib.md5(sign_string_to_verify.encode("utf-8")).hexdigest()

		return hmac.compare_digest(expected_signature, sign_string)

	@frappe.whitelist()
	def clear(self):
		"""Clear sensitive data"""
		self.merchant_id = self.service_id = self.secret_key = None
		self.flags.ignore_mandatory = True
		self.save()


@frappe.whitelist(allow_guest=True)
def callback():
	"""Handle Click payment callback"""
	from uzbek_payments.lock_utils import payment_lock
	from uzbek_payments.webhook_retry import WebhookRetry
	from uzbek_payments.rate_limiter import callback_rate_limiter
	
	callback_start_time = time.time()
	
	# Apply rate limiting
	try:
		ip_address = frappe.local.request.remote_addr if hasattr(frappe.local, 'request') else "unknown"
	except (AttributeError, KeyError, TypeError):
		ip_address = "unknown"
	
	if not callback_rate_limiter.check_rate_limit(ip_address):
		from frappe import _
		frappe.throw(
			_("Rate limit exceeded. Please try again later."),
			exc=frappe.ValidationError
		)
	
	try:
		data = frappe.local.form_dict

		# Get Click settings
		settings = frappe.get_doc("Click Settings")

		# Verify signature
		if not settings.verify_signature(data):
			frappe.throw(_("Invalid signature"), exc=frappe.PermissionError)

		# Process callback
		click_trans_id = data.get("click_trans_id")
		merchant_trans_id = data.get("merchant_trans_id")  # This is our order_id
		action = data.get("action")
		error = data.get("error")
		error_note = data.get("error_note")
		
		# Prepare lock key safely
		lock_key = merchant_trans_id or click_trans_id or str(click_trans_id) if click_trans_id else "unknown"
		
		# Use lock to prevent race conditions
		with payment_lock(lock_key):
			# Find integration request - escape merchant_trans_id to prevent SQL injection
			integration_requests = []
			if merchant_trans_id:
				# Escape merchant_trans_id to prevent SQL injection
				escaped_order_id = frappe.db.escape(merchant_trans_id)
				integration_requests = frappe.get_all(
					"Integration Request",
					filters={
						"integration_request_service": "Click",
						"data": ["like", f'%"order_id": {escaped_order_id}%'],
					},
					fields=["name", "data", "reference_doctype", "reference_docname"],
					order_by="creation desc",
					limit=1,
				)
			
			# If not found by order_id, try to find by click_trans_id
			if not integration_requests and click_trans_id:
				# Escape click_trans_id to prevent SQL injection
				escaped_click_trans_id = frappe.db.escape(str(click_trans_id))
				integration_requests = frappe.get_all(
					"Integration Request",
					filters={
						"integration_request_service": "Click",
						"data": ["like", f'%"click_trans_id": {escaped_click_trans_id}%'],
					},
					fields=["name", "data", "reference_doctype", "reference_docname"],
					order_by="creation desc",
					limit=1,
				)

			if not integration_requests:
				frappe.throw(_("Integration Request not found"))

			integration_request = frappe.get_doc("Integration Request", integration_requests[0].name)
			integration_request_dict = frappe.parse_json(integration_request.data) or {}

			# Update with payment information
			integration_request_dict.update(
				{
					"click_trans_id": click_trans_id,
					"action": action,
					"error": error,
					"error_note": error_note,
				}
			)

			integration_request.data = frappe.as_json(integration_request_dict)

			# Handle payment status
			if action == "0" and not error:  # 0 means success in Click
				integration_request.status = "Completed"
				integration_request.save(ignore_permissions=True)
				frappe.db.commit()

				# Record metrics for successful payment
				duration = time.time() - callback_start_time
				amount = integration_request_dict.get("amount", 0) / 100 if integration_request_dict.get("amount") else 0
				PaymentMetrics.record_payment("Click", amount, "Completed", duration, None)

				# Call on_payment_authorized
				if integration_request.reference_doctype and integration_request.reference_docname:
					try:
						doc = frappe.get_doc(
							integration_request.reference_doctype, integration_request.reference_docname
						)
						doc.run_method("on_payment_authorized", "Completed")
						
						# Integrate with accounting and banking modules
						try:
							from uzbek_payments.integrations import integrate_with_accounting, integrate_with_banking
							integrate_with_accounting(doc.as_dict())
							integrate_with_banking({"payment_entry": doc.name})
						except Exception as integration_error:
							# Log integration errors but don't fail the payment
							frappe.log_error(
								message=f"Integration error: {str(integration_error)}",
								title="Payment Integration Error"
							)
					except Exception as doc_error:
						frappe.log_error(frappe.get_traceback(), "Click Callback - Document Processing Error")

				return {"error": 0, "error_note": "Success"}
			else:
				integration_request.status = "Failed"
				integration_request.error = error_note or f"Payment failed: {error}"
				integration_request.save(ignore_permissions=True)
				frappe.db.commit()
				
				# Record metrics for failed payment
				duration = time.time() - callback_start_time
				amount = integration_request_dict.get("amount", 0) / 100 if integration_request_dict.get("amount") else 0
				PaymentMetrics.record_payment("Click", amount, "Failed", duration, error_note or f"Error: {error}")
				
				# Schedule retry for failed webhook
				WebhookRetry.schedule_retry(integration_request.name, 0)

				return {"error": error or -1, "error_note": error_note or "Payment failed"}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Click Callback Error")
		
		# Schedule retry on error
		try:
			if 'integration_request' in locals():
				WebhookRetry.schedule_retry(integration_request.name, 0)
		except (NameError, AttributeError, Exception) as retry_error:
			# Log retry scheduling error but don't fail the callback
			frappe.log_error(
				message=f"Error scheduling webhook retry: {str(retry_error)}",
				title="Webhook Retry Scheduling Error"
			)
		
		return {"error": -1, "error_note": str(e)}
