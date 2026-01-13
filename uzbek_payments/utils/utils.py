import frappe
from frappe import _


def after_install():
	"""Called after app installation"""
	create_payment_gateways()


def create_payment_gateways():
	"""Create payment gateway records for Uzbek payment systems"""
	from payments.utils import create_payment_gateway

	# Create Payme gateway
	create_payment_gateway(
		gateway="Payme",
		settings="Payme Settings",
		controller="PaymeSettings",
	)

	# Create Click gateway
	create_payment_gateway(
		gateway="Click",
		settings="Click Settings",
		controller="ClickSettings",
	)

	# Create FreedomPay gateway
	create_payment_gateway(
		gateway="FreedomPay",
		settings="FreedomPay Settings",
		controller="FreedomPaySettings",
	)

	frappe.msgprint(_("Uzbek payment gateways created successfully"))
