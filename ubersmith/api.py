"""Lower level API, configuration, and HTTP stuff."""

import json
import urlparse
import time
from functools import partial

import httplib2

from ubersmith.exceptions import (
    RequestError,
    ResponseError,
    UpdatingTokenResponse,
)
from ubersmith.utils import append_qs, urlencode_unicode

__all__ = [
    'METHODS',
    'HttpRequestHandler',
    'get_default_request_handler',
    'set_default_request_handler',
]

_DEFAULT_REQUEST_HANDLER = None

"""A dict of all methods returned by uber.method_list()"""
METHODS = {
    u'client.ach_add': u'Add a New Bank Account',
    u'client.ach_delete': u'Delete a Bank Account',
    u'client.ach_update': u'Update a Bank Account',
    u'client.add': u'Add a New Client',
    u'client.cc_add': u'Add a New Credit Card',
    u'client.cc_delete': u'Delete a Credit Card',
    u'client.cc_update': u'Update a Credit Card',
    u'client.comment_list': u"List a Client's Comments",
    u'client.contact_add': u'Add a New Contact',
    u'client.contact_delete': u'Delete a Contact',
    u'client.contact_get': u'Get Contact Details',
    u'client.contact_list': u"List a Client's Contacts",
    u'client.contact_update': u'Update a Contact',
    u'client.count': u'Count Active Clients',
    u'client.credit_add': u'Add an Account Credit',
    u'client.credit_comment_list': u"List a Credit's Comments",
    u'client.credit_deactivate': u'Deactivate an Account Credit',
    u'client.credit_list': u"List a Client's Credits",
    u'client.deactivate': u'Deactivate a Client',
    u'client.domain_add': u'Add a Domain',
    u'client.domain_list': u"List a Client's Domains",
    u'client.domain_lookup': u'Look Up a Domain',
    u'client.domain_register': u'Register a Domain',
    u'client.domain_transfer': u'Transfer a Domain',
    u'client.get': u'Get Client Details',
    u'client.invoice_charge': u'Charge an Invoice',
    u'client.invoice_count': u'Count Invoices',
    u'client.invoice_disregard': u'Disregard an Invoice',
    u'client.invoice_generate': u'Generate an Invoice',
    u'client.invoice_get': u'Get an Invoice',
    u'client.invoice_list': u"List a Client's Invoices",
    u'client.invoice_payments': u"List an Invoice's Payments",
    u'client.invoice_post_gw_payment': u'Record a Payment',
    u'client.latest_client': u'Get the Latest Client',
    u'client.list': u'List Clients',
    u'client.lookup': u'Look Up a Client',
    u'client.metadata_get': u"Get a Client's Metadata",
    u'client.metadata_single': u"Get a Client's Metadata Value",
    u'client.payment_method_list': u"List a Client's Payment Methods",
    u'client.payment_refund': u'Refund a payment.',
    u'client.reactivate': u'Reactivate a Client',
    u'client.renewal_list': u'List Services for Renewal',
    u'client.send_welcome': u'Send a Welcome Letter',
    u'client.service_add': u'Add a New Service',
    u'client.service_comment_list': u"List a Service's Comments",
    u'client.service_deactivate': u'Deactivate a Service',
    u'client.service_get': u'Get a Service',
    u'client.service_list': u"List a Client's Services",
    u'client.service_metadata_get': u"Get a Service's Metadata",
    u'client.service_metadata_single': u"Get a Service's Metadata Value",
    u'client.service_module_call': u'Call a Service Module Function',
    u'client.service_prorate': u'Prorate a Service',
    u'client.service_update': u'Update a Service',
    u'client.set_login': u"Set a Client's Login",
    u'client.update': u'Update a Client',
    u'device.add': u'Add a New Device',
    u'device.comment_list': u"List a Device's Comments",
    u'device.cpanel_add': u'Add a cPanel Account',
    u'device.delete': u'Delete a Device',
    u'device.event_list': u'List Device Events',
    u'device.facility_list': u'List Device Facilities',
    u'device.get': u'Get a Device',
    u'device.hostname_get': u'Get a Device Hostname',
    u'device.ip_assign': u'Assign an IP to a Device',
    u'device.ip_assignment_add': u'Create a New IP Assignment',
    u'device.ip_assignment_delete': u'Delete a Device IP Assignment',
    u'device.ip_assignment_list': u'List Device IP Assignments',
    u'device.ip_assignment_update': u'Update a Device IP Assignment',
    u'device.ip_get_available': u'List Available IP Addresses',
    u'device.ip_get_unassigned': u'Get Unassigned IP Addresses',
    u'device.ip_group_add': u'Add a Device IP Group',
    u'device.ip_group_delete': u'Delete a Device IP Group',
    u'device.ip_group_list': u'List a Device IP Group',
    u'device.ip_group_update': u'Update a Device IP Group',
    u'device.ip_lookup': u'Look Up a Device IP',
    u'device.ip_unassign': u'Unassign a Device IP',
    u'device.list': u'List Devices',
    u'device.module_call': u'Call a Device Module Function',
    u'device.module_call_aggregate': u'Call an Aggregate Device Module Function',
    u'device.module_graph': u'Generate Device Module Graph',
    u'device.monitor_add': u'Add a New Device Monitor',
    u'device.monitor_delete': u'Delete a Device Monitor',
    u'device.monitor_disable': u'Disable a Device Monitor',
    u'device.monitor_enable': u'Enable a Device Monitor',
    u'device.monitor_list': u'List Device Monitors',
    u'device.monitor_update': u'Update a Device Monitor',
    u'device.reboot': u"Set a Device's Power State",
    u'device.reboot_graph': u'Get a Reboot Graph',
    u'device.tag': u'Tag a Device',
    u'device.type_list': u'List Device Types',
    u'device.untag': u'Untag a Device',
    u'device.update': u'Update a Device',
    u'device.vlan_get_available': u'List Available VLANs',
    u'order.cancel': u'Cancel an Order',
    u'order.client_respond': u'Post a Client/Lead Order Response',
    u'order.coupon_get': u'Get Order Coupon Details',
    u'order.create': u'Create a New Order',
    u'order.get': u'Get Order Details',
    u'order.list': u'List Orders',
    u'order.process': u'Process an Order',
    u'order.queue_list': u'List Order Queues',
    u'order.respond': u'Post an Order Response',
    u'order.submit': u'Submit An Order',
    u'order.update': u'Update an Order',
    u'sales.opportunity_add': u'Add an Opportunity',
    u'sales.opportunity_list': u'List Opportunities',
    u'sales.opportunity_stage_list': u'List Opportunity Stages',
    u'sales.opportunity_status_list': u'List Opportunity Statuses',
    u'sales.opportunity_type_list': u'List Opportunity Types',
    u'sales.opportunity_update': u'Update an Opportunity',
    u'support.department_get': u'Get Ticket Departments',
    u'support.department_list': u'List Ticket Departments',
    u'support.ticket_count': u'Count Support Tickets',
    u'support.ticket_get': u'Get Support Ticket Details',
    u'support.ticket_list': u'Get a List of Tickets',
    u'support.ticket_merge': u'Merge Tickets',
    u'support.ticket_post_client_response': u'Post a Client Response to a Ticket',
    u'support.ticket_post_list': u'Get all Posts for a Ticket',
    u'support.ticket_post_staff_response': u'Post a Staff Response to a Ticket',
    u'support.ticket_submit': u'Submit a New Ticket',
    u'support.ticket_submit_outgoing': u'Create a New Outgoing Ticket',
    u'support.ticket_update': u'Update a Ticket',
    u'uber.api_export': u'Export Data',
    u'uber.attachment_get': u'Get an attachment',
    u'uber.attachment_list': u'List Attachments',
    u'uber.check_login': u'Verify a login and password',
    u'uber.client_welcome_stats': u'Display Client Statistics',
    u'uber.comment_add': u'Add Comment',
    u'uber.comment_delete': u'Delete Comment',
    u'uber.comment_get': u'Get Comments',
    u'uber.comment_list': u'List Comments',
    u'uber.comment_update': u'Update Comment',
    u'uber.documentation': u'Download API Documentation',
    u'uber.event_list': u'Access the Event Log',
    u'uber.forgot_pass': u'Send a Password Reminder',
    u'uber.login_list': u'List User Logins',
    u'uber.mail_get': u'Get an Email From the Log',
    u'uber.mail_list': u'Access the Mail Log',
    u'uber.message_list': u'List Message Board Messages',
    u'uber.metadata_bulk_get': u'Bulk Get Metadata Values',
    u'uber.metadata_get': u'Get Metadata Values',
    u'uber.method_get': u'Get API Method Details',
    u'uber.method_list': u'List Available API Methods',
    u'uber.quick_stats': u'Get Quick System Stats',
    u'uber.quick_stats_detail': u'Get Detailed System Stats',
    u'uber.service_plan_get': u'Get Service Plan Details',
    u'uber.service_plan_list': u'List Service Plans',
    u'uber.user_exists': u'Check whether a Client Exists',
    u'uber.username_exists': u'Check Whether a Username Exists',
}


