# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Payment metrics tracking
"""

import frappe
from datetime import datetime
from typing import Dict, Any, Optional, List


class PaymentMetrics:
	"""Track payment metrics"""

	@staticmethod
	def record_payment(
		gateway_name: str,
		amount: float,
		status: str,
		duration: Optional[float] = None,
		error: Optional[str] = None
	):
		"""
		Record payment metrics
		
		Args:
			gateway_name: Payment gateway name
			amount: Payment amount
			status: Payment status
			duration: Processing duration in seconds
			error: Error message if any
		"""
		metrics = {
			"gateway": gateway_name,
			"amount": amount,
			"status": status,
			"duration": duration,
			"error": error,
			"timestamp": datetime.now().isoformat()
		}
		
		# Store in cache
		cache_key = f"payment_metrics_{gateway_name}"
		existing = frappe.cache().get(cache_key) or []
		existing.append(metrics)
		
		# Keep only last 1000 metrics
		if len(existing) > 1000:
			existing = existing[-1000:]
		
		frappe.cache().set(cache_key, existing)

	@staticmethod
	def get_metrics(gateway_name: str, limit: int = 100) -> List[Dict[str, Any]]:
		"""
		Get payment metrics
		
		Args:
			gateway_name: Payment gateway name
			limit: Maximum number of metrics to return
			
		Returns:
			List of metrics
		"""
		cache_key = f"payment_metrics_{gateway_name}"
		metrics = frappe.cache().get(cache_key) or []
		return metrics[-limit:]

	@staticmethod
	@frappe.whitelist()
	def get_summary(gateway_name: str = None) -> Dict[str, Any]:
		"""
		Get payment metrics summary
		
		Args:
			gateway_name: Payment gateway name or None for all
			
		Returns:
			Summary statistics
		"""
		gateways = [gateway_name] if gateway_name else ["Payme", "Click", "FreedomPay"]
		
		result = {}
		for gw in gateways:
			metrics = PaymentMetrics.get_metrics(gw, limit=1000)
			
			if not metrics:
				result[gw] = {
					"total_payments": 0,
					"success_rate": 0,
					"total_amount": 0,
					"average_duration": 0,
					"error_count": 0
				}
				continue
			
			total_payments = len(metrics)
			success_payments = sum(1 for m in metrics if m.get("status") == "Completed")
			error_count = sum(1 for m in metrics if m.get("error"))
			total_amount = sum(m.get("amount", 0) for m in metrics)
			durations = [m.get("duration", 0) for m in metrics if m.get("duration")]
			
			result[gw] = {
				"total_payments": total_payments,
				"success_rate": (success_payments / total_payments * 100) if total_payments > 0 else 0,
				"total_amount": total_amount,
				"average_duration": sum(durations) / len(durations) if durations else 0,
				"error_count": error_count
			}
		
		return result
