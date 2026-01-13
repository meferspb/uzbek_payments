# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
# Integrating Payme (payme.uz)

Payme is one of the most popular payment systems in Uzbekistan.

### Setup

1. Register at https://payme.uz
2. Get your Merchant ID and Key
3. Configure in Payme Settings

### Usage

Example:

	from payments.utils import get_payment_gateway_controller

	controller = get_payment_gateway_controller("Payme")
	controller().validate_transaction_currency("UZS")

	payment_details = {
		"amount": 100000,  # Amount in tiyin (1 UZS = 100 tiyin)
		"title": "Payment for Order #123",
		"description": "Payment via Payme",
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

Payme will send callback to: /api/method/uzbek_payments.payment_gateways.doctype.payme_settings.payme_settings.callback

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


class PaymeSettings(Document):
	"""Settings for Payme payment gateway"""

	supported_currencies = ("UZS",)

	def validate(self):
		create_payment_gateway("Payme")
		call_hook_method("payment_gateway_enabled", gateway="Payme")
		if not self.flags.ignore_mandatory:
			self.validate_credentials()

	def validate_credentials(self):
		"""Validate Payme credentials"""
		if self.merchant_id and self.merchant_key:
			# Test connection with Payme API
			try:
				# Payme API endpoint for testing
				test_url = "https://checkout.paycom.uz/api"
				# This is a placeholder - actual validation depends on Payme API
				pass
			except Exception:
				frappe.throw(_("Invalid Payme credentials. Please check Merchant ID and Key."))

	def validate_transaction_currency(self, currency):
		"""Validate if currency is supported"""
		if currency not in self.supported_currencies:
			frappe.throw(
				_("Payme only supports UZS currency. Please select UZS for payment.")
			)

	def get_payment_url(self, **kwargs):
		"""Generate payment URL for Payme checkout"""
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
			existing = PaymentIdempotency.check_existing_payment("Payme", order_id)
			if existing and existing.get("payment_url"):
				return existing["payment_url"]
			
			# Convert amount to tiyin (Payme uses tiyin, 1 UZS = 100 tiyin)
			amount_uzs = amount
			amount_tiyin = int(amount_uzs * 100)

			# Create integration request
			integration_request = create_request_log(kwargs, service_name="Payme")

			# Prepare payment data
			payment_data = {
				"merchant_id": self.merchant_id,
				"amount": amount_tiyin,
				"account": {
					"order_id": kwargs.get("order_id"),
					"reference_doctype": kwargs.get("reference_doctype"),
					"reference_docname": kwargs.get("reference_docname"),
				},
				"callback_url": get_url(
					f"/api/method/uzbek_payments.payment_gateways.doctype.payme_settings.payme_settings.callback"
				),
				"description": kwargs.get("description", kwargs.get("title", "Payment")),
			}

			# Create payment request
			payment_request = self.create_payment_request(payment_data)
			
			# Validate response
			APIResponseValidator.validate_payme_response(payment_request)

			if payment_request and payment_request.get("result", {}).get("checkout_url"):
				# Update integration request with payment ID
				integration_request_dict = frappe.parse_json(integration_request.data)
				integration_request_dict["payme_payment_id"] = payment_request.get("result", {}).get("id")
				integration_request_dict["payment_url"] = payment_request.get("result", {}).get("checkout_url")
				
				# Store idempotency key
				idempotency_key = PaymentIdempotency.generate_idempotency_key("Payme", order_id)
				integration_request_dict["idempotency_key"] = idempotency_key
				
				integration_request.data = frappe.as_json(integration_request_dict)
				integration_request.save(ignore_permissions=True)
				frappe.db.commit()
				
				PaymentIdempotency.store_idempotency_key(integration_request.name, idempotency_key)

				return payment_request.get("result", {}).get("checkout_url")
			else:
				frappe.throw(_("Failed to create Payme payment request"))

		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Payme Payment URL Error")
			frappe.throw(_("Could not generate Payme payment URL: {0}").format(str(e)))

	def create_payment_request(self, payment_data):
		"""Create payment request in Payme system"""
		url = "https://checkout.paycom.uz/api"

		headers = {
			"Content-Type": "application/json",
			"X-Auth": self.merchant_key,
		}

		try:
			response = make_post_request(
				url=url,
				json=payment_data,
				headers=headers,
			)

			return response
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Payme Create Payment Request Error")
			raise

	def verify_signature(self, data, signature):
		"""Verify Payme callback signature"""
		# Payme uses HMAC SHA256 for signature verification
		expected_signature = hmac.new(
			key=self.merchant_key.encode("utf-8"),
			msg=json.dumps(data, sort_keys=True).encode("utf-8"),
			digestmod=hashlib.sha256,
		).hexdigest()

		return hmac.compare_digest(expected_signature, signature)

	@frappe.whitelist()
	def clear(self):
		"""Clear sensitive data"""
		self.merchant_id = self.merchant_key = None
		self.flags.ignore_mandatory = True
		self.save()


@frappe.whitelist(allow_guest=True)
@frappe.get_attr("uzbek_payments.rate_limiter.callback_rate_limiter").rate_limit_callback
def callback():
	"""Handle Payme payment callback"""
	from uzbek_payments.lock_utils import payment_lock
	from uzbek_payments.webhook_retry import WebhookRetry
	
	callback_start_time = time.time()
	
	try:
		data = frappe.local.form_dict
		headers = frappe.request.headers

		# Get signature from headers
		signature = headers.get("X-Payme-Signature") or headers.get("Authorization")

		if not signature:
			frappe.throw(_("Missing signature in callback"))

		# Get Payme settings
		settings = frappe.get_doc("Payme Settings")

		# Verify signature
		if not settings.verify_signature(data, signature):
			frappe.throw(_("Invalid signature"), exc=frappe.PermissionError)

		# Process callback
		payment_id = data.get("id")
		account_data = data.get("account", {})
		order_id = account_data.get("order_id") if account_data else None
		status = data.get("status")
		
		# Prepare lock key safely
		lock_key = order_id or payment_id or str(payment_id) if payment_id else "unknown"
		
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
						"integration_request_service": "Payme",
						"data": ["like", f'%"order_id": {escaped_order_id}%'],
					},
					fields=["name", "data", "reference_doctype", "reference_docname"],
					order_by="creation desc",
					limit=1,
				)
			
			# If not found by order_id, try to find by payment_id
			if not integration_requests and payment_id:
				# Escape payment_id to prevent SQL injection
				escaped_payment_id = frappe.db.escape(str(payment_id))
				integration_requests = frappe.get_all(
					"Integration Request",
					filters={
						"integration_request_service": "Payme",
						"data": ["like", f'%"payme_payment_id": {escaped_payment_id}%'],
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
					"payme_payment_id": payment_id,
					"status": status,
				}
			)

			integration_request.data = frappe.as_json(integration_request_dict)

			# Handle payment status
			if status == "paid" or status == "completed":
				integration_request.status = "Completed"
				integration_request.save(ignore_permissions=True)
				frappe.db.commit()

				# Record metrics for successful payment
				duration = time.time() - callback_start_time
				amount = integration_request_dict.get("amount", 0) / 100 if integration_request_dict.get("amount") else 0
				PaymentMetrics.record_payment("Payme", amount, "Completed", duration, None)

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
						frappe.log_error(frappe.get_traceback(), "Payme Callback - Document Processing Error")

				return {"result": {"status": "success"}}
			else:
				integration_request.status = "Failed"
				integration_request.error = f"Payment status: {status}"
				integration_request.save(ignore_permissions=True)
				frappe.db.commit()
				
				# Record metrics for failed payment
				duration = time.time() - callback_start_time
				amount = integration_request_dict.get("amount", 0) / 100 if integration_request_dict.get("amount") else 0
				PaymentMetrics.record_payment("Payme", amount, "Failed", duration, f"Status: {status}")
				
				# Schedule retry for failed webhook
				WebhookRetry.schedule_retry(integration_request.name, 0)

				return {"result": {"status": "failed", "message": f"Payment {status}"}}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Payme Callback Error")
		
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
		
		return {"result": {"status": "error", "message": str(e)}}


@frappe.whitelist()
def check_payment_status():
	"""Scheduled job to check payment status"""
	# This can be used to periodically check payment status
	# for pending payments
	pass
