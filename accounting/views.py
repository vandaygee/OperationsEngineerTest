# You will probably need more methods from flask but this one is a good start.
from flask import render_template, request, jsonify
import datetime

# Import things from Flask that we need.
from accounting import app, db

# Import our models
from models import Contact, Invoice, Policy
from utils import PolicyAccounting

# Routing for the server.
@app.route("/")
def index():
    # You will need to serve something up here.
    return render_template('index.html')


@app.route("/invoice")
def test():
    return render_template('invoice.html')


@app.route("/invoices", methods=['POST'])
def get_invoice():
    if request.json:
        data = dict()
        policy_id = int(request.json['policy_id'])
        query_date = datetime.datetime.strptime(request.json['query_date'], '%d/%m/%Y').date()
        pa = PolicyAccounting(policy_id)
        data['policy_number'] = pa.get_policy_number()
        data['account_balance'] = pa.return_account_balance(query_date)
        data['invoices'] = pa.get_invoices(query_date)
        return jsonify(data)