class _ProxyModule(object):
    def __init__(self, handler, module):
        self.handler = handler
        self.module = module

    def __getattr__(self, name):
        """Return the call with request_handler prefilled."""
        call_func = getattr(self.module, name)
        if callable(call_func):
            call_p = partial(call_func, request_handler=self.handler)
            # store partial on proxy so it doesn't have to be created again
            setattr(self, name, call_p)
            return call_p
        raise AttributeError("'{0}' object has no attribute '{1}'".format(
                                                   type(self).__name__, name))


class _AbstractRequestHandler(object):
    def process_request(self, method, data=None, raw=False):
        """Process request.

            method: Ubersmith API method string
            data: dict of method arguments
            raw: Set to True to return the raw response vs the default
                 behavior of returning JSON data

        """
        raise NotImplementedError

    def _render_response(self, response, content, raw):
        """Render response as python object.

            response: dict like object with headers
            content: raw response string from ubersmith
            raw: Set to True to return the raw response vs the default
                 behavior of returning JSON data

        """
        # just return the raw response
        if raw:
            return response, content

        # response isn't json
        if response.get('content-type') != 'application/json':
            # handle case where ubersmith is 'updating token'
            # see: https://github.com/jasonkeene/python-ubersmith/issues/1
            if response.get('content-type') == 'text/html' and \
                'Updating Token' in content:
                raise UpdatingTokenResponse
            raise ResponseError("Response wasn't application/json")

        # response is json
        response_dict = json.loads(content)

        # test for error in json response
        if not response_dict.get('status'):
            raise ResponseError(response=response_dict)

        return response_dict['data']

    def _validate_request_method(self, method):
        """Make sure requested method is valid."""
        if method not in METHODS:
            raise RequestError("Requested method is not valid.")

    def _encode_data(self, data):
        """URL encode data."""
        return urlencode_unicode(data if data is not None else {})

    def __getattr__(self, name):
        """If attribute accessed is a call module, return a proxy."""
        if name in set(m.split('.')[0] for m in METHODS):
            module_name = 'ubersmith.{0}'.format(name)
            module = __import__(module_name, fromlist=[''])
            proxy = _ProxyModule(self, module)
            # store proxy on handler so it doesn't have to be created again
            setattr(self, name, proxy)
            return proxy
        raise AttributeError("'{0}' object has no attribute '{1}'".format(
                                                   type(self).__name__, name))


