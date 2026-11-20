# Noel Chauffer — support@noelchauffer.com auto-reply bank

Question-based auto-replies for mail arriving at support@noelchauffer.com
(which forwards to the owner's Gmail). Same answers as the website's
"Chat with us" widget + homepage FAQ, so email, widget and app all say
the same thing.

## Rules
- Match the customer's question by keywords (first match wins, in order).
- Reply in English, warm and plain. Customer-facing text is English only.
- NEVER quote per-mile rates or fares — the site shows no rates; the total
  is shown only inside a booking.
- NEVER invent a booking, driver, time or price. If the question needs a
  real booking lookup, say the team will check and reply within 24 hours.
- Sign every reply: "Noel Chauffer team".

## Answers

### Cancellation / refund
Keywords: cancel, refund
> Cancellation is free if you cancel more than 1 hour before pickup, and your payment is refunded in full. If you cancel 1 hour or less before pickup, the full price of the ride applies.

### Waiting / airport / late / delay
Keywords: wait, airport, late, delay
> Waiting is free for 60 minutes at airports and 15 minutes at other pickups. After that, waiting is charged at $1/min. A no-show is charged the full price — your chauffeur waits 60 minutes at airports and 30 minutes at other pickups before a ride is marked as a no-show.

### Price / cost / total / pay / payment
Keywords: price, cost, much, total, charge, pay, payment
> After you complete the booking form, choose Business Class or Business SUV — each class shows its own single total, with no breakdown and no hidden charges. You pay by card on this page, and then your chauffeur is assigned.

### Lost item
Keywords: lost, left, forgot, belonging, item
> I am sorry to hear that. Please report it here as soon as you can, and within 7 days. The driver checks the car after every ride. Unclaimed items go to the police station after one week.

### Problem / complaint / unhappy
Keywords: problem, complaint, issue, unhappy, escalat, manager, owner
> I am sorry about that. I will escalate this to the owner, who will look into it personally. Please tell me your pickup date and time and what happened.

### Driver / chauffeur details
Keywords: driver, chauffeur, phone, email, detail, contact
> As soon as your chauffeur accepts, you will see their name, phone number, car, colour and plate number — and the same details are sent to your phone and email.

### Cars / classes
Keywords: car, vehicle, sedan, suv, type, class
> Our rides come in two classes — Business Class and Business SUV — recent high-end cars, clean, comfortable, and prepared for every ride, with phone chargers on board.

### Return / round trip
Keywords: return, round trip, back, come back
> For a return journey, simply book a second one-way ride. After you pay for your first ride, you can book your return trip with the addresses already swapped for you.

### By the hour
Keywords: hour, hourly, by the hour
> Choose the "By the hour" tab in the booking form, enter your pickup, date, time and how many hours you need. Your chauffeur stays with you for the hours you book.

### Referral / 5% off
Keywords: refer, friend, code, discount, off
> If a friend referred you, enter their referral code in the booking form, or book through their referral link — you get 5% off your first ride.

### How to book
Keywords: book, reserve, ride, pickup, how
> To book: fill in the form at noelchauffer.com — pickup, drop-off (or hours), date, time, and your name, phone and email — then tap "View options" to choose your class. Each class shows its own single total — you pay by card, and then your chauffeur will be assigned.

### Greeting
Keywords: hello, hi, hey, salam
> Hello, and welcome to Noel Chauffer. I can help with booking, the total, cancellation, waiting time, lost items, or a problem with a ride.

### Human / agent
Keywords: human, person, agent, support, help
> You are writing to the Noel Chauffer team here. The team replies within 24 hours. If your matter is urgent, please describe it and we will escalate it to the owner.

### Fallback (no match)
> Happy to help. I can answer questions about booking a ride, when you see the total, cancellation, waiting time, your chauffeur's details, cars, return trips, by-the-hour rides, or lost items — just ask. The team replies within 24 hours.

## How it runs
Gmail itself cannot do this (no vacation reply / filter access from here),
so a scheduled checker reads new mail to support@noelchauffer.com, picks
the matching answer above, and sends the reply from support@noelchauffer.com.
Anything the bank cannot answer goes to the owner, not to the customer.
