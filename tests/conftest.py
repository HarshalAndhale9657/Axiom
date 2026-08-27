"""Test session guards."""
import os

# Never hit the live Razorpay API from the test suite — force the actuator's stub path.
os.environ["RAZORPAY_ENABLED"] = "0"
