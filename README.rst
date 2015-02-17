============================================
Python Ripple API and transaction management
============================================

Settings
========

* ``RIPPLE_ACCOUNT`` - account that acts as 'manager' and monitors incoming transactions
* ``RIPPLE_SECRET`` - secret for 'manager' account
* ``RIPPLE_API_DATA[0]['RIPPLE_API_URL']``
* ``RIPPLE_API_DATA[0]['RIPPLE_API_USER']``
* ``RIPPLE_API_DATA[0]['RIPPLE_API_PASSWORD']``
* ``RIPPLE_TIMEOUT`` - timeout for django manamgement command calls
* ``RIPPLE_TRANSACTION_MONITOR_MIN_LEDGER_INDEX`` - offset, ledger index to start transaction monitoring with,
default is the beginning of time

Example Config::

	RIPPLE_API_DATA = [
		{
            'RIPPLE_API_URL': 'http://s_west.ripple.com:51234',
            'RIPPLE_API_USER': '',
            'RIPPLE_API_PASSWORD': '',
        }
	]  # You can specify multiple servers and ripple_api app will try them in order if one of servers
	#    returns error


Signals
=======

* ``ripple_api.signals.transaction_status_changed = Signal(providing_args=["old_status"])`` - sent
  when existing Transaction's status is changed
* default django's post_save signal is useful to get new Transactions


.. TODO:
   * docs on api usage
   * docs on management command
