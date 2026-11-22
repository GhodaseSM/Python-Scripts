"""OTP Verify — Otpverification.py
=================================
Generates a 6-digit numeric OTP, (optionally) sends it via Gmail SMTP,
reads user input, and prints Verified / Please Check your OTP again.

Public API
----------
generate_otp(rng=None) -> str
    Returns a 6-character string of digits (domain: "000000"–"999999").
    *rng* is an optional ``random.Random`` instance; when omitted the
    module-level ``random`` state is used (line 9 of original source).

verify_otp(user_input: str, otp: str) -> bool
    Returns True iff user_input == otp (exact string equality, line 18).

send_otp_email(smtp_client, sender: str, recipient: str, otp: str) -> None
    Sends "<otp> is your OTP" via *smtp_client* (line 16 of original).

run_interactive(smtp_factory=None, input_fn=input, print_fn=print) -> bool
    Full interactive flow: generate → send → verify (lines 7-21 of original).
    *smtp_factory* is a callable() -> connected SMTP object; when None the
    function skips sending (useful for testing without a live SMTP server).
    Returns the bool result of verify_otp so callers can inspect it.

Mutation behaviour
------------------
* ``generate_otp`` has no side-effects beyond advancing the PRNG state.
* ``verify_otp`` is a pure function with no side-effects.
* ``send_otp_email`` mutates the SMTP connection (calls starttls, login,
  sendmail).  External dependency: network + Gmail SMTP credentials.
* ``run_interactive`` reads from stdin (via *input_fn*) and writes to stdout
  (via *print_fn*); those are injectable for testing.

External dependencies (original)
---------------------------------
* ``smtplib`` — stdlib, no install required.
* ``random``, ``math``, ``os`` — stdlib.
* Gmail SMTP: smtp.gmail.com:587, requires app-password credentials.
* stdin / stdout (interactive).
"""

import math
import os
import random
import smtplib

# ---------------------------------------------------------------------------
# Core logic (extracted from original lines 6-21)
# ---------------------------------------------------------------------------

DIGITS = "0123456789"  # domain definition (original line 6)


def generate_otp(rng=None):
    """Generate a 6-digit OTP string.

    Precondition (src line 8): loop runs exactly 6 times.
    Precondition (src line 9): each character is drawn from DIGITS (0-9).
    Returns a str of length 6 composed solely of ASCII digits.
    """
    if rng is None:
        _rng_random = random.random
    else:
        _rng_random = rng.random

    otp = ""
    for i in range(6):                              # src line 8
        otp += DIGITS[math.floor(_rng_random() * 10)]  # src line 9
    return otp                                      # returns str, len==6


def verify_otp(user_input: str, otp: str) -> bool:
    """Return True iff user_input exactly matches otp.

    Precondition (src line 18): comparison is strict string equality (==).
    No type coercion, no case folding, no stripping.
    """
    return user_input == otp                        # src line 18


def send_otp_email(smtp_client, sender: str, recipient: str, otp: str) -> None:
    """Send the OTP message via an already-connected SMTP client.

    src line 10: message format is "<OTP> is your OTP"
    src line 16: sendmail(sender, recipient, msg)
    """
    msg = otp + " is your OTP"                     # src line 10-11
    smtp_client.sendmail(sender, recipient, msg)    # src line 16


def run_interactive(smtp_factory=None, input_fn=input, print_fn=print) -> bool:
    """Full interactive OTP flow (original lines 7-21).

    When *smtp_factory* is None, email sending is skipped (test-safe).
    Returns verify_otp result so test callers can assert on it.
    """
    otp = generate_otp()                           # src lines 7-9

    if smtp_factory is not None:
        smtp_client = smtp_factory()               # src lines 12-16
        send_otp_email(smtp_client, "sender@gmail.com",
                       input_fn("Enter your email: "), otp)
    else:
        _ = input_fn("Enter your email: ")        # keep prompt for UX parity

    user_input = input_fn("Enter Your OTP >>: ")  # src line 17
    result = verify_otp(user_input, otp)           # src line 18

    if result:
        print_fn("Verified")                       # src line 19
    else:
        print_fn("Please Check your OTP again")   # src line 21

    return result


# ---------------------------------------------------------------------------
# Entry-point (keeps original interactive behaviour when run directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.starttls()
    s.login("Your Gmail Account", "You app password")

    email = input("Enter your email: ")
    otp = generate_otp()
    send_otp_email(s, "&&&&&&&&&&", email, otp)

    user_input = input("Enter Your OTP >>: ")
    if verify_otp(user_input, otp):
        print("Verified")
    else:
        print("Please Check your OTP again")
