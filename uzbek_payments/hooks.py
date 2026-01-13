from . import __version__ as app_version

app_name = "uzbek_payments"
app_title = "Uzbek Payments"
app_publisher = "Frappe Technologies"
app_description = "Payment gateway integrations for Uzbek payment systems (Payme, Click)"
app_email = "hello@frappe.io"
app_license = "MIT"

# Installation
after_install = "uzbek_payments.utils.after_install"

# Scheduler Events
scheduler_events = {
	"all": [
		"uzbek_payments.payment_gateways.doctype.payme_settings.payme_settings.check_payment_status",
	],
}
