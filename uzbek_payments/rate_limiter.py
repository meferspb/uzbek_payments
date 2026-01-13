# Copyright (c) 2026, Viktor Krasnikov
# License: MIT. See LICENSE

"""
Rate limiter for payment callbacks
"""

import time
import frappe
from collections import defaultdict
from functools import wraps
from typing import Optional


class CallbackRateLimiter:
	"""Rate limiter for payment callbacks"""

	def __init__(self, max_calls: int = 10, period: int = 60):
		"""
		Initialize rate limiter
		
		Args:
			max_calls: Maximum number of calls per period
			period: Time period in seconds
		"""
		self.max_calls = max_calls
		self.period = period
		self.calls = defaultdict(list)

	def check_rate_limit(self, ip_address: str) -> bool:
		"""
		Check if rate limit is exceeded
		
		Args:
			ip_address: IP address
			
		Returns:
			True if within limit, False otherwise
		"""
		now = time.time()
		ip_calls = self.calls[ip_address]
		
		# Remove old calls
		ip_calls[:] = [call_time for call_time in ip_calls if now - call_time < self.period]
		
		if len(ip_calls) >= self.max_calls:
			return False
		
		ip_calls.append(now)
		return True

	def rate_limit_callback(self, func):
		"""
		Decorator for rate limiting callbacks
		
		Args:
			func: Callback function
			
		Returns:
			Wrapped function
		"""
		@wraps(func)
		def wrapper(*args, **kwargs):
			try:
				ip_address = frappe.local.request.remote_addr if hasattr(frappe.local, 'request') else "unknown"
			except (AttributeError, KeyError, TypeError):
				ip_address = "unknown"
			
			if not self.check_rate_limit(ip_address):
				frappe.throw(
					"Rate limit exceeded. Please try again later.",
					exc=frappe.RateLimitExceeded
				)
			
			return func(*args, **kwargs)
		
		return wrapper


# Global rate limiter instance
callback_rate_limiter = CallbackRateLimiter()
