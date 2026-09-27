# Card payments

`PAYMENT_CHANNEL_ID` defaults to `-1003949300805`. The main bot must receive new
channel posts there; existing channel history is not scanned. Run one Telegram
polling process for the token. Database startup creates `card_orders` and
`card_receipts`. No external payment request is sent by the test suite.

Each recipient card has its own FIFO queue. Prices come from the server.
An order gets five minutes when it reaches the head and the client polls it.
Reopening an active order does not reset the deadline. Queued clients poll every
three seconds; a queued client absent for 45 seconds is removed so abandoned
queues do not block others. Active orders remain reserved even if the app closes.

PostgreSQL transaction advisory locking serializes order creation, queue
advancement and receipts across workers. Subscription grants and receipt
consumption commit together. Channel/message IDs and normalized full-message
fingerprints prevent duplicate grants. Authentication uses Telegram init data;
order status is accessible only to its owner.

Supported incoming bank notifications contain a plus-prefixed UZS credit amount,
masked recipient ending 8346 or 9963, and Uzbekistan bank date/time in either
`DD.MM.YY HH:MM` or `HH:MM DD.MM.YYYY` form. The balance is never used as the paid
amount. Messages must arrive during the active order, have a matching amount,
and a bank timestamp inside that window (minute precision). Unknown, mismatched,
old or late messages are stored with `review` status without granting anything.
The UI shows Support after expiry; no admin review UI is included yet.

Accepted limitation: the notification has no payer identity. A former customer
paying during a later customer's slot with the same amount can be attributed
to the later customer. The owner accepted manual correction for this case.
Full-message deduplication is not a bank transaction ID; changed duplicates
cannot be reliably recognized. No claim of payer identification is made.

Local checks: `python -m unittest discover -s tests -p test_card_orders.py -v`
and `node --check app/web/assets/card-payment.js`. Before publishing, verify
real bank formats and a real channel delivery on a controlled order, along with
PostgreSQL multi-worker behavior. Local tests use isolated SQLite only.
