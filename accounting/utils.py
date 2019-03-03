#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import logging

from accounting import db
from models import Contact, Invoice, Payment, Policy


logging.basicConfig(format='%(process)d-%(levelname)s-%(message)s')

"""
#######################################################
This is the base code for the engineer project.
#######################################################
"""


class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    def __init__(self, policy_id):
        self.policy = Policy.query.filter_by(id=policy_id).one()

        if not self.policy.invoices:
            self.make_invoices()

    """
    This function gets the account balance of a policy i.e the amount left to paid on the policy
    """
    def return_account_balance(self, date_cursor=None):

        # this sets the filtering date to today's date if date is not specified
        if not date_cursor:
            date_cursor = datetime.now().date()

        # gets all the policy's invoices whose bill date is less than or equals to the date_cursor
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()
        # sets the initial total amount due to be paid on the policy to 0
        due_now = 0

        # get the amount to have been paid before date_cursor
        for invoice in invoices:
            due_now += invoice.amount_due

        # gets all the payments made before the date_cursor
        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()
        # deducts all the payments made so far on the policy from the policy total amount due
        for payment in payments:
            due_now -= payment.amount_paid

        # returns the total amount left to paid on the policy
        return due_now

    """
    This function enables payment to be made for a policy
    """
    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        # this sets the filtering date to today's date if date is not specified
        if not date_cursor:
            date_cursor = datetime.now().date()

        # if contact_id is not set, get the policy name_insured and set contact_id to it
        if not contact_id:
            try:
                contact_id = self.policy.named_insured
            except:
                pass

        # create a payment instance and add the payment to database
        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        # returns the an instance of the payment made
        return payment

    """
        This function checks for policy's cancellation pending due to non-pay
    """

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """
         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.
        """
        # this sets the filtering date to today's date if date is not specified
        if not date_cursor:
            date_cursor = datetime.now().date()
            print date_cursor

        # gets the policy's invoice whose due date has passed but not made it yet to cancel_date
        invoices = Invoice.query.filter_by(policy_id=self.policy.id) \
            .filter(Invoice.due_date <= date_cursor, Invoice.cancel_date >= date_cursor) \
            .order_by(Invoice.bill_date) \
            .all()

        for invoice in invoices:
            # check if there has been payment for the invoice
            payments = Payment.query.filter_by(policy_id=self.policy.id) \
                .filter(Payment.transaction_date <= invoice.cancel_date,
                        Payment.transaction_date >= invoice.bill_date) \
                .all()

            if not payments:
                self.policy.status = "Cancellation pending due to non-pay"
                db.session.commit()
                return invoice

    """
    This function checks for invoice cancellation
    """
    def evaluate_cancel(self, date_cursor=None):
        # this sets the filtering date to today's date if date is not specified
        if not date_cursor:
            date_cursor = datetime.now().date()

        # gets all the policy's invoices whose cancel date is in the past
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.cancel_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()

        # checks for all the policy's invoices that should have been canceled available for
        for invoice in invoices:
            """
            check if there is still an outstanding invoice amount_due on the the invoice
            if there is prompt for a policy cancellation
            """
            if not self.return_account_balance(invoice.cancel_date):
                continue
            else:
                print "THIS POLICY SHOULD HAVE CANCELED"
                break
        else:
            print "THIS POLICY SHOULD NOT CANCEL"

    """
        This function generates invoices for a new created policy
    """
    def make_invoices(self):
        # delete all invoices attached to the policy
        for invoice in self.policy.invoices:
            invoice.delete()

        # dictionary for billing schedules
        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Semi-Annual': 3, 'Quarterly': 4, 'Monthly': 12}

        # create an empty list to store all invoices generated for the policy
        invoices = []
        # create a initial invoice that holds the total annual amount to paid on the policy
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date, #bill_date
                                self.policy.effective_date + relativedelta(months=1), #due
                                self.policy.effective_date + relativedelta(months=1, days=14), #cancel
                                self.policy.annual_premium)
        # add the initial invoice to invoice list
        invoices.append(first_invoice)

        if self.policy.billing_schedule == "Annual":
            """
            if the policy billing schedule is Annual don't generate any additional invoice(s) for the policy
            """
            pass
        elif self.policy.billing_schedule == "Two-Pay":
            """
            if the policy billing schedule is Two-Pay generate 2 invoices for the policy
            """
            # set the initial invoice amount to the total policy due amount divided by number of times to pay it
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)

            # generate individual invoice for the number of time to pay for the policy
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                # calculate the month for the next payment
                months_after_eff_date = i*6
                # set the date fr the bill date
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                # create an instance of invoice
                invoice = Invoice(self.policy.id,
                                  bill_date,  # bill date
                                  bill_date + relativedelta(months=1),  # due date
                                  bill_date + relativedelta(months=1, days=14),  # cancel date
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                # add the generated invoice to invoice list
                invoices.append(invoice)
        elif self.policy.billing_schedule == "Quarterly":
            """
            if the policy billing schedule is Quarterly generate 4 invoices for the policy
            """
            # set the initial invoice amount to the total policy due amount divided by number of times to pay it
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            # generate individual invoice for the number of time to pay for the policy
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                # calculate the month for the next payment
                months_after_eff_date = i*3
                # set the date fr the bill date
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                # create an instance of invoice
                invoice = Invoice(self.policy.id,
                                  bill_date,  # bill date
                                  bill_date + relativedelta(months=1),  # due date
                                  bill_date + relativedelta(months=1, days=14), # cancel date
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                # add the generated invoice to invoice list
                invoices.append(invoice)

        elif self.policy.billing_schedule == "Monthly":
            """
            if the policy billing schedule is Monthly generate invoice for monthly payment yet
            """
            pass
        else:
            print "You have chosen a bad billing schedule."

        # save all the generated invoices to the database
        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()

    """
        This function implements being able to change the billing schedule in the middle of a policy
    """
    def schedule_changing(self, new_billing_schedule):
        account_balance = self.return_account_balance()
        # dictionary for billing schedules
        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Semi-Annual': 3, 'Quarterly': 4, 'Monthly': 12}
        if new_billing_schedule in billing_schedules.keys():
            self.policy.billing_schedule = new_billing_schedule

            # set old invoice delete to TRUE
            for invoice in self.policy.invoices:
                invoice.deleted = True

            # create an empty list to store all the new invoices generated for the policy
            invoices = []
            # create a initial invoice that holds the total annual amount to paid on the policy
            first_invoice = Invoice(self.policy.id,
                                    self.policy.effective_date,  # bill_date
                                    self.policy.effective_date + relativedelta(months=1),  # due
                                    self.policy.effective_date + relativedelta(months=1, days=14),  # cancel
                                    account_balance)
            # add the initial invoice to invoice list
            invoices.append(first_invoice)

            if self.policy.billing_schedule == "Annual":
                """
                if the policy billing schedule is Annual don't generate any additional invoice(s) for the policy
                """
                pass
            elif self.policy.billing_schedule == "Two-Pay":
                """
                if the policy billing schedule is Two-Pay generate 2 invoices for the policy
                """
                # set the initial invoice amount to the total policy due amount divided by number of times to pay it
                first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(
                    self.policy.billing_schedule)

                # generate individual invoice for the number of time to pay for the policy
                for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                    # calculate the month for the next payment
                    months_after_eff_date = i * 6
                    # set the date fr the bill date
                    bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                    # create an instance of invoice
                    invoice = Invoice(self.policy.id,
                                      bill_date,  # bill date
                                      bill_date + relativedelta(months=1),  # due date
                                      bill_date + relativedelta(months=1, days=14),  # cancel date
                                      account_balance / billing_schedules.get(self.policy.billing_schedule))
                    # add the generated invoice to invoice list
                    invoices.append(invoice)
            elif self.policy.billing_schedule == "Quarterly":
                """
                if the policy billing schedule is Quarterly generate 4 invoices for the policy
                """
                # set the initial invoice amount to the total policy due amount divided by number of times to pay it
                first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(
                    self.policy.billing_schedule)
                # generate individual invoice for the number of time to pay for the policy
                for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                    # calculate the month for the next payment
                    months_after_eff_date = i * 3
                    # set the date fr the bill date
                    bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                    # create an instance of invoice
                    invoice = Invoice(self.policy.id,
                                      bill_date,  # bill date
                                      bill_date + relativedelta(months=1),  # due date
                                      bill_date + relativedelta(months=1, days=14),  # cancel date
                                      account_balance / billing_schedules.get(self.policy.billing_schedule))
                    # add the generated invoice to invoice list
                    invoices.append(invoice)

            elif self.policy.billing_schedule == "Monthly":
                """
                if the policy billing schedule is Monthly generate invoices for monthly payment 
                """
                first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(
                    self.policy.billing_schedule)
                for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                    months_after_eff_date = i * 1
                    bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                    # create an instance of invoice
                    invoice = Invoice(self.policy.id,
                                      bill_date,
                                      bill_date + relativedelta(months=1),
                                      bill_date + relativedelta(months=1, days=14),
                                      account_balance / billing_schedules.get(self.policy.billing_schedule))
                    # add the generated invoice to invoice list
                    invoices.append(invoice)

            # save all the generated invoices to the database
            for invoice in invoices:
                db.session.add(invoice)
            db.session.commit()
            print self.policy.policy_number, " billing schedule changed to ", self.policy.billing_schedule, \
                " successfully"
        else:
            print "Bad Billing Schedule Selected"


"""
    This function generates invoices for policy three (a monthly schedule)
    Invoice(s) are not generated automatically when policy three plan is created
    
    Note: This function should be run in shell with the Policy Three id passed to it
"""


def generate_monthly_invoices(policy_id):
        # query the database to get the policy with the id
        policy = Policy.query.filter_by(id=policy_id).one()

        # check if the policy has an initial invoice generated by PolicyAccounting
        if policy.invoices:

            # check if the policy is a Policy Three plan
            if policy.policy_number == "Policy Three":
                # delete any pre-generated invoice for the policy
                for invoice in policy.invoices:
                    db.session.delete(invoice)

                # set the billing schedule to 12 i.e monthly
                billing_schedule = 12
                # create an empty list to store all invoices generated for the policy
                invoices = []
                # create an instance of invoice
                first_invoice = Invoice(policy.id,
                                        policy.effective_date,  # bill_date
                                        policy.effective_date + relativedelta(months=1),  # due
                                        policy.effective_date + relativedelta(months=1, days=14),  # cancel
                                        policy.annual_premium)

                invoices.append(first_invoice)

                first_invoice.amount_due = first_invoice.amount_due / billing_schedule
                for i in range(1, billing_schedule):
                    months_after_eff_date = i * 1
                    bill_date = policy.effective_date + relativedelta(months=months_after_eff_date)
                    # create an instance of invoice
                    invoice = Invoice(policy.id,
                                      bill_date,
                                      bill_date + relativedelta(months=1),
                                      bill_date + relativedelta(months=1, days=14),
                                      policy.annual_premium / billing_schedule)
                    # add the generated invoice to invoice list
                    invoices.append(invoice)

                # save all the generated invoices to the database
                for invoice in invoices:
                    db.session.add(invoice)
                db.session.commit()
                print "Invoices generated for Policy Three (Monthly Schedule)"
            else:
                print("This not a Policy Three. Get the appropriate representation of Policy Three")
        else:
            print("Policy not found")


"""
    This function creates Policy Four with the following details
        - Policy Number: 'Policy Four'
        - Effective: 2/1/2015
        - Billing Schedule: 'Two-Pay'
        - Named Insured: 'Ryan Bucket'
        - Agent: 'John Doe'
        - Annual Premium: $500
    and also generates invoice(s) for it
    
    Note: This function should be run from shell
"""


def create_policy_four():
    # get contact whose name and Role are John Doe and role respectively
    john_doe_agent = Contact.query.filter_by(name="John Doe", role="Agent").one()
    # get contact whose name and Role are Ryan Bucket and Name Insured respectively
    ryan_bucket = Contact.query.filter_by(name="Ryan Bucket", role="Named Insured").one()
    #   create a policy instance for Policy Four with annual amount of $500
    p4 = Policy('Policy Four', date(2015, 2, 1), 500)
    p4.billing_schedule = 'Two-Pay'  # billing schedule
    p4.agent = john_doe_agent.id  # agent
    p4.named_insured = ryan_bucket.id  # named insured

    # save Policy Four to database
    db.session.add(p4)
    db.session.commit()

    # Use PolicyAccounting to create invoice(s) for Policy Four
    PolicyAccounting(p4.id)
    print "Policy Four Created and invoices are generated for it"


"""
    This function helps Mary Sue Client to pay off policy one

    Note: This function should be run from the shell
"""


def pay_off_policy_one():
    try:
        policy_id = int(raw_input("Enter Policy Id: "))
        policy_name_insured = raw_input("Enter Name Insured: ")
        amount = int(raw_input("Enter amount: "))
        pay_date = map(int, raw_input("Enter date (YYYY/mm/dd): ").strip().split("/"))

        # query the database to get the policy with the id
        policy = Policy.query.filter_by(id=policy_id).one()
        if policy:
            if policy.policy_number == "Policy One":
                contact = Contact.query.filter_by(name=policy_name_insured, role="Named Insured").one()
                if contact:
                    if policy.annual_premium == amount:
                        pa = PolicyAccounting(policy.id)
                        pa.make_payment(contact.id, date(pay_date[0], pay_date[1], pay_date[2]), amount)
                        print "Policy One paid off successfully!"
                    else:
                        print " Amount entered is not the amount expected. Try again with the exact amount" \
                              " expected to be paid"
                else:
                    print "Name Insured not found. Try again with a valid Name Insured"
            else:
                print "Policy is not Policy One. Try again with a valid Policy One Id!!!"
        else:
            print "Invalid policy Id entered. Try again with a valid policy Id!"
    except:
        print "\nAn error occurred while processing your payment. Try again and be sure are input are correctly entered"


################################
# The functions below are for the db and 
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()

