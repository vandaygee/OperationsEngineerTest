#!/user/bin/env python2.7

import unittest
from datetime import date, datetime

from accounting import db
from accounting.models import Contact, Policy
from accounting.utils import PolicyAccounting, generate_monthly_invoices

"""
#######################################################
Test Suite for Generate Policy Three
#######################################################
"""


class TestGeneratePolicyThreeInvoices(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Policy Three', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        cls.policy.billing_schedule = "Monthly"
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pa = PolicyAccounting(self.policy.id)

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_generate_policy_three_invoice(self):
        #test if policy three has invoice(s)
        self.assertTrue(self.policy.invoices)
        generate_monthly_invoices(self.policy.id)
        # test if the number of policy three invoices is 12 plus the unaltered invoice generated
        self.assertEqual(len(self.policy.invoices), 12)
        # test if the generated policy invoice due amount is equals to policy annual amount divided by 12
        self.assertEqual(self.policy.invoices[0].amount_due, self.policy.annual_premium / 12)

