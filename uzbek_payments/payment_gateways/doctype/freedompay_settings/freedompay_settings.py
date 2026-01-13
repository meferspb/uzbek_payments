# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
# Integrating FreedomPay (freedompay.uz)

FreedomPay is a payment system in Uzbekistan.

### Setup

1. Register at https://freedompay.uz
2. Get your Merchant ID, Terminal ID, and Secret Key
3. Configure in FreedomPay Settings

### Usage

Example:

	from payments.utils import get_payment_gateway_controller

	controller = get_payment_gateway_controller("FreedomPay")
	controller().validate_transaction_currency("UZS")

	payment_details = {
		"amount": 100000,  # Amount in UZS (will be converted to tiyin)
		"title": "Payment for Order #123",
		"description": "Payment via FreedomPay",
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

FreedomPay will send callback to: /api/method/uzbek_payments.payment_gateways.doctype.freedompay_settings.freedompay_settings.callback

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


class FreedomPaySettings(Document):
	"""Settings for FreedomPay payment gateway"""

	supported_currencies = ("UZS",)

	def validate(self):
		create_payment_gateway("FreedomPay")
		call_hook_method("payment_gateway_enabled", gateway="FreedomPay")
		if not self.flags.ignore_mandatory:
			self.validate_credentials()

	def validate_credentials(self):
		"""Validate FreedomPay credentials"""
		if self.merchant_id and self.terminal_id and self.secret_key:
			# Test connection with FreedomPay API
			try:
				# FreedomPay API endpoint for testing
				# This is a placeholder - actual validation depends on FreedomPay API
				pass
			except Exception:
				frappe.throw(
					_(
						"Invalid FreedomPay credentials. Please check Merchant ID, Terminal ID, and Secret Key."
					)
				)

	def validate_transaction_currency(self, currency):
		"""Validate if currency is supported"""
		if currency not in self.supported_currencies:
			frappe.throw(
				_("FreedomPay only supports UZS currency. Please select UZS for payment.")
			)

	def get_payment_url(self, **kwargs):
		"""Generate payment URL for FreedomPay checkout"""
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
			existing = PaymentIdempotency.check_existing_payment("FreedomPay", order_id)
			if existing and existing.get("payment_url"):
				return existing["payment_url"]
			
			# Convert amount to tiyin (FreedomPay uses tiyin, 1 UZS = 100 tiyin)
			amount_uzs = amount
			amount_tiyin = int(amount_uzs * 100)

			# Create integration request
			integration_request = create_request_log(kwargs, service_name="FreedomPay")

			# Prepare payment data
			payment_data = {
				"merchant_id": self.merchant_id,
				"terminal_id": self.terminal_id,
				"amount": amount_tiyin,
				"order_id": kwargs.get("order_id"),
				"description": kwargs.get("description", kwargs.get("title", "Payment")),
				"return_url": kwargs.get("redirect_to")
				or get_url("/payment-success"),
				"callback_url": get_url(
					f"/api/method/uzbek_payments.payment_gateways.doctype.freedompay_settings.freedompay_settings.callback"
				),
			}

			# Generate signature
			signature = self.generate_signature(payment_data)
			payment_data["signature"] = signature

			# Create payment request
			payment_request = self.create_payment_request(payment_data)
			
			# Validate response
			APIResponseValidator.validate_freedompay_response(payment_request)

			if payment_request and payment_request.get("payment_url"):
				# Update integration request with payment ID
				integration_request_dict = frappe.parse_json(integration_request.data)
				integration_request_dict["freedompay_payment_id"] = payment_request.get("payment_id")
				integration_request_dict["freedompay_transaction_id"] = payment_request.get(
					"transaction_id"
				)
				integration_request_dict["payment_url"] = payment_request.get("payment_url")
				
				# Store idempotency key
				idempotency_key = PaymentIdempotency.generate_idempotency_key("FreedomPay", order_id)
				integration_request_dict["idempotency_key"] = idempotency_key
				
				integration_request.data = frappe.as_json(integration_request_dict)
				integration_request.save(ignore_permissions=True)
				frappe.db.commit()
				
				PaymentIdempotency.store_idempotency_key(integration_request.name, idempotency_key)

				return payment_request.get("payment_url")
			else:
				frappe.throw(_("Failed to create FreedomPay payment request"))

		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "FreedomPay Payment URL Error")
			frappe.throw(_("Could not generate FreedomPay payment URL: {0}").format(str(e)))

	def generate_signature(self, data):
		"""Generate signature for FreedomPay request"""
		# FreedomPay typically uses HMAC SHA256 or MD5 for signatures
		# Adjust based on actual API documentation
		sign_string = (
			f"{data['merchant_id']}"
			f"{data['terminal_id']}"
			f"{data['amount']}"
			f"{data['order_id']}"
			f"{self.secret_key}"
		)

		# Using SHA256 (adjust if FreedomPay uses different algorithm)
		signature = hmac.new(
			key=self.secret_key.encode("utf-8"),
			msg=sign_string.encode("utf-8"),
			digestmod=hashlib.sha256,
		).hexdigest()

		return signature

	def create_payment_request(self, payment_data):
		"""Create payment request in FreedomPay system"""
		# Adjust URL based on actual FreedomPay API endpoint
		url = self.api_endpoint or "https://api.freedompay.uz/payment/create"

		headers = {
			"Content-Type": "application/json",
			"Accept": "application/json",
		}

		try:
			response = make_post_request(
				url=url,
				json=payment_data,
				headers=headers,
			)

			return response
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "FreedomPay Create Payment Request Error")
			raise

	def verify_signature(self, data, signature):
		"""Verify FreedomPay callback signature"""
		# Build sign string from callback data
		sign_string = (
			f"{data.get('merchant_id')}"
			f"{data.get('terminal_id')}"
			f"{data.get('transaction_id')}"
			f"{data.get('order_id')}"
			f"{data.get('amount')}"
			f"{data.get('status')}"
			f"{self.secret_key}"
		)

		# Generate expected signature
		expected_signature = hmac.new(
			key=self.secret_key.encode("utf-8"),
			msg=sign_string.encode("utf-8"),
			digestmod=hashlib.sha256,
		).hexdigest()

		return hmac.compare_digest(expected_signature, signature)

	@frappe.whitelist()
	def clear(self):
		"""Clear sensitive data"""
		self.merchant_id = self.terminal_id = self.secret_key = None
		self.flags.ignore_mandatory = True
		self.save()


