=========
Changelog
=========

0.0.44
======

- Change error message in `buy_xrp`


0.0.40
======

- handle input better in `simple_trade`


0.0.39
======

- add `simple_trade` function for currency exchange. Uses method similar to
  what ripple client does in 'Trade -> Simple' mode.

0.0.34
======
Changed "amount" to "value" in `create_offer`, according to https://ripple.com/build/transactions/#offercreate

0.0.32
======
Offset option `RIPPLE_TRANSACTION_MONITOR_MIN_LEDGER_INDEX` for transaction monitor.

0.0.31
======
Transaction monitor to support `account` param.

0.0.30
======
Minor PEP8 fixes

0.0.24
======
Changed description of error in `buy_xrp`

0.0.23
======
Added trade api

0.0.22
======
Added ability to trade USD -> XRP (`buy_xrp`)

0.0.21
======
Added XRP support to create_offer

0.0.18.2
========
* return funds for transactions marked as MUST_BE_RETURN
* retry failed transactions by creating new ones

0.0.17.1
========
Added configurable (in settings) timeout to management/commands/process_transactions.py

0.0.16
======
Fixed `tx` and `balance` calls

0.0.15
======
* added path_find support to tasks.sign_task

0.0.14
======
Added path_find

0.0.10
======
* retry transaction status if got telINSUF_FEE_P from server

0.0.3
=====
* multiple servers can be specified in django settings.
* ripple_api.ripple_api.* methods now support speciying API-server url

0.0.2
=====
* ripple_api.ripple_api.* methods now support speciying API-server user and password

0.0.1
=====
* initial release
