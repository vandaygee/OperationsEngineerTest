$("#query-date").datepicker({ dateFormat: 'dd/mm/yy' });

function InvoicesViewModel() {
    var self = this;
    self.invoicesURI='http://0.0.0.0:5000/invoices';
    self.policy_id = ko.observable();
    self.query_date = ko.observable();
    self.policy_number = ko.observable();
    self.account_balance = ko.observable();
    self.invoices = ko.observableArray();
    self.error_message = ko.observable();

    self.hidePolicyDetails = function(e){
        $('.policy-details').hide();
        $('.policy-show').hide();
        $('.err-msg').hide();
    }

    self.ajax = function(uri, method, data) {
        var json_data = ko.toJSON(data);
        var jqxhr = $.ajax({
            url: uri,
            type: "POST",
            crossDomain: true,
            data: json_data,
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            accepts: "application/json",
            cache: false,
            success: function(){
                console.log("success")
            }
        });
        return jqxhr;
    }

    self.loadInvoices = function(policy) {
        self.clearInvoices(self.invoices);
        self.ajax(self.invoicesURI, 'POST', policy).done(function(data) {
        self.policy_number(data.policy_number);
        self.account_balance(data.account_balance);
            $.each(data.invoices, function( index, value ) {
                self.invoices.push({
                    bill_date: ko.observable(value.bill_date),
                    due_date: ko.observable(value.due_date),
                    cancel_date: ko.observable(value.cancel_date),
                    amount_due: ko.observable(value.amount_due),
                    payment_status: ko.observable(value.payment_status)
                 });
            });

            $('.policy-details').show();
            $('.policy-show').show();
            $('.err-msg').hide();

        }).fail(function(err){
            $('.policy-details').show();
            $('.policy-show').hide();
            $('.err-msg').show();


            self.error_message("Oops!!! Error occurred loading invoice(s) for Policy ID "+self.policy_id()+
            "\n. Please try again with a valid Policy ID.");
            console.log("Error: "+err.status);
        });
    }

    self.clearInvoices = function(invoices){
        invoices([])
    }

    self.hidePolicyDetails();
}


function QueryPolicy() {
    var self = this;
    self.policy_id = ko.observable();
    self.query_date = ko.observable();

    self.query = function() {
        invoicesViewModel.hidePolicyDetails();
        invoicesViewModel.policy_id(self.policy_id());
        invoicesViewModel.query_date(self.query_date());

        invoicesViewModel.loadInvoices({
            policy_id: self.policy_id(),
            query_date: self.query_date()
        });

        self.policy_id("");
        self.query_date("");
    }
 }

var invoicesViewModel = new InvoicesViewModel()
var queryPolicy = new QueryPolicy()

ko.applyBindings(invoicesViewModel, $('.policy-details')[0]);
ko.applyBindings(queryPolicy, $('.query-policy')[0]);