@frappe.whitelist(allow_guest=True)
def callback():
	"""Handle FreedomPay payment callback"""
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
		headers = frappe.request.headers

		# Get signature from headers or data
		signature = (
			headers.get("X-FreedomPay-Signature")
			or headers.get("Signature")
			or data.get("signature")
		)

		if not signature:
			frappe.throw(_("Missing signature in callback"))

		# Get FreedomPay settings
		settings = frappe.get_doc("FreedomPay Settings")

		# Verify signature
		if not settings.verify_signature(data, signature):
			frappe.throw(_("Invalid signature"), exc=frappe.PermissionError)

		# Process callback
		transaction_id = data.get("transaction_id")
		order_id = data.get("order_id")
		status = data.get("status")
		amount = data.get("amount")
		
		# Prepare lock key safely
		lock_key = order_id or transaction_id or str(transaction_id) if transaction_id else "unknown"
		
		# Use lock to prevent race conditions
		with payment_lock(lock_key):
			# Find integration request - escape order_id to prevent SQL injection
			integration_requests = []
			if order_id:
				# Escape order_id to prevent SQL injection
				escaped_order_id = frappe.db.escape(order_id)
				integration_requests = frappe.get_all(
					"Integration Request",
					filters={
						"integration_request_service": "FreedomPay",
						"data": ["like", f'%"order_id": {escaped_order_id}%'],
					},
					fields=["name", "data", "reference_doctype", "reference_docname"],
					order_by="creation desc",
					limit=1,
				)
			
			# If not found by order_id, try to find by transaction_id
			if not integration_requests and transaction_id:
				# Escape transaction_id to prevent SQL injection
				escaped_transaction_id = frappe.db.escape(str(transaction_id))
				integration_requests = frappe.get_all(
					"Integration Request",
					filters={
						"integration_request_service": "FreedomPay",
						"data": ["like", f'%"freedompay_transaction_id": {escaped_transaction_id}%'],
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
					"freedompay_transaction_id": transaction_id,
					"status": status,
					"amount": amount,
				}
			)

			integration_request.data = frappe.as_json(integration_request_dict)

			# Handle payment status
			# Adjust status values based on actual FreedomPay API
			if status in ("success", "completed", "paid", "1"):
				integration_request.status = "Completed"
				integration_request.save(ignore_permissions=True)
				frappe.db.commit()

				# Record metrics for successful payment
				duration = time.time() - callback_start_time
				payment_amount = amount or (integration_request_dict.get("amount", 0) / 100 if integration_request_dict.get("amount") else 0)
				PaymentMetrics.record_payment("FreedomPay", payment_amount, "Completed", duration, None)

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
						frappe.log_error(frappe.get_traceback(), "FreedomPay Callback - Document Processing Error")

				return {"status": "success", "message": "Payment processed successfully"}
			else:
				integration_request.status = "Failed"
				integration_request.error = f"Payment status: {status}"
				integration_request.save(ignore_permissions=True)
				frappe.db.commit()
				
				# Record metrics for failed payment
				duration = time.time() - callback_start_time
				payment_amount = amount or (integration_request_dict.get("amount", 0) / 100 if integration_request_dict.get("amount") else 0)
				PaymentMetrics.record_payment("FreedomPay", payment_amount, "Failed", duration, f"Status: {status}")
				
				# Schedule retry for failed webhook
				WebhookRetry.schedule_retry(integration_request.name, 0)

				return {"status": "failed", "message": f"Payment {status}"}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "FreedomPay Callback Error")
		
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
		
		return {"status": "error", "message": str(e)}


@frappe.whitelist()
def check_payment_status():
	"""Scheduled job to check payment status"""
	# This can be used to periodically check payment status
	# for pending payments
	pass
