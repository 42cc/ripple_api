=========
Changelog
=========

0.0.22
====
Added ability to trade USD -> XRP (`buy_xrp`)

0.0.21
====
Added XRP support to create_offer

0.0.18.2
====
* return funds for transactions marked as MUST_BE_RETURN
* retry failed transactions by creating new ones

0.0.17.1
====
Added configurable (in settings) timeout to management/commands/process_transactions.py

0.0.16
=====
Fixed `tx` and `balance` calls

0.0.15
=====
* added path_find support to tasks.sign_task

0.0.14
=====
Added path_find

0.0.10
=====
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