class HttpRequestHandler(_AbstractRequestHandler):
    """Handles HTTP requests and authentication."""

    def __init__(self, base_url, username=None, password=None):
        """Initialize HTTP request handler with optional authentication.

            base_url: URL to send API requests
            username: Username for API access
            password: Password for API access

        >>> handler = HttpRequestHandler('http://127.0.0.1:8088/')
        >>> handler.base_url
        'http://127.0.0.1:8088/'
        >>> config = {
        ...     'base_url': 'http://127.0.0.1/api/',
        ...     'username': 'admin',
        ...     'password': 'test_pass',
        ... }
        >>> handler = HttpRequestHandler(**config)
        >>> handler.base_url
        'http://127.0.0.1/api/'
        >>> handler.username
        'admin'
        >>> handler.password
        'test_pass'

        """
        self.base_url = base_url
        self.username = username
        self.password = password

        self._http = httplib2.Http(disable_ssl_certificate_validation=True)
        self._http.add_credentials(self.username, self.password,
                                   urlparse.urlparse(self.base_url)[1])

    def process_request(self, method, data=None, raw=False):
        """Process request over HTTP to ubersmith instance.

            method: Ubersmith API method string
            data: dict of method arguments
            raw: Set to True to return the raw response vs the default
                 behavior of returning JSON data

        """
        # make sure requested method is valid
        self._validate_request_method(method)

        # try request 3 times
        for i in range(3):
            # make the request
            response, content = self._send_request(method, data)
            try:
                # render the response as python object
                return self._render_response(response, content, raw)
            except UpdatingTokenResponse:
                # wait 4 secs before retrying request
                time.sleep(4)
        # if last attempt still threw an exception, reraise it
        raise

    def _send_request(self, method, data):
        url = append_qs(self.base_url, {'method': method})
        body = self._encode_data(data)
        # httplib2 requires that you manually send Content-Type on POSTs :/
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self._http.request(url, "POST", body, headers)


def get_default_request_handler():
    """Return the default request handler."""
    if not _DEFAULT_REQUEST_HANDLER:
        raise Exception("Request handler required but no default was found.")
    return _DEFAULT_REQUEST_HANDLER


def set_default_request_handler(request_handler):
    """Set the default request handler."""
    if not isinstance(request_handler, _AbstractRequestHandler):
        raise TypeError(
            "Attempted to set an invalid request handler as default.")
    global _DEFAULT_REQUEST_HANDLER
    _DEFAULT_REQUEST_HANDLER = request_handler
