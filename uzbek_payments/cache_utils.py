# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Cache utilities for payment gateways
"""

import frappe
from typing import Optional, Dict, Any


class SettingsCache:
	"""Cache for payment gateway settings"""

	@staticmethod
	def get_settings(gateway_name: str) -> Optional[Dict[str, Any]]:
		"""
		Get cached gateway settings
		
		Args:
			gateway_name: Gateway name (Payme, Click, FreedomPay)
			
		Returns:
			Cached settings or None
		"""
		cache_key = f"payment_gateway_settings_{gateway_name}"
		settings = frappe.cache().get(cache_key)
		
		if settings:
			return settings
		
		# Load from database
		try:
			settings_doc = frappe.get_doc(f"{gateway_name} Settings")
			settings = {
				"merchant_id": settings_doc.merchant_id,
			}
			
			# Add gateway-specific fields
			if gateway_name == "Payme":
				settings["merchant_key"] = settings_doc.get_password("merchant_key")
			elif gateway_name == "Click":
				settings["merchant_id"] = settings_doc.merchant_id
				settings["service_id"] = settings_doc.service_id
				settings["secret_key"] = settings_doc.get_password("secret_key")
			elif gateway_name == "FreedomPay":
				settings["merchant_id"] = settings_doc.merchant_id
				settings["terminal_id"] = settings_doc.terminal_id
				settings["secret_key"] = settings_doc.get_password("secret_key")
			
			# Cache for 1 hour
			frappe.cache().setex(cache_key, 3600, settings)
			
			return settings
		except Exception as e:
			frappe.log_error(
				f"Error loading settings for {gateway_name}: {str(e)}",
				"Settings Cache Error"
			)
			return None

	@staticmethod
	def clear_cache(gateway_name: str):
		"""
		Clear gateway settings cache
		
		Args:
			gateway_name: Gateway name
		"""
		cache_key = f"payment_gateway_settings_{gateway_name}"
		frappe.cache().delete(cache_key)
