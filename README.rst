============================================
Python Ripple API and transaction management
============================================

Settings
========

* ``RIPPLE_ACCOUNT`` — account that acts as 'manager' and monitors incoming transactions
* ``RIPPLE_SECRET`` — secret for 'manager' account
* ``RIPPLE_API_URL``
* ``RIPPLE_API_USER``
* ``RIPPLE_API_PASSWORD``


Signals
=======

* ``ripple_api.signals.transaction_status_changed = Signal(providing_args=["old_status"])`` — sent
  when existing Transaction's status is changed
* default django's post_save signal is useful to get new Transactions


.. TODO:
   * docs on api usage
   * docs on management command