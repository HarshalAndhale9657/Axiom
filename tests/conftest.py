"""Test session guards."""
import os

# Never hit live external APIs from the test suite.
os.environ["RAZORPAY_ENABLED"] = "0"          # actuator uses its stub path
os.environ["AXIOM_VERIFIER_PROVIDER"] = "none"  # the cross-vendor verifier is skipped
